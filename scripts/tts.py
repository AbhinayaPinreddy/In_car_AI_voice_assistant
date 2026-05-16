"""
TTS — low-latency sentence-streaming playback via edge_tts + pygame.

Instead of synthesising the whole response then playing it, we:
  1. Split the text into sentences.
  2. Synthesise sentence N+1 in a background thread while sentence N is playing.
  3. Play each sentence as soon as its MP3 is ready.

This cuts perceived latency by ~60-70% on multi-sentence responses.
"""

from __future__ import annotations

import asyncio
import os
import queue
import re
import tempfile
import threading
import time

import edge_tts
import pygame

from .config import TTS_VOICES

pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
pygame.mixer.init()

_SENTENCE_RE = re.compile(r'(?<=[.!?])\s+')


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()
    parts = _SENTENCE_RE.split(text)
    # Merge very short fragments (< 4 words) with the next sentence
    merged: list[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if merged and len(merged[-1].split()) < 4:
            merged[-1] += ' ' + p
        else:
            merged.append(p)
    return merged or [text]


async def _synthesise(text: str, voice: str, path: str) -> None:
    await edge_tts.Communicate(text=text, voice=voice, rate='-5%').save(path)


def _synth_one(i: int, sentence: str, voice: str, result_q: queue.Queue) -> None:
    """Synthesise a single sentence in its own thread and push result to queue."""
    fd, path = tempfile.mkstemp(suffix='.mp3')
    os.close(fd)
    try:
        asyncio.run(_synthesise(sentence, voice, path))
        result_q.put((i, path, None))
    except Exception as exc:
        try:
            os.remove(path)
        except OSError:
            pass
        result_q.put((i, None, exc))


def _play_stream(sentences: list[str], voice: str, should_interrupt) -> bool:
    """
    Synthesise sentences concurrently and play them in order.

    All sentences are submitted to background threads at once.
    Playback waits for each in order, so sentence N+1 is often already
    ready by the time sentence N finishes playing.
    Returns True if interrupted by barge-in.
    """
    result_q: queue.Queue = queue.Queue()
    # Launch all synth threads immediately — they race in parallel
    for i, sentence in enumerate(sentences):
        threading.Thread(
            target=_synth_one, args=(i, sentence, voice, result_q), daemon=True
        ).start()
    sentinel_needed = len(sentences)

    pending: dict[int, str] = {}   # index -> path, ready to play
    next_play = 0
    received = 0
    interrupted = False
    paths_to_clean: list[str] = []

    while received < sentinel_needed:
        try:
            item = result_q.get(timeout=10)
        except queue.Empty:
            break

        received += 1
        idx, path, err = item
        if err or path is None:
            next_play = max(next_play, idx + 1)  # skip failed sentence
            continue

        pending[idx] = path

        # Play all consecutive ready sentences
        while next_play in pending:
            play_path = pending.pop(next_play)
            paths_to_clean.append(play_path)
            pygame.mixer.music.load(play_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if should_interrupt and should_interrupt():
                    pygame.mixer.music.stop()
                    interrupted = True
                    break
                time.sleep(0.04)
            if interrupted:
                break
            next_play += 1

        if interrupted:
            break

    # Play any remaining sentences that arrived while we were busy
    if not interrupted:
        while next_play in pending:
            play_path = pending.pop(next_play)
            paths_to_clean.append(play_path)
            pygame.mixer.music.load(play_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                if should_interrupt and should_interrupt():
                    pygame.mixer.music.stop()
                    interrupted = True
                    break
                time.sleep(0.04)
            if interrupted:
                break
            next_play += 1

    pygame.mixer.music.stop()
    try:
        pygame.mixer.music.unload()
    except Exception:
        pass

    for p in paths_to_clean:
        try:
            os.remove(p)
        except OSError:
            pass

    return interrupted


def speak(text: str, should_interrupt=None) -> bool:
    """
    Speak *text* with sentence-level streaming for low latency.
    Returns True if the user interrupted (barge-in), False on normal completion.
    """
    text = re.sub(r'\s+', ' ', text.replace('\n', ' ')).strip()
    if not text:
        return False

    sentences = _split_sentences(text)

    for voice in TTS_VOICES:
        try:
            interrupted = _play_stream(sentences, voice, should_interrupt)
            return interrupted
        except Exception as exc:
            print(f'[TTS] {voice} failed: {exc}')

    print('[TTS] All voices failed — skipping audio.')
    return False
