import asyncio
import os
import re
import tempfile
import time

# Neural TTS (natural female, smooth playback). Requires network once per reply.
# Set CAR_VOICE_ENGINE=pyttsx3 to force legacy offline engine only.
_EDGE_VOICES = (
    "en-IN-NeerjaNeural",  # Indian English, female
    "en-US-JennyNeural",  # US English, female
    "en-GB-SoniaNeural",  # UK English, female
)

_engine = None


def _get_pyttsx3_engine():
    global _engine
    if _engine is None:
        import pyttsx3

        eng = pyttsx3.init()
        eng.setProperty("rate", 138)
        eng.setProperty("volume", 1.0)
        _select_pyttsx3_voice(eng)
        _engine = eng
    return _engine


def _select_pyttsx3_voice(engine):
    voices = engine.getProperty("voices")
    if not voices:
        return

    female_tokens = (
        ("female", 200),
        ("zira", 220),
        ("hazel", 200),
        ("samantha", 200),
        ("victoria", 190),
        ("karen", 190),
        ("heera", 220),
        ("jenny", 160),
        ("aria", 150),
        ("priya", 180),
    )
    male_tokens = (
        "david",
        "mark",
        "george",
        "james",
        "brian",
        "ravi",
        "hemant",
    )
    quality_tokens = (
        ("onecore", 55),
        ("neural", 50),
        ("en-in", 18),
    )

    def score_voice(voice) -> int:
        text = f"{voice.id} {voice.name}".lower()
        s = 0
        for tok, w in female_tokens:
            if tok in text:
                s += w
        for tok in male_tokens:
            if tok in text:
                s -= 280
        if re.search(r"\bmale\b", text) and "female" not in text:
            s -= 280
        for tok, w in quality_tokens:
            if tok in text:
                s += w
        return s

    ranked = sorted(voices, key=lambda v: score_voice(v), reverse=True)
    best = ranked[0]
    if score_voice(best) < 0:
        best = max(
            voices,
            key=lambda v: sum(w for t, w in female_tokens if t in f"{v.id} {v.name}".lower()),
        )
    engine.setProperty("voice", best.id)


def _normalize_speech_text(text: str) -> str:
    t = text.replace("|", ", ").replace("\r\n", "\n").replace("\n", " ").strip()
    t = re.sub(r"\s+", " ", t)
    for ch in "<>":
        t = t.replace(ch, " ")
    return t


def _edge_text_chunks(text: str, max_chars: int = 4800) -> list[str]:
    """Edge is reliable under a few thousand chars per request; keeps one file per chunk."""
    text = _normalize_speech_text(text)
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    out: list[str] = []
    rest = text
    while rest:
        if len(rest) <= max_chars:
            out.append(rest.strip())
            break
        cut = rest.rfind(" ", 0, max_chars)
        if cut <= 0:
            cut = max_chars
        out.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    return [x for x in out if x]


async def _edge_save(text: str, out_path: str, voice: str) -> None:
    import edge_tts

    comm = edge_tts.Communicate(text, voice, rate="-2%")
    await comm.save(out_path)


def _ordered_edge_voices() -> tuple[str, ...]:
    order: list[str] = []
    custom = os.environ.get("CAR_EDGE_VOICE", "").strip()
    if custom:
        order.append(custom)
    for v in _EDGE_VOICES:
        if v not in order:
            order.append(v)
    return tuple(order)


def _speak_edge_neural(text: str, should_interrupt) -> bool:
    import pygame

    interrupted = False
    voices_to_try = _ordered_edge_voices()

    try:
        pygame.mixer.init()
    except Exception:
        raise RuntimeError("pygame mixer init failed")

    pieces = _edge_text_chunks(text)
    for piece in pieces:
        if interrupted:
            break
        last_error = None
        saved_path = None
        for v in voices_to_try:
            fd, path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            try:
                asyncio.run(_edge_save(piece, path, v))
                saved_path = path
                break
            except Exception as e:
                last_error = e
                try:
                    os.unlink(path)
                except OSError:
                    pass
                path = None
        if saved_path is None:
            raise last_error or RuntimeError("edge-tts failed")

        path = saved_path
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            # Wait until playback actually starts (avoids a false "not busy" race).
            for _ in range(50):
                if pygame.mixer.music.get_busy():
                    break
                time.sleep(0.01)
            next_check = time.monotonic() + 0.22
            while pygame.mixer.music.get_busy():
                pygame.time.wait(20)
                if should_interrupt and time.monotonic() >= next_check:
                    try:
                        if should_interrupt():
                            pygame.mixer.music.stop()
                            interrupted = True
                            break
                    except Exception:
                        pass
                    next_check = time.monotonic() + 0.22
        finally:
            try:
                pygame.mixer.music.stop()
                um = getattr(pygame.mixer.music, "unload", None)
                if callable(um):
                    um()
            except Exception:
                pass
            try:
                os.unlink(path)
            except OSError:
                pass

    return interrupted


def _speak_pyttsx3(text: str, should_interrupt) -> bool:
    engine = _get_pyttsx3_engine()
    interrupted = False
    normalized = _normalize_speech_text(text)
    if not normalized:
        return False
    try:
        engine.stop()
        engine.say(normalized)
        engine.startLoop(False)
        next_check_at = time.monotonic() + 0.22
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
                next_check_at = time.monotonic() + 0.22
            time.sleep(0.006)
        try:
            engine.endLoop()
        except Exception:
            pass
    except Exception:
        pass
    return interrupted


def speak(text, should_interrupt=None):
    if not text:
        return False
    if os.environ.get("CAR_VOICE_ENGINE", "").strip().lower() == "pyttsx3":
        return _speak_pyttsx3(text, should_interrupt)

    try:
        return _speak_edge_neural(text, should_interrupt)
    except Exception:
        return _speak_pyttsx3(text, should_interrupt)
