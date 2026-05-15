"""Centralised configuration — loads .env from the project root regardless of CWD."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Always resolve .env relative to this file's parent's parent (project root)
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)

# ── API keys ──────────────────────────────────────────────────────────────────
OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "")
NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
HF_API_TOKEN: str = os.getenv("HF_API_TOKEN", "")
HF_MODEL: str = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")

# ── App defaults ──────────────────────────────────────────────────────────────
DEFAULT_CITY: str = os.getenv("DEFAULT_CITY", "Hyderabad")

# ── Audio settings ────────────────────────────────────────────────────────────
SAMPLE_RATE: int = 16_000
CHUNK_SIZE: int = 1024
MAX_WAIT_SECONDS: float = 7.0
MAX_RECORD_SECONDS: float = 14.0
SILENCE_HANGOVER: float = 0.9
MIN_SPEECH_SECONDS: float = 0.35
CALIBRATION_SECONDS: float = 0.75

# ── STT settings ──────────────────────────────────────────────────────────────
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")

# ── TTS voices (tried in order, first success wins) ───────────────────────────
TTS_VOICES: list[str] = [
    "en-IN-NeerjaNeural",
    "en-US-JennyNeural",
    "en-GB-SoniaNeural",
]

# ── LLM ───────────────────────────────────────────────────────────────────────
LLM_MAX_HISTORY: int = 6        # number of user+assistant turn pairs to keep
LLM_MAX_TOKENS: int = 140
LLM_TEMPERATURE: float = 0.3
LLM_TIMEOUT: int = 20

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPTS_DIR: Path = Path(__file__).resolve().parent
DB_PATH: Path = SCRIPTS_DIR / "database" / "todo.db"
AUDIO_TMP: Path = SCRIPTS_DIR / "audio.wav"
