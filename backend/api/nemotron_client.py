import os
from pathlib import Path
import requests


def _load_env_fallback() -> None:
    """
    Load NEMO_* settings from local .env files if not already in environment.
    Avoids hard dependency on python-dotenv.
    """
    if os.getenv("NEMO_BASE") and os.getenv("NEMO_MODEL") and os.getenv("NEMO_API_KEY"):
        return

    repo_root = Path(__file__).resolve().parents[2]
    candidates = [
        repo_root / "backend" / ".env",
        repo_root / ".env",
        repo_root / "frontend" / ".env",
    ]

    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, value = raw.split("=", 1)
            key = key.strip()
            if key not in {"NEMO_BASE", "NEMO_MODEL", "NEMO_API_KEY"}:
                continue
            value = value.strip().strip('"').strip("'")
            if os.getenv(key) is None:
                os.environ[key] = value


def _resolve_base_url() -> str:
    base = os.getenv("NEMO_BASE", "http://localhost:8000").rstrip("/")
    if base.endswith("/v1"):
        return base
    return f"{base}/v1"


def chat(messages, temperature: float = 0.2, max_tokens: int = 1200) -> str:
    _load_env_fallback()
    base = _resolve_base_url()
    model = os.getenv("NEMO_MODEL", "nvidia/nemotron-nano-3-30b")
    api_key = os.getenv("NEMO_API_KEY", "")
    url = f"{base}/chat/completions"

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
