# Car Voice Assistant (Windows, Local Prototype)

A branded, in-car style voice assistant that:
- Records from your microphone (with noise gating + barge-in interruption)
- Transcribes speech locally (Whisper)
- Routes your request to “skills” (weather/news/todos) or to an online LLM for general Q&A
- Speaks the answer out loud (Windows TTS, tries to pick an Indian female voice if installed)

## Features

### Skills (works offline except APIs)
- **Weather (current)**: temperature + condition
- **Rain forecast (today)**: “Will it rain in X today?”
- **Top news**: reads top headlines (NewsAPI)
- **Todos (SQLite)**:
  - add task
  - show/list tasks
  - mark task done
  - delete task

### Voice UX
- **Noise gating**: tries to ignore background noise and only start recording when you speak
- **Barge-in**: if you start speaking while the assistant is talking, it stops and listens

## Project structure
- `scripts/main.py`: voice loop + intent routing
- `scripts/record_audio.py`: mic capture + noise gate + barge-in detector
- `scripts/stt.py`: Whisper transcription
- `scripts/tts.py`: text-to-speech (pyttsx3)
- `scripts/weather.py`: OpenWeather current + forecast
- `scripts/news.py`: NewsAPI headlines
- `scripts/todo.py`: SQLite todo database (supports done/delete)
- `database/todo.db`: created automatically

## Setup (Windows PowerShell)

Create and activate a virtual environment:

```powershell
python -m venv venv
.\venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Configure keys (`.env`)

Create/edit `.env` in the project root.

Required for skills:

```env
OPENWEATHER_API_KEY=your_openweather_key
NEWS_API_KEY=your_newsapi_key
```

Optional for general questions (choose at least one):

### Option A (recommended): OpenAI-compatible / OpenRouter

```env
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini

# If your key starts with sk-or-v1 (OpenRouter), set this:
OPENAI_BASE_URL=https://openrouter.ai/api/v1
# For OpenRouter you can also use models like:
# OPENAI_MODEL=openai/gpt-4o-mini
```

### Option B: Hugging Face Inference API

```env
HF_API_TOKEN=your_huggingface_token
HF_MODEL=mistralai/Mistral-7B-Instruct-v0.2
```

## Run

```powershell
.\venv\Scripts\python.exe scripts\main.py
```

## Voice commands (examples)

### Weather
- “What’s the weather in Hyderabad?”
- “What is the temperature in Hyderabad?”
- “Will it rain in Kolkata today?”

### News
- “Give me top news”
- “Headlines”

### Todos
- “Add buy groceries”
- “Add buy groceries to my tasks”
- “Show my todo list”
- “Mark task 3 done”
- “Delete task 2”

### Control
- “Stop assistant”

## Troubleshooting

### It says “I could not hear you”
- Check **Windows Settings → Sound → Input** and select the correct microphone.
- Increase input volume to ~80–100.
- Use a headset mic for best results.

### It speaks with a non-Indian voice
`pyttsx3` can only use voices installed on your Windows machine. The code prefers Indian/female voices if present.
To add more voices: Windows **Settings → Time & language → Speech → Manage voices**.


