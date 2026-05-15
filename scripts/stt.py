"""Speech-to-text using faster-whisper with lazy model loading."""

from __future__ import annotations

from typing import Optional

from config import WHISPER_DEVICE, WHISPER_MODEL

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        print(f"Loading Whisper model '{WHISPER_MODEL}' on {WHISPER_DEVICE}…")
        _model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type="int8")
        print("Whisper ready.")
    return _model


def speech_to_text(audio_path: Optional[str]) -> str:
    """Transcribe audio file to text. Returns empty string on failure or silence."""
    if not audio_path:
        return ""

    model = _get_model()

    segments, _ = model.transcribe(
        audio_path,
        language="en",
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=300, threshold=0.50),
        no_speech_threshold=0.72,
        compression_ratio_threshold=2.6,
        condition_on_previous_text=False,
        beam_size=5,
    )

    chunks: list[str] = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        no_speech_prob = getattr(seg, "no_speech_prob", 0.0) or 0.0
        if no_speech_prob > 0.82:
            continue
        if any(ch.isalpha() for ch in text):
            chunks.append(text)

    return " ".join(chunks).strip()
