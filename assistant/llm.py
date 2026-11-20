"""Thin client for a local Ollama server (https://ollama.com).

Settings come from environment variables, so nobody has to edit code to try another model:
  OLLAMA_HOST   default http://localhost:11434
  OLLAMA_MODEL  default qwen3:8b
"""
import os

import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
TIMEOUT_SECONDS = 300


class LLMError(RuntimeError):
    """Ollama is not reachable or returned an error."""


def chat(system: str, user: str, *, model: str = OLLAMA_MODEL, temperature: float = 0.0) -> str:
    """Send one system + user message pair and return the model's reply text."""
    payload = {
        "model": model,
        "stream": False,
        "think": False,  # qwen3 and other reasoning models: answer directly, without a <think> block
        "options": {"temperature": temperature, "num_ctx": 8192},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    try:
        response = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=TIMEOUT_SECONDS)
    except requests.ConnectionError as exc:
        raise LLMError(f"Ollama is not running at {OLLAMA_HOST}. Start it with `ollama serve`.") from exc
    if response.status_code == 404:
        raise LLMError(f"Model {model!r} is not installed. Run `ollama pull {model}`.")
    if not response.ok:
        raise LLMError(f"Ollama returned HTTP {response.status_code}: {response.text[:300]}")
    return response.json()["message"]["content"].strip()
