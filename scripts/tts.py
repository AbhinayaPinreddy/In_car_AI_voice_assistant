import asyncio
import os
import re
import tempfile
import time
import platform

import pygame
import edge_tts


# Best clear female neural voices
VOICES = [
    "en-IN-NeerjaNeural",   # Indian English Female
    "en-US-JennyNeural",    # US Female
    "en-GB-SoniaNeural",    # UK Female
]


def normalize_text(text: str) -> str:
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


async def save_tts(text: str, output_file: str, voice: str):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate="-5%",
        pitch="+0Hz",
    )
    await communicate.save(output_file)


def speak(text: str, should_interrupt=None):
    text = normalize_text(text)

    if not text:
        return False

    pygame.mixer.init()

    interrupted = False

    for voice in VOICES:
        try:
            fd, path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)

            asyncio.run(save_tts(text, path, voice))

            pygame.mixer.music.load(path)
            pygame.mixer.music.play()

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

            os.remove(path)

            return interrupted

        except Exception as e:
            print(f"TTS failed with {voice}: {e}")

    return False
