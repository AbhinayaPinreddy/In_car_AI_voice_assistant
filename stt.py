from faster_whisper import WhisperModel

model = WhisperModel("base", device="cpu", compute_type="int8")


def speech_to_text(audio_path):
    if not audio_path:
        return ""

    segments, _ = model.transcribe(
        audio_path,
        vad_filter=True,
        no_speech_threshold=0.5,
        language="en"
    )

    filtered_chunks = []

    for segment in segments:
        chunk = segment.text.strip()
        if not chunk:
            continue
        no_speech_prob = getattr(segment, "no_speech_prob", 0.0)
        if no_speech_prob and no_speech_prob > 0.95:
            continue
        if any(ch.isalpha() for ch in chunk):
            filtered_chunks.append(chunk)

    return " ".join(filtered_chunks).strip()