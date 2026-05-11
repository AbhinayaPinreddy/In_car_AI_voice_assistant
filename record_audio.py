import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from collections import deque
import time

_LAST_NOISE_RMS = 0.0025


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
    calibration = sd.rec(int(0.6 * fs), samplerate=fs, channels=1, dtype="float32")
    sd.wait()
    noise_rms = float(np.sqrt(np.mean(np.square(calibration))))
    _LAST_NOISE_RMS = max(noise_rms, 0.0012)
    voice_threshold = min(max(_LAST_NOISE_RMS * 1.9, 0.0032), 0.015)

    pre_buffer = deque(maxlen=pre_roll_chunks)
    frames = []
    speech_started = False
    speech_started_at = None
    last_voice_at = None

    with sd.InputStream(samplerate=fs, channels=1, dtype="float32", blocksize=chunk_size) as stream:
        started_at = time.monotonic()
        while True:
            now = time.monotonic()
            data, _ = stream.read(chunk_size)
            chunk = data.copy()
            rms = float(np.sqrt(np.mean(np.square(chunk))))
            voice_detected = rms >= voice_threshold

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
                # Fall back to fixed short capture so low-volume users are still transcribed.
                fallback = sd.rec(int(4.0 * fs), samplerate=fs, channels=1, dtype="float32")
                sd.wait()
                frames = [fallback]
                speech_started = True
                break

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
    threshold = min(max(_LAST_NOISE_RMS * 2.2, 0.0035), 0.02)
    return rms >= threshold