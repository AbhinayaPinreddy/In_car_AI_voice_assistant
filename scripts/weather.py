"""Weather queries via OpenWeatherMap."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

import requests

from .config import DEFAULT_CITY, OPENWEATHER_API_KEY

_BASE = "https://api.openweathermap.org/data/2.5"
_STOPWORDS = {"today", "tomorrow", "please", "now", "tonight", "too", "the"}


def _clean_city(raw: Optional[str], fallback: str = DEFAULT_CITY) -> str:
    if not raw:
        return fallback
    clean = re.sub(r"[^a-zA-Z\s-]", " ", raw).strip().lower()
    words = [w for w in clean.split() if w and w not in _STOPWORDS]
    if not words:
        return fallback
    return " ".join(words[:3]).title()


def _api_key_missing() -> str:
    return "Weather is unavailable. Please add your OpenWeatherMap API key to the dot-env file."


def get_weather(city: Optional[str]) -> str:
    if not OPENWEATHER_API_KEY:
        return _api_key_missing()

    city = _clean_city(city)
    try:
        resp = requests.get(
            f"{_BASE}/weather",
            params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"},
            timeout=10,
        )
    except requests.RequestException:
        return f"I could not connect to the weather service right now."

    if resp.status_code == 404:
        return f"I could not find a place called {city}. Please try again."
    if resp.status_code != 200:
        return f"Weather for {city} is unavailable right now."

    data = resp.json()
    temp = round(data["main"]["temp"])
    feels = round(data["main"]["feels_like"])
    desc = data["weather"][0]["description"]
    humidity = data["main"]["humidity"]
    wind = round(data.get("wind", {}).get("speed", 0) * 3.6)  # m/s → km/h

    return (
        f"In {city} it is {temp}°C, feels like {feels}°C, with {desc}. "
        f"Humidity {humidity}%, wind {wind} km/h."
    )


def will_it_rain_today(city: Optional[str]) -> str:
    if not OPENWEATHER_API_KEY:
        return _api_key_missing()

    city = _clean_city(city)
    try:
        resp = requests.get(
            f"{_BASE}/forecast",
            params={"q": city, "appid": OPENWEATHER_API_KEY, "units": "metric"},
            timeout=10,
        )
    except requests.RequestException:
        return "I could not connect to the weather service right now."

    if resp.status_code != 200:
        return f"Forecast for {city} is unavailable right now."

    items = resp.json().get("list", [])
    if not items:
        return f"No forecast data available for {city}."

    today = datetime.now(timezone.utc).date()
    today_items = [
        it for it in items
        if datetime.fromtimestamp(it["dt"], tz=timezone.utc).date() == today
    ] or items[:8]  # fallback: first 24 h if no exact date match

    max_pop = 0.0
    rain_slots = 0
    temps: list[float] = []
    weather_mains: list[str] = []

    for it in today_items:
        pop = float(it.get("pop") or 0)
        max_pop = max(max_pop, pop)
        main = (it.get("weather") or [{}])[0].get("main", "").lower()
        weather_mains.append(main)

        rain_flag = (
            ("rain" in it and it["rain"])
            or ("snow" in it and it["snow"])
            or main in {"rain", "drizzle", "thunderstorm"}
            or pop >= 0.4
        )
        if rain_flag:
            rain_slots += 1

        temp = (it.get("main") or {}).get("temp")
        if isinstance(temp, (int, float)):
            temps.append(temp)

    pop_pct = int(round(max_pop * 100))
    likely = rain_slots >= 1 or max_pop >= 0.4 or "rain" in weather_mains

    temp_part = ""
    if temps:
        temp_part = f" Temperatures between {min(temps):.0f} and {max(temps):.0f}°C."

    if likely:
        return f"Yes, rain is possible in {city} today — up to {pop_pct}% chance.{temp_part}"
    return f"Rain looks unlikely in {city} today — only {pop_pct}% chance.{temp_part}"
