import requests
import os
import re
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

_CITY_STOPWORDS = {"today", "tomorrow", "too", "please", "now", "tonight"}


def _normalize_city(city, fallback="Hyderabad"):
    clean = re.sub(r"[^a-zA-Z\s-]", " ", city or "").strip().lower()
    words = [w for w in clean.split() if w and w not in _CITY_STOPWORDS]
    if not words:
        return fallback
    # Keep it short in case of STT extra words.
    return " ".join(words[:3]).title()


def get_weather(city):
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Weather API key is missing. Add OPENWEATHER_API_KEY to .env."

    clean_city = _normalize_city(city, fallback="Hyderabad")

    url = f"https://api.openweathermap.org/data/2.5/weather?q={clean_city}&appid={api_key}&units=metric"

    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        return f"I could not fetch weather for {clean_city} right now."

    data = response.json()

    if "main" not in data:
        return "Unable to fetch weather"

    temp = data["main"]["temp"]

    desc = data["weather"][0]["description"]

    return f"The temperature in {clean_city} is {temp} degree Celsius with {desc}"


def will_it_rain_today(city):
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Weather API key is missing. Add OPENWEATHER_API_KEY to .env."

    clean_city = _normalize_city(city, fallback="Hyderabad")

    # 5 day / 3 hour forecast
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={clean_city}&appid={api_key}&units=metric"
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        return f"I could not fetch forecast for {clean_city} right now."

    data = response.json()
    items = data.get("list", [])
    if not items:
        return f"I could not fetch forecast for {clean_city} right now."

    # Determine "today" in UTC based on forecast timestamps.
    now_utc = datetime.now(timezone.utc).date()
    today_items = []
    for it in items:
        dt = it.get("dt")
        if not dt:
            continue
        day = datetime.fromtimestamp(dt, tz=timezone.utc).date()
        if day == now_utc:
            today_items.append(it)

    if not today_items:
        # If timezone mismatch, fall back to the first 8 slots (~24h)
        today_items = items[:8]

    rain_slots = 0
    max_pop = 0.0
    min_temp = None
    max_temp = None
    main_conditions = []

    for it in today_items:
        pop = float(it.get("pop", 0.0) or 0.0)
        max_pop = max(max_pop, pop)

        main = (it.get("weather") or [{}])[0].get("main", "")
        if main:
            main_conditions.append(main.lower())

        has_rain = False
        if "rain" in it and isinstance(it["rain"], dict) and it["rain"]:
            has_rain = True
        if "snow" in it and isinstance(it["snow"], dict) and it["snow"]:
            has_rain = True
        if main.lower() in {"rain", "drizzle", "thunderstorm"}:
            has_rain = True
        if pop >= 0.4:
            has_rain = True

        if has_rain:
            rain_slots += 1

        temp = (it.get("main") or {}).get("temp")
        if isinstance(temp, (int, float)):
            min_temp = temp if min_temp is None else min(min_temp, temp)
            max_temp = temp if max_temp is None else max(max_temp, temp)

    likely = rain_slots >= 1 or max_pop >= 0.4 or ("rain" in main_conditions)
    pop_pct = int(round(max_pop * 100))

    if min_temp is not None and max_temp is not None:
        temp_part = f" Temperatures around {min_temp:.0f} to {max_temp:.0f}°C."
    else:
        temp_part = ""

    if likely:
        return f"Yes, rain is possible in {clean_city} today (up to {pop_pct}% chance).{temp_part}"
    return f"Rain is unlikely in {clean_city} today (up to {pop_pct}% chance).{temp_part}"