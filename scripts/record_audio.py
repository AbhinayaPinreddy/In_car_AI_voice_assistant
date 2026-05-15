"""Microphone recording with adaptive VAD (voice activity detection)."""

from __future__ import annotations

import time
from collections import deque
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as wav_write

from config import (
    AUDIO_TMP,
    CALIBRATION_SECONDS,
    CHUNK_SIZE,
    MAX_RECORD_SECONDS,
    MAX_WAIT_SECONDS,
    MIN_SPEECH_SECONDS,
    SAMPLE_RATE,
    SILENCE_HANGOVER,
)

# Shared noise floor so barge-in detection uses the same baseline
_LAST_NOISE_RMS: float = 0.0025
_INPUT_DEVICE: Optional[int] = None   # set once on first call to record_audio()

_VOICE_START_STREAK = 3        # consecutive loud chunks needed to confirm speech
_PRE_ROLL_CHUNKS = 4           # keep a few chunks before speech starts

# Absolute floor — prevents threshold from climbing above this even in noisy rooms
_ABS_START_MAX = 0.065
_ABS_CONT_MAX = 0.055


def _voice_thresholds(noise_rms: float) -> tuple[float, float]:
    """
    Compute (start, continue) thresholds from calibrated noise floor.

    Strategy:
    - start  = noise * 1.8  (voice must be ~80% louder than background)
    - cont   = noise * 1.3  (hysteresis: easier to stay in than to enter)
    - Both are capped so extremely noisy rooms don't block speech entirely.
    - cont is always strictly less than start.
    """
    n = max(float(noise_rms), 0.003)
    start = min(n * 1.8, _ABS_START_MAX)
    start = max(start, 0.008)          # absolute floor for digital silence
    cont = min(n * 1.3, _ABS_CONT_MAX)
    cont = max(cont, 0.005)
    cont = min(cont, start * 0.85)     # cont must always be < start
    return start, cont


def _select_input_device() -> Optional[int]:
    """
    Pick the input device with the lowest noise floor.

    Tries all available input devices, records 0.3 s each, and returns the
    device index whose RMS is smallest. Falls back to system default (None)
    if nothing can be opened.
    """
    devices = sd.query_devices()
    best_idx: Optional[int] = None
    best_rms: float = float("inf")

    for i, d in enumerate(devices):
        if d["max_input_channels"] < 1:
            continue
        try:
            cal = sd.rec(
                int(0.3 * SAMPLE_RATE),
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                device=i,
            )
            sd.wait()
            rms = float(np.sqrt(np.mean(cal ** 2)))
            if rms < best_rms:
                best_rms = rms
                best_idx = i
        except Exception:
            continue

    if best_idx is not None:
        print(f"Selected input device [{best_idx}]: {devices[best_idx]['name']}  noise={best_rms:.5f}")
    return best_idx


def record_audio() -> Optional[str]:
    """
    Record one utterance from the microphone.

    Returns the path to the saved WAV file, or None if no speech was detected
    within MAX_WAIT_SECONDS (so the caller can skip STT / TTS entirely).
    """
    global _LAST_NOISE_RMS, _INPUT_DEVICE

    if _INPUT_DEVICE is None:
        _INPUT_DEVICE = _select_input_device()
    device = _INPUT_DEVICE

    print("Listening...")
    # Calibrate noise floor
    calibration = sd.rec(
        int(CALIBRATION_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=device,
    )
    sd.wait()
    noise_rms = float(np.sqrt(np.mean(calibration ** 2)))
    _LAST_NOISE_RMS = max(noise_rms, 0.0014)
    thr_start, thr_cont = _voice_thresholds(_LAST_NOISE_RMS)

    pre_buffer: deque[np.ndarray] = deque(maxlen=_PRE_ROLL_CHUNKS)
    frames: list[np.ndarray] = []
    speech_started = False
    speech_started_at: float = 0.0
    last_voice_at: float = 0.0
    above_streak = 0

    stream_kw = dict(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=CHUNK_SIZE,
        device=device,
    )

    with sd.InputStream(**stream_kw) as stream:
        started_at = time.monotonic()
        while True:
            now = time.monotonic()
            data, _ = stream.read(CHUNK_SIZE)
            chunk = data.copy()
            rms = float(np.sqrt(np.mean(chunk ** 2)))

            if speech_started:
                voice_now = rms >= thr_cont
            else:
                above_streak = above_streak + 1 if rms >= thr_start else 0
                voice_now = above_streak >= _VOICE_START_STREAK

            if not speech_started:
                pre_buffer.append(chunk)
                if voice_now:
                    speech_started = True
                    speech_started_at = now
                    last_voice_at = now
                    frames.extend(list(pre_buffer))
                    frames.append(chunk)
                elif now - started_at >= MAX_WAIT_SECONDS:
                    print("No speech detected — listening again.")
                    return None
            else:
                frames.append(chunk)
                if voice_now:
                    last_voice_at = now

                elapsed = now - speech_started_at
                silence = now - last_voice_at
                if (elapsed >= MIN_SPEECH_SECONDS and silence >= SILENCE_HANGOVER) or elapsed >= MAX_RECORD_SECONDS:
                    break

    recording = np.concatenate(frames, axis=0)
    peak = float(np.max(np.abs(recording)))
    if 0.0 < peak < 0.18:
        recording = np.clip(recording * (0.18 / peak), -1.0, 1.0)

    audio_int16 = np.int16(recording * 32767)
    wav_write(str(AUDIO_TMP), SAMPLE_RATE, audio_int16)

    rms = float(np.sqrt(np.mean(recording ** 2)))
    print(f"Captured audio  rms={rms:.5f}  peak={peak:.5f}")
    return str(AUDIO_TMP)


def detect_voice_interrupt() -> bool:
    """Return True if a loud sound (barge-in) is detected on the mic right now."""
    sample = sd.rec(
        int(0.2 * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        device=_INPUT_DEVICE,
    )
    sd.wait()
    rms = float(np.sqrt(np.mean(sample ** 2)))
    n = max(_LAST_NOISE_RMS, 0.003)
    threshold = min(n * 1.8, _ABS_START_MAX)
    threshold = max(threshold, 0.008)
    return rms >= threshold
