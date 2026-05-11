import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from collections import deque
import time
from typing import Tuple

_LAST_NOISE_RMS = 0.0025

# Chunks above threshold required to start speech (rejects single-sample / fan / USB spikes).
_VOICE_START_STREAK = 4
# After speech starts, use a lower bar so words are not clipped (hysteresis).
_SPEECH_CONTINUE_RATIO = 0.72


def _voice_thresholds(noise_rms: float) -> Tuple[float, float]:
    """Return (start_threshold, continue_threshold) from calibrated noise floor."""
    n = max(float(noise_rms), 0.0014)
    # Strong margin over noise + absolute floor so "digital silence" still needs real speech.
    start = max(n * 3.4, n + 0.0052, 0.0062)
    start = min(start, 0.038)
    cont = max(start * _SPEECH_CONTINUE_RATIO, n * 2.1, 0.0045)
    return start, cont


def record_audio():
    global _LAST_NOISE_RMS

    fs = 16000
    chunk_size = 1024
    max_wait_seconds = 6.0
    max_record_seconds = 12.0
    silence_hangover_seconds = 0.9
    min_speech_seconds = 0.35
    pre_roll_chunks = 4

    print("Speak now...")
    calibration = sd.rec(int(0.75 * fs), samplerate=fs, channels=1, dtype="float32")
    sd.wait()
    noise_rms = float(np.sqrt(np.mean(np.square(calibration))))
    _LAST_NOISE_RMS = max(noise_rms, 0.0014)
    thr_start, thr_continue = _voice_thresholds(_LAST_NOISE_RMS)

    pre_buffer = deque(maxlen=pre_roll_chunks)
    frames = []
    speech_started = False
    speech_started_at = None
    last_voice_at = None
    above_streak = 0

    with sd.InputStream(samplerate=fs, channels=1, dtype="float32", blocksize=chunk_size) as stream:
        started_at = time.monotonic()
        while True:
            now = time.monotonic()
            data, _ = stream.read(chunk_size)
            chunk = data.copy()
            rms = float(np.sqrt(np.mean(np.square(chunk))))
            if speech_started:
                voice_detected = rms >= thr_continue
            else:
                if rms >= thr_start:
                    above_streak += 1
                else:
                    above_streak = 0
                voice_detected = above_streak >= _VOICE_START_STREAK

            if not speech_started:
                pre_buffer.append(chunk)
                if voice_detected:
                    speech_started = True
                    speech_started_at = now
                    last_voice_at = now
                    frames.extend(list(pre_buffer))
                    frames.append(chunk)
            else:
                frames.append(chunk)
                if voice_detected:
                    last_voice_at = now

                enough_speech = (now - speech_started_at) >= min_speech_seconds
                silence_timeout = (now - last_voice_at) >= silence_hangover_seconds
                max_record_reached = (now - speech_started_at) >= max_record_seconds
                if (enough_speech and silence_timeout) or max_record_reached:
                    break

            if not speech_started and (now - started_at) >= max_wait_seconds:
                # Do not capture seconds of silence: Whisper will hallucinate text.
                print("No speech detected (quiet input).")
                return None

    recording = np.concatenate(frames, axis=0)
    rms = float(np.sqrt(np.mean(np.square(recording))))
    peak = float(np.max(np.abs(recording)))
    if 0.0 < peak < 0.18:
        recording = recording * (0.18 / peak)
        recording = np.clip(recording, -1.0, 1.0)

    audio_int16 = np.int16(recording * 32767)
    write("audio.wav", fs, audio_int16)

    print(f"Recording completed (level rms={rms:.5f}, peak={peak:.5f})")

    return "audio.wav"


def detect_voice_interrupt():
    fs = 16000
    sample = sd.rec(int(0.2 * fs), samplerate=fs, channels=1, dtype="float32")
    sd.wait()
    rms = float(np.sqrt(np.mean(np.square(sample))))
    n = max(_LAST_NOISE_RMS, 0.0014)
    # Slightly easier than record start so barge-in still works, but above idle noise.
    threshold = max(n * 2.9, n + 0.0048, 0.0075)
    threshold = min(threshold, 0.042)
    return rms >= threshold