import requests
import os
from dotenv import load_dotenv

load_dotenv()

def get_news():
    api_key = os.getenv("NEWS_API_KEY")
    
    if not api_key:
        return "News API key is missing. Add NEWS_API_KEY to .env."

    url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={api_key}"

    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        return "I could not fetch news right now."

    data = response.json()

    articles = data.get("articles", [])[:5]
    if not articles:
        return "No news articles are available right now."

    titles = []
    for article in articles:
        title = article.get("title")
        if title:
            titles.append(title)

    if not titles:
        return "I could not read news headlines right now."

    short_titles = titles[:3]
    return "Here are the top headlines. " + ". ".join(short_titles) + "."