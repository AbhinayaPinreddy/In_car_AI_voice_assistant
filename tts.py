import pyttsx3
import time

engine = pyttsx3.init()
engine.setProperty("rate", 170)
engine.setProperty("volume", 1.0)


def _select_preferred_voice():
    voices = engine.getProperty("voices")
    if not voices:
        return

    # Prefer Indian English female voices when available.
    preferred_tokens = [
        "heera",
        "india",
        "indian",
        "en-in",
        "zira",
        "female",
    ]
    selected = None
    for voice in voices:
        text = f"{voice.id} {voice.name}".lower()
        if any(token in text for token in preferred_tokens):
            selected = voice.id
            break

    if not selected:
        selected = voices[0].id

    engine.setProperty("voice", selected)


_select_preferred_voice()


def _prepare_chunks(text, max_chunk_len=220):
    normalized = text.replace("|", ". ").replace("\n", ". ").strip()
    parts = [p.strip() for p in normalized.split(".") if p.strip()]
    chunks = []
    current = ""
    for part in parts:
        candidate = f"{current}. {part}".strip(". ").strip() if current else part
        if len(candidate) <= max_chunk_len:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = part
    if current:
        chunks.append(current)
    return chunks if chunks else [text]


def speak(text, should_interrupt=None):
    if not text:
        return False
    interrupted = False
    try:
        engine.stop()
        for chunk in _prepare_chunks(text):
            engine.say(chunk)
            engine.startLoop(False)
            next_check_at = time.monotonic() + 0.25
            while engine.isBusy():
                engine.iterate()
                if should_interrupt and time.monotonic() >= next_check_at:
                    try:
                        if should_interrupt():
                            interrupted = True
                            engine.stop()
                            break
                    except Exception:
                        pass
                    next_check_at = time.monotonic() + 0.25
                time.sleep(0.01)
            try:
                engine.endLoop()
            except Exception:
                pass
            if interrupted:
                break
    except Exception:
        # Keep assistant running even if TTS fails.
        pass
    return interrupted