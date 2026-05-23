# ARIA — In-Car AI Voice Assistant

ARIA (Advanced Road Intelligence Assistant) is a hands-free, voice-first AI assistant built for the car. Speak naturally — it listens, understands, and responds through your speakers in real time.

Built in collaboration with [superteams.ai](https://www.superteams.ai/)

---

## Features

| Capability | Details |
|---|---|
| **Weather** | Current temperature, humidity, wind speed |
| **Rain forecast** | "Will it rain in Delhi today?" |
| **Top headlines** | Reads top 3 news headlines |
| **To-do list** | Add, view, mark done, delete tasks (stored in SQLite) |
| **General Q&A** | Powered by GPT-4o-mini (or HuggingFace fallback) |
| **Conversation memory** | Remembers last 6 exchanges for follow-up questions |
| **Barge-in** | Interrupt the assistant mid-sentence by speaking |
| **Low latency** | Sentence-level streaming — first word plays in ~1.3s |
| **Cross-platform** | Works on Linux, macOS, and Windows |

---

## Project Structure

```
├── main.py                  ← Entry point — run this
├── .env                     ← Your API keys (never committed)
├── .env_example             ← Template for .env
├── requirements.txt
├── setup_windows.bat        ← One-click Windows setup
├── run.bat                  ← One-click Windows launcher
└── scripts/
    ├── config.py            ← All settings and constants
    ├── record_audio.py      ← Microphone capture + adaptive VAD
    ├── stt.py               ← Whisper speech-to-text
    ├── tts.py               ← Edge TTS + sentence-streaming playback
    ├── llm_engine.py        ← Streaming LLM with conversation memory
    ├── weather.py           ← OpenWeatherMap current + forecast
    ├── news.py              ← NewsAPI top headlines
    └── todo.py              ← SQLite to-do list
```

---

## Setup

### Prerequisites

- Python 3.10 or higher
- A working microphone
- Internet connection (for LLM, weather, news, and TTS)

---

### Linux / macOS

```bash
# Clone the repo
git clone <repo-url>
cd In_car_AI_voice_assistant

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up your API keys
cp .env_example .env
# Edit .env and fill in your keys
```

**Linux only** — if you get a PortAudio error:
```bash
sudo apt install portaudio19-dev
```

---

### Windows

1. Install **Python 3.10+** from [python.org](https://python.org) — tick **"Add to PATH"**
2. Install **Visual C++ Redistributable** from [Microsoft](https://aka.ms/vs/17/release/vc_redist.x64.exe)
3. Double-click **`setup_windows.bat`** — creates `.venv` and installs everything
4. Fill in your API keys in `.env` (created automatically from the template)

---

## API Keys

Edit the `.env` file in the project root:

```env
# Required for weather
OPENWEATHER_API_KEY=your_key_here

# Required for news
NEWS_API_KEY=your_key_here

# Required for general Q&A — choose Option A or B below
```

### Option A — OpenAI (recommended)

```env
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini
```

### Option A (alternative) — OpenRouter

```env
OPENAI_API_KEY=sk-or-v1-your_key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=openai/gpt-4o-mini
```

### Option B — HuggingFace (free, slower)

```env
HF_API_TOKEN=your_hf_token
HF_MODEL=mistralai/Mistral-7B-Instruct-v0.2
```

> You can set both Option A and B — OpenAI is tried first, HuggingFace is the fallback.

Get your keys here:
- OpenWeatherMap: [openweathermap.org/api](https://openweathermap.org/api)
- NewsAPI: [newsapi.org](https://newsapi.org)
- OpenAI: [platform.openai.com](https://platform.openai.com)
- OpenRouter: [openrouter.ai](https://openrouter.ai)
- HuggingFace: [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

---

## Running

### Linux / macOS
```bash
source .venv/bin/activate
python main.py
```

### Windows
Double-click **`run.bat`**

or from terminal:
```bat
.venv\Scripts\activate
python main.py
```

---

## Voice Commands

### Weather
| Say | Does |
|---|---|
| "What's the weather in Mumbai?" | Current weather |
| "Temperature in Bangalore" | Current temperature |
| "Will it rain in Delhi today?" | Rain forecast |

### News
| Say | Does |
|---|---|
| "Give me the latest news" | Top 3 headlines |
| "What are today's headlines?" | Top 3 headlines |

### To-Do List
| Say | Does |
|---|---|
| "Add buy groceries to my todo" | Adds a task |
| "Show my tasks" | Lists open tasks |
| "Mark task 1 done" | Marks task 1 complete |
| "Delete task 2" | Removes task 2 |

### General Q&A
| Say | Does |
|---|---|
| "Who invented the telephone?" | LLM answer |
| "Tell me a fun fact" | LLM answer |
| "I'm feeling sleepy while driving" | Safety advice |
| "What can you do?" | Lists capabilities |

### Control
| Say | Does |
|---|---|
| "Clear conversation memory" | Resets chat history |
| "Goodbye" / "Exit" / "Stop" | Exits the assistant |

---

## How It Works

```
You speak
    ↓
Microphone captures audio (adaptive noise gate)
    ↓
Whisper transcribes speech to text (local, CPU)
    ↓
Intent detector routes to the right handler
    ↓
Handler fetches data (weather / news / todo / LLM)
    ↓
LLM streams sentence by sentence  ←── TTS synthesises each sentence in parallel
    ↓
pygame plays audio — first word heard in ~1.3s
    ↓
You can interrupt at any time (barge-in)
```

---

## Troubleshooting

**"No speech detected" keeps repeating**
- Speak louder or move the mic closer
- On first run, device selection probes all mics and picks the cleanest one automatically

**TTS voice sounds wrong or errors**
- Requires internet — `edge-tts` calls Microsoft's neural TTS service
- Check your network connection

**Weather / News returns "API key missing"**
- Make sure `.env` exists in the project root (not inside `scripts/`)
- Keys must not have extra spaces or quotes

**LLM falls back to local responses**
- Check that `OPENAI_API_KEY` in `.env` is valid
- The local fallback only handles greetings and basic questions

**Windows: `No module named 'sounddevice'`**
- Run `setup_windows.bat` again
- Or: `.venv\Scripts\pip install sounddevice`

**Linux: `ALSA lib` errors in terminal**
- These are harmless warnings from the audio driver, not errors — the assistant still works

---

## Configuration

All tunable settings are in [scripts/config.py](scripts/config.py):

| Setting | Default | Description |
|---|---|---|
| `DEFAULT_CITY` | `Hyderabad` | Fallback city for weather queries |
| `WHISPER_MODEL` | `base` | Whisper model size (`tiny`, `base`, `small`) |
| `LLM_MAX_HISTORY` | `6` | Conversation turns to remember |
| `LLM_MAX_TOKENS` | `180` | Max response length |
| `MAX_WAIT_SECONDS` | `7.0` | How long to wait for speech before giving up |
| `MAX_RECORD_SECONDS` | `14.0` | Maximum recording length per utterance |
## Collaboration

This project was created in collaboration with [Superteams.ai](https://superteams.ai).

The collaboration involved contributing technical content, sharing insights, and building projects/blogs focused on learning, innovation, and community engagement in the tech ecosystem.

