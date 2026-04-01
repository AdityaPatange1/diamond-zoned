from __future__ import annotations

import json
from typing import Any

import httpx

from diamond_zoned.config import Settings
from diamond_zoned.exceptions import OllamaTransportError, ValidationError


def _think_payload(settings: Settings) -> bool | str:
    if not settings.think_enabled:
        return False
    if settings.think_level:
        level = settings.think_level.lower()
        if level not in {"low", "medium", "high"}:
            raise ValidationError('OLLAMA_THINK_LEVEL must be one of: low, medium, high (for gpt-oss).')
        return level
    return True


def chat_completion(
    settings: Settings,
    *,
    system: str,
    user: str,
) -> dict[str, Any]:
    """Call Ollama /api/chat with thinking enabled when configured."""
    url = f"{settings.ollama_host}/api/chat"
    payload: dict[str, Any] = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "think": _think_payload(settings),
    }

    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(settings.timeout_s, connect=min(10.0, settings.timeout_s))

    last_exc: Exception | None = None
    attempts = settings.max_retries + 1
    for attempt in range(attempts):
        try:
            with httpx.Client(limits=limits, timeout=timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            last_exc = exc
            if attempt == attempts - 1:
                break
    assert last_exc is not None
    raise OllamaTransportError(f"Ollama request failed after {attempts} attempt(s): {last_exc}") from last_exc


def extract_message_fields(data: dict[str, Any]) -> tuple[str | None, str]:
    """Return (thinking, content) from Ollama chat JSON."""
    message = data.get("message")
    if not isinstance(message, dict):
        raise OllamaTransportError("Ollama response missing 'message' object.")
    thinking = message.get("thinking")
    if thinking is not None and not isinstance(thinking, str):
        raise OllamaTransportError("Ollama 'message.thinking' must be a string when present.")
    content = message.get("content")
    if not isinstance(content, str):
        raise OllamaTransportError("Ollama 'message.content' must be a string.")
    return (thinking if thinking else None, content)
