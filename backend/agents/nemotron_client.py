import os
import requests

NEMO_URL = os.getenv("NEMO_URL")
NEMO_MODEL = os.getenv("NEMO_MODEL", "nemotron-nano-3-30b")


def chat(messages, temperature: float = 0.2, max_tokens: int = 1200) -> str:
    if not NEMO_URL:
        raise RuntimeError("NEMO_URL is not set")
    response = requests.post(
        NEMO_URL,
        json={
            "model": NEMO_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
