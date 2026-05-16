"""
LLM engine — streaming OpenAI responses with conversation memory.

Streaming cuts time-to-first-audio from ~4 s to ~1 s:
  - We accumulate tokens until a sentence boundary (.!?)
  - Yield each sentence to the caller as it arrives
  - The caller (main.py) feeds sentences to TTS immediately

Falls back to HuggingFace (non-streaming) then local canned replies.
"""

from __future__ import annotations

import platform
from collections import deque
from typing import Generator, Optional

import requests

if platform.system() == "Windows":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from .config import (
    HF_API_TOKEN,
    HF_MODEL,
    LLM_MAX_HISTORY,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)

_SYSTEM_PROMPT = """You are ARIA — an Advanced Road Intelligence Assistant built into the car's dashboard.
You speak directly to the driver through the car speakers. Your voice is calm, warm, and confident — like a trusted co-pilot.

RESPONSE RULES (strictly follow every rule):
1. ALWAYS respond in plain spoken English — zero markdown, zero bullet points, zero numbered lists, zero URLs, zero code.
2. Keep every reply to 1–3 short, natural sentences. Never write a paragraph.
3. Each sentence must sound smooth when read aloud — use contractions (it's, you'll, I'd), avoid jargon.
4. Never start a sentence with "Certainly!", "Of course!", "Absolutely!" or similar hollow filler words.
5. Never suggest the driver look at a phone, screen, or read anything — they are driving.
6. If you don't know something, say so simply and offer an alternative in one sentence.
7. If the request is unclear, ask exactly ONE short clarifying question and nothing else.
8. Never repeat the user's question back to them.
9. Match the driver's energy — casual questions get casual answers, urgent questions get direct answers.
10. End responses cleanly. Don't trail off with "Is there anything else I can help you with?"

PERSONALITY:
- Confident but never arrogant.
- Warm but never sycophantic.
- Precise but never robotic.
- Think less Siri, more the smartest person you know riding shotgun.

SAFETY PRIORITY: If the driver seems distressed, immediately acknowledge their concern and keep the response under 1 sentence."""

_history: deque[dict] = deque(maxlen=LLM_MAX_HISTORY * 2)


def _build_messages(user_prompt: str) -> list[dict]:
    msgs = [{"role": "system", "content": _SYSTEM_PROMPT}]
    msgs.extend(_history)
    msgs.append({"role": "user", "content": user_prompt})
    return msgs


def _record(user_prompt: str, reply: str) -> None:
    _history.append({"role": "user", "content": user_prompt})
    _history.append({"role": "assistant", "content": reply})


def _resolve_endpoint() -> tuple[str, str]:
    base = OPENAI_BASE_URL.strip()
    model = OPENAI_MODEL
    if not base:
        if OPENAI_API_KEY.startswith("sk-or-v1"):
            base = "https://openrouter.ai/api/v1"
            if "/" not in model:
                model = f"openai/{model}"
        else:
            base = "https://api.openai.com/v1"
    return base, model


def _stream_openai(user_prompt: str) -> Generator[str, None, None]:
    """
    Yield complete sentences from the OpenAI streaming API.
    Raises on any error so the caller can fall back.
    """
    base, model = _resolve_endpoint()
    resp = requests.post(
        f"{base}/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Car Voice Assistant",
        },
        json={
            "model": model,
            "messages": _build_messages(user_prompt),
            "temperature": LLM_TEMPERATURE,
            "max_tokens": LLM_MAX_TOKENS,
            "stream": True,
        },
        stream=True,
        timeout=LLM_TIMEOUT,
    )
    resp.raise_for_status()

    buf = ""
    for raw_line in resp.iter_lines():
        if not raw_line:
            continue
        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if payload == "[DONE]":
            break
        try:
            import json
            delta = json.loads(payload)["choices"][0]["delta"].get("content", "")
        except Exception:
            continue
        if not delta:
            continue
        buf += delta
        # Yield at sentence boundaries so TTS can start immediately
        while True:
            for sep in (".", "!", "?"):
                idx = buf.find(sep)
                if idx != -1:
                    sentence = buf[: idx + 1].strip()
                    buf = buf[idx + 1 :]
                    if sentence:
                        yield sentence
                    break
            else:
                break

    if buf.strip():
        yield buf.strip()


def _call_huggingface(user_prompt: str) -> Optional[str]:
    if not HF_API_TOKEN:
        return None
    history_str = "".join(
        f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}\n"
        for m in _history
    )
    prompt = f"{_SYSTEM_PROMPT}\n\n{history_str}User: {user_prompt}\nAssistant:"
    try:
        resp = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
            headers={"Authorization": f"Bearer {HF_API_TOKEN}", "Content-Type": "application/json"},
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": LLM_MAX_TOKENS,
                    "temperature": LLM_TEMPERATURE,
                    "return_full_text": False,
                },
            },
            timeout=LLM_TIMEOUT + 10,
        )
        if resp.status_code < 400:
            data = resp.json()
            if isinstance(data, list) and data and "generated_text" in data[0]:
                text = data[0]["generated_text"].strip().split("User:")[0].strip()
                if text:
                    return text
    except Exception as exc:
        print(f"[LLM] HuggingFace error: {exc}")
    return None


def _local_fallback(prompt: str) -> str:
    t = prompt.lower()
    if any(g in t for g in ("hello", "hi ", "hey")):
        return "Hey! I'm ARIA, your in-car assistant. What can I do for you?"
    if "how are you" in t:
        return "Running perfectly. What do you need?"
    if "what can you do" in t or t == "help":
        return "I can check weather, read you the news, manage your to-do list, and answer questions — all hands-free."
    if "who are you" in t or "your name" in t:
        return "I'm ARIA, your in-car voice assistant. Think of me as your co-pilot."
    return "I'm having trouble connecting right now. Try asking about weather, news, or your to-do list."


def ask_llm_stream(prompt: str) -> Generator[str, None, None]:
    """
    Yield sentences as they arrive from the LLM.
    Falls back to single-shot methods if streaming fails.
    """
    if not prompt.strip():
        yield "Please say that again."
        return

    sentences: list[str] = []

    if OPENAI_API_KEY:
        try:
            for sentence in _stream_openai(prompt):
                sentences.append(sentence)
                yield sentence
            if sentences:
                _record(prompt, " ".join(sentences))
                return
        except Exception as exc:
            print(f"[LLM] OpenAI stream error: {exc}")

    # Non-streaming fallbacks
    reply = _call_huggingface(prompt) or _local_fallback(prompt)
    _record(prompt, reply)
    yield reply


def ask_llm(prompt: str) -> str:
    """Blocking wrapper — returns full response as a single string."""
    return " ".join(ask_llm_stream(prompt))


def clear_history() -> None:
    _history.clear()
