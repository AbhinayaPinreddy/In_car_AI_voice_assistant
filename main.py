"""In-car AI voice assistant — entry point (run from project root)."""

from __future__ import annotations

import re
import traceback

from scripts.config import DEFAULT_CITY
from scripts.llm_engine import ask_llm, ask_llm_stream, clear_history
from scripts.news import get_news
from scripts.record_audio import detect_voice_interrupt, record_audio
from scripts.stt import speech_to_text
from scripts.todo import add_task, delete_task, get_tasks, mark_task_done
from scripts.tts import speak
from scripts.weather import get_weather, will_it_rain_today

# ── Intent detection ──────────────────────────────────────────────────────────

_EXIT_PHRASES = {"stop assistant", "exit", "quit", "goodbye", "bye", "shut down", "stop"}

_SHOW_TASKS_PHRASES = {
    "show task", "show tasks", "my todo", "my todos",
    "todo list", "show my todo list", "list tasks", "list my tasks",
}

_WEATHER_TYPOS = {
    "whether": "weather",
    "matter":  "weather",
    "wether":  "weather",
}

_STT_RAIN_ALTS = ("rain", "train")  # "train" is a common STT mishearing of "rain"


def _normalise(query: str) -> str:
    q = query.lower().strip()
    for typo, fix in _WEATHER_TYPOS.items():
        q = q.replace(typo + " in", fix + " in")
    q = q.replace("to-do", "todo").replace("to do", "todo")
    return q


def _is_meaningful(query: str) -> bool:
    return sum(ch.isalpha() for ch in query) >= 3


def detect_intent(query: str) -> tuple[str, str | None]:
    q = _normalise(query)

    # Exit
    if any(phrase in q for phrase in _EXIT_PHRASES) or q in _EXIT_PHRASES:
        return "exit", None

    # Temperature / weather
    m = re.search(r"\b(temp(?:erature)?)\b\s+in\s+([a-zA-Z\s-]+)", q)
    if m:
        return "weather", m.group(2).strip()

    if "weather in" in q:
        city = q.split("weather in", 1)[1].strip()
        return "weather", city or DEFAULT_CITY
    if "weather" in q:
        return "weather", DEFAULT_CITY

    # Rain
    has_rain_word = any(w in q for w in _STT_RAIN_ALTS)
    if has_rain_word:
        if "train" in q and not any(t in q for t in ("today", "tomorrow", " in ")):
            pass  # real train question, not rain
        else:
            m = re.search(r"(?:rain|train)\s+in\s+([a-zA-Z\s-]+)", q)
            city = m.group(1).strip() if m else DEFAULT_CITY
            return "rain_today", city

    # News
    if "news" in q or "headlines" in q:
        return "news", None

    # Tasks — show
    if re.search(r"\b(show|list|read)\b.*\b(todo|todos|task|tasks)\b", q) or q in _SHOW_TASKS_PHRASES:
        return "show_tasks", None

    # Tasks — add (explicit: "add/create/remember X task/todo")
    m = re.search(r"\b(add|create|remember|remind)\b\s+(.*)", q)
    if m and re.search(r"\b(task|tasks|todo|todos)\b", q):
        task = m.group(2)
        task = re.sub(r"\b(?:to|into)\b\s+(?:my\s+)?\b(?:todo|tasks?)\b\s*(?:list)?\.?$", "", task).strip()
        if task:
            return "add_task", task

    # Tasks — add (implicit: "add X" without task keyword)
    m = re.match(r"^add\s+(.+)$", q)
    if m:
        task = re.sub(r"\b(?:to|into)\b\s+(?:my\s+)?\b(?:todo|tasks?)\b\s*(?:list)?\.?$", "", m.group(1)).strip()
        if task:
            return "add_task", task

    # Tasks — delete / mark done
    m = re.search(r"\b(?:delete|remove)\b\s+(?:task\s*)?(\d+)\b", q)
    if m:
        return "delete_task", m.group(1)

    m = re.search(r"\b(?:mark|complete|done)\b\s+(?:task\s*)?(\d+)\b", q)
    if m:
        return "mark_done", m.group(1)

    # Clear conversation memory
    if re.search(r"\b(clear|reset)\b.*\b(history|memory|context|conversation)\b", q):
        return "clear_history", None

    return "llm", None


# ── Response dispatcher ───────────────────────────────────────────────────────

def _dispatch_instant(intent: str, value: str | None) -> str | None:
    """Return a ready string for non-LLM intents, or None if it's an LLM query."""
    if intent == "weather":
        return get_weather(value)
    if intent == "rain_today":
        return will_it_rain_today(value)
    if intent == "news":
        return get_news()
    if intent == "add_task":
        return add_task(value or "")
    if intent == "show_tasks":
        return get_tasks(show_done=False)
    if intent == "delete_task":
        return delete_task(value or "")
    if intent == "mark_done":
        return mark_task_done(value or "")
    if intent == "clear_history":
        clear_history()
        return "Conversation memory cleared."
    return None  # LLM — use streaming path


# ── Main loop ─────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 50)
    print("  In-Car AI Voice Assistant — ready")
    print("  Say 'goodbye' or 'exit' to stop.")
    print("=" * 50)

    while True:
        try:
            audio_path = record_audio()
            if not audio_path:
                continue

            query = speech_to_text(audio_path).strip().lower()

            if not query or not _is_meaningful(query):
                response = "I did not catch that. Please try again."
                print(f"Assistant: {response}")
                speak(response)
                continue

            print(f"\nYou: {query}")
            intent, value = detect_intent(query)

            if intent == "exit":
                response = "Drive safe. Goodbye!"
                print(f"Assistant: {response}")
                speak(response)
                break

            # Non-LLM intents return instantly — speak the whole response
            response = _dispatch_instant(intent, value)
            if response is not None:
                print(f"Assistant: {response}")
                speak(response, should_interrupt=detect_voice_interrupt)
                continue

            # LLM intent — stream sentences to TTS as they arrive
            print("Assistant: ", end="", flush=True)
            full_parts: list[str] = []
            for sentence in ask_llm_stream(query):
                print(sentence, end=" ", flush=True)
                full_parts.append(sentence)
                interrupted = speak(sentence, should_interrupt=detect_voice_interrupt)
                if interrupted:
                    print("\n(Interrupted — listening…)")
                    break
            print()
            continue

        except KeyboardInterrupt:
            print("\nStopped by user.")
            break
        except Exception:
            traceback.print_exc()
            response = "Something went wrong. Please try again."
            print(f"Assistant: {response}")
            speak(response)


if __name__ == "__main__":
    main()
