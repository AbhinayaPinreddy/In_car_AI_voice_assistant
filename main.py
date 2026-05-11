from record_audio import record_audio
from record_audio import detect_voice_interrupt

from stt import speech_to_text

from llm_engine import ask_llm

from tts import speak

from weather import get_weather, will_it_rain_today

from news import get_news

from todo import add_task, get_tasks, delete_task, mark_task_done

DEFAULT_CITY = "Hyderabad"


def is_meaningful_query(query):
    letters = sum(ch.isalpha() for ch in query)
    return letters >= 3


def detect_intent(query):
    import re

    normalized = query
    normalized = normalized.replace("whether in", "weather in").replace("matter in", "weather in")
    normalized = normalized.replace("to-do", "todo").replace("to do", "todo")
    normalized = normalized.strip()

    if any(x in normalized for x in ["stop assistant", "exit", "quit", "goodbye"]):
        return "exit", None

    # Temperature questions should be treated as weather.
    m_temp = re.search(r"\b(temp|temperature)\b\s+in\s+([a-zA-Z\s-]+)", normalized)
    if m_temp:
        return "weather", m_temp.group(2).strip()
    if "weather in" in normalized:
        city = normalized.split("weather in", 1)[1].strip()
        return "weather", city if city else DEFAULT_CITY
    if "weather" in normalized:
        return "weather", DEFAULT_CITY

    # "rain" is often transcribed as "train" by STT.
    is_rain_query = ("rain" in normalized) or (
        "train" in normalized and " in " in normalized and any(x in normalized for x in ["today", "tomorrow"])
    )
    if is_rain_query:
        # e.g. "will it rain in kolkata today"
        m = re.search(r"(rain|train)\s+in\s+([a-zA-Z\s-]+)", normalized)
        city = m.group(1).strip() if m else DEFAULT_CITY
        city = m.group(2).strip() if m else DEFAULT_CITY
        return "rain_today", city
    if "news" in normalized or "headlines" in normalized:
        return "news", None

    # --- TODO / TASK intents (flexible voice phrasing) ---
    if re.search(r"\b(show|list|read)\b.*\b(todo|todos|task|tasks)\b", normalized) or normalized in {
        "show task",
        "show tasks",
        "my todo",
        "my todos",
        "todo list",
        "show my todo list",
    }:
        return "show_tasks", None

    add_match = re.search(r"\b(add|create|remember|remind)\b\s+(.*)", normalized)
    if add_match and ("task" in normalized or "tasks" in normalized or "todo" in normalized):
        task_text = add_match.group(2).strip()
        # remove common filler tails
        task_text = re.sub(r"\b(to|into)\b\s+(my\s+)?\b(todo|tasks?)\b\s*(list)?\.?$", "", task_text).strip()
        if task_text:
            return "add_task", task_text

    # Natural phrasing like: "add buy groceries" (without saying task/todo)
    add_simple = re.search(r"^add\s+(.+)$", normalized)
    if add_simple:
        task_text = add_simple.group(1).strip()
        task_text = re.sub(r"\b(to|into)\b\s+(my\s+)?\b(todo|tasks?)\b\s*(list)?\.?$", "", task_text).strip()
        if task_text:
            return "add_task", task_text

    del_match = re.search(r"\b(delete|remove)\b\s+(task\s*)?(\d+)\b", normalized)
    if del_match:
        return "delete_task", del_match.group(3)

    done_match = re.search(r"\b(mark|complete|done)\b\s+(task\s*)?(\d+)\b", normalized)
    if done_match:
        return "mark_done", done_match.group(3)

    return "llm", None


print("Assistant Started...")


while True:
    try:
        audio_file = record_audio()
        if not audio_file:
            response = "I could not hear you. Please speak a little louder."
            print("Assistant:", response)
            speak(response)
            continue

        query = speech_to_text(audio_file)
        query = query.strip().lower()

        if not query or not is_meaningful_query(query):
            response = "I did not catch that clearly. Please speak again."
            print("Assistant:", response)
            speak(response)
            continue

        print("You:", query)
        intent, value = detect_intent(query)

        if intent == "exit":
            response = "Drive safe. Stopping assistant now."
            print("Assistant:", response)
            speak(response)
            break

        if intent == "weather":
            response = get_weather(value)

        elif intent == "rain_today":
            response = will_it_rain_today(value)

        elif intent == "news":
            response = get_news()

        elif intent == "add_task":
            response = add_task(value)

        elif intent == "show_tasks":
            response = get_tasks()

        elif intent == "delete_task":
            response = delete_task(value)

        elif intent == "mark_done":
            response = mark_task_done(value)

        else:
            response = ask_llm(query)

    except Exception:
        response = "Something went wrong. Please try again."

    print("Assistant:", response)
    interrupted = speak(response, should_interrupt=detect_voice_interrupt)
    if interrupted:
        print("Assistant interrupted. Listening now...")
        continue

    if response == "Drive safe. Stopping assistant now.":
        break