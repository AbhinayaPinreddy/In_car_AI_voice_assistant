"""LLM engine with conversation memory, OpenAI + HuggingFace fallback."""

from __future__ import annotations

from collections import deque
from typing import Optional

import requests

from config import (
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

_SYSTEM_PROMPT = (
    "You are a premium in-car voice assistant — think Siri meets Alexa, but smarter. "
    "Speak naturally, warmly, and confidently. "
    "Keep every response to 1–3 short sentences, voice-friendly (no bullet points, markdown, or URLs). "
    "Prioritise driving safety: never suggest the driver look at a screen. "
    "If a request is ambiguous, ask ONE short clarifying question."
)

# Sliding window of (role, content) pairs
_history: deque[dict] = deque(maxlen=LLM_MAX_HISTORY * 2)


def _build_messages(user_prompt: str) -> list[dict]:
    messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
    messages.extend(_history)
    messages.append({"role": "user", "content": user_prompt})
    return messages


def _record_exchange(user_prompt: str, assistant_reply: str) -> None:
    _history.append({"role": "user", "content": user_prompt})
    _history.append({"role": "assistant", "content": assistant_reply})


def _resolve_openai_endpoint() -> tuple[str, str]:
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


def _call_openai(user_prompt: str) -> Optional[str]:
    if not OPENAI_API_KEY:
        return None
    base, model = _resolve_openai_endpoint()
    try:
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
            },
            timeout=LLM_TIMEOUT,
        )
        if resp.status_code < 400:
            text = resp.json()["choices"][0]["message"]["content"].strip()
            if text:
                return text
    except Exception as exc:
        print(f"[LLM] OpenAI error: {exc}")
    return None


def _call_huggingface(user_prompt: str) -> Optional[str]:
    if not HF_API_TOKEN:
        return None
    # Build a minimal prompt string from history for HF (no chat endpoint)
    history_str = ""
    for msg in _history:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_str += f"{role}: {msg['content']}\n"
    prompt = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"{history_str}"
        f"User: {user_prompt}\nAssistant:"
    )
    try:
        resp = requests.post(
            f"https://api-inference.huggingface.co/models/{HF_MODEL}",
            headers={
                "Authorization": f"Bearer {HF_API_TOKEN}",
                "Content-Type": "application/json",
            },
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
                text = data[0]["generated_text"].strip()
                # Strip anything after a second "User:" line (hallucinated turns)
                text = text.split("User:")[0].strip()
                if text:
                    return text
    except Exception as exc:
        print(f"[LLM] HuggingFace error: {exc}")
    return None


def _local_fallback(prompt: str) -> str:
    t = prompt.lower()
    if any(g in t for g in ("hello", "hi ", "hey")):
        return "Hi! I am your in-car assistant. How can I help you?"
    if "how are you" in t:
        return "All systems go! What can I do for you?"
    if "what can you do" in t or t == "help":
        return "I can check weather, read headlines, manage your to-do list, and answer general questions."
    return "I am having trouble reaching the AI service. Try asking for weather, news, or your to-do list."


def ask_llm(prompt: str) -> str:
    if not prompt.strip():
        return "Please say that again."

    reply = _call_openai(prompt) or _call_huggingface(prompt) or _local_fallback(prompt)
    _record_exchange(prompt, reply)
    return reply


def clear_history() -> None:
    _history.clear()
