import os
import requests
from dotenv import load_dotenv

load_dotenv()


def _local_fallback(prompt):
    text = prompt.lower().strip()
    if text in {"hello", "hi", "hey", "hello assistant", "hi assistant"}:
        return "Hi! I am your driving assistant. How can I help you right now?"
    if "how are you" in text:
        return "I am doing great and ready to help. What do you need?"
    if "what can you do" in text or "help" in text:
        return (
            "I can check weather, read top news, manage your todos, and answer "
            "general questions in a short voice-friendly way."
        )
    return (
        "I am having trouble reaching online AI at the moment. "
        "Please ask me for weather, top news, or your todo list."
    )


def ask_llm(prompt):
    if not prompt.strip():
        return "Please say that again."

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        base_url = os.getenv("OPENAI_BASE_URL", "").strip()
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        # OpenRouter keys start with sk-or-v1 and require OpenRouter endpoint.
        if not base_url:
            if openai_key.startswith("sk-or-v1"):
                base_url = "https://openrouter.ai/api/v1"
                if "/" not in model:
                    model = f"openai/{model}"
            else:
                base_url = "https://api.openai.com/v1"

        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "Car Voice Assistant",
                },
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a premium in-car voice assistant similar to Siri or Alexa. "
                                "Speak naturally, politely, and confidently. "
                                "Keep responses short (1 to 3 sentences), clear, and voice-friendly. "
                                "Prioritize driving safety: avoid long explanations and distractions. "
                                "If a request is ambiguous, ask one short clarifying question."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 140,
                },
                timeout=20,
            )
            if response.status_code < 400:
                data = response.json()
                text = data["choices"][0]["message"]["content"].strip()
                if text:
                    return text
        except Exception:
            pass

    hf_key = os.getenv("HF_API_TOKEN")
    hf_model = os.getenv("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
    if hf_key:
        try:
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{hf_model}",
                headers={
                    "Authorization": f"Bearer {hf_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "inputs": (
                        "You are a premium in-car voice assistant like Siri/Alexa. "
                        "Reply naturally and briefly (1 to 3 sentences), with safe driving focus.\n\n"
                        f"User: {prompt}\nAssistant:"
                    ),
                    "parameters": {
                        "max_new_tokens": 140,
                        "temperature": 0.3,
                        "return_full_text": False,
                    },
                },
                timeout=30,
            )
            if response.status_code < 400:
                data = response.json()
                if isinstance(data, list) and data and "generated_text" in data[0]:
                    text = data[0]["generated_text"].strip()
                    if text:
                        return text
        except Exception:
            pass

    return _local_fallback(prompt)