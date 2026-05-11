# Branded In-Car Voice Assistant (Local Prototype)

This project records your voice, transcribes it with Whisper, routes requests to "skills", and speaks back.

Implemented skills:
- Top news (`get_news`)
- Weather (`get_weather`)
- Todo queries (`add_task`, `get_tasks`)
- Open-question answers via LLM API fallback

## 1) Setup

Create and activate virtualenv (if not already):

```powershell
python -m venv venv
.\venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## 2) Configure API keys

Use `.env` file in project root:

```powershell
OPENWEATHER_API_KEY=your_openweather_key
NEWS_API_KEY=your_newsapi_key
OPENAI_API_KEY=your_openai_key
HF_API_TOKEN=your_huggingface_token
```

For general open questions, set at least one of:
- `OPENAI_API_KEY` (recommended), or
- `HF_API_TOKEN` for Hugging Face Inference API.

You can get keys from:
- OpenWeather: https://openweathermap.org/api
- NewsAPI: https://newsapi.org/

## 3) Run the assistant

```powershell
.\venv\Scripts\python.exe main.py
```

## 4) Voice test commands

Try saying:
- "What's the weather in Hyderabad?"
- "Give me top news"
- "Add task call mom tonight"
- "Show tasks"
- "Why is traffic worse in rain?" (LLM fallback)
- "Stop assistant"

## Notes for real in-car deployment

- Replace `pyttsx3` with a robust TTS engine (cloud or edge) for better voice quality.
- Add wake-word detection and noise suppression for driving conditions.
- Use a production NLU/intents layer instead of keyword-only routing.
- Add timeout/retry caching for network APIs.
