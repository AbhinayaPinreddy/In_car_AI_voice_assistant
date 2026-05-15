"""Text-to-speech via edge_tts (neural voices) with pygame playback and barge-in."""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
import time

import edge_tts
import pygame

from config import TTS_VOICES

pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
pygame.mixer.init()


def _normalize(text: str) -> str:
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


async def _generate_mp3(text: str, voice: str, path: str) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice, rate="-5%", pitch="+0Hz")
    await communicate.save(path)


def speak(text: str, should_interrupt=None) -> bool:
    """
    Synthesise and play *text*.

    - Tries each voice in TTS_VOICES until one works.
    - Polls should_interrupt() every 50 ms; stops early and returns True if triggered.
    - Returns False on normal completion.
    """
    text = _normalize(text)
    if not text:
        return False

    for voice in TTS_VOICES:
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        try:
            asyncio.run(_generate_mp3(text, voice, path))

            pygame.mixer.music.load(path)
            pygame.mixer.music.play()

            interrupted = False
            while pygame.mixer.music.get_busy():
                if should_interrupt and should_interrupt():
                    pygame.mixer.music.stop()
                    interrupted = True
                    break
                time.sleep(0.05)

            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass

            return interrupted

        except Exception as exc:
            print(f"[TTS] {voice} failed: {exc}")
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    print("[TTS] All voices failed — skipping audio output.")
    return False
