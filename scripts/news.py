"""Top headlines via NewsAPI."""

from __future__ import annotations

import re

import requests

from .config import NEWS_API_KEY

_BASE = "https://newsapi.org/v2/top-headlines"
_MAX_HEADLINES = 3


def _strip_source(title: str) -> str:
    """Remove ' - Source Name' suffix that NewsAPI appends to titles."""
    return re.sub(r"\s*-\s*[^-]{2,40}$", "", title).strip()


def get_news() -> str:
    if not NEWS_API_KEY:
        return "News is unavailable. Please add your NewsAPI key to the dot-env file."

    try:
        resp = requests.get(
            _BASE,
            params={"country": "us", "apiKey": NEWS_API_KEY, "pageSize": 10},
            timeout=10,
        )
    except requests.RequestException:
        return "I could not connect to the news service right now."

    if resp.status_code == 401:
        return "The news API key appears to be invalid."
    if resp.status_code != 200:
        return "I could not fetch the news right now."

    articles = resp.json().get("articles", [])
    titles = [
        _strip_source(a["title"])
        for a in articles
        if a.get("title") and a["title"] != "[Removed]"
    ][:_MAX_HEADLINES]

    if not titles:
        return "There are no news headlines available right now."

    joined = ". ".join(titles)
    return f"Here are today's top headlines. {joined}."
