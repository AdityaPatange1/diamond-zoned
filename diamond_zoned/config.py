from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

from diamond_zoned.exceptions import ValidationError

_DEFAULT_HOST = "http://127.0.0.1:11434"
_DEFAULT_MODEL = "deepseek-r1"
_DEFAULT_MAX_INPUT_CHARS = 16_000
_DEFAULT_TIMEOUT_S = 120.0
_DEFAULT_MAX_RETRIES = 2


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValidationError(f"Environment variable {name} must be a float.") from exc


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw, 10)
    except ValueError as exc:
        raise ValidationError(f"Environment variable {name} must be an integer.") from exc


def _validate_base_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValidationError("OLLAMA_HOST must use http or https.")
    if not parsed.netloc:
        raise ValidationError("OLLAMA_HOST must include a host (and port if needed).")
    return url.rstrip("/")


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration from environment variables."""

    ollama_host: str
    ollama_model: str
    max_input_chars: int
    timeout_s: float
    max_retries: int
    think_enabled: bool
    # For gpt-oss: "low" | "medium" | "high"; ignored when think_enabled is False for bool models
    think_level: str | None

    @classmethod
    def from_environ(cls) -> Settings:
        host = (os.environ.get("OLLAMA_HOST") or _DEFAULT_HOST).strip()
        model = (os.environ.get("OLLAMA_MODEL") or _DEFAULT_MODEL).strip()
        think_level_raw = os.environ.get("OLLAMA_THINK_LEVEL")
        think_level = think_level_raw.strip() if think_level_raw else None

        return cls(
            ollama_host=_validate_base_url(host),
            ollama_model=model or _DEFAULT_MODEL,
            max_input_chars=max(256, _env_int("DIAMOND_MAX_INPUT_CHARS", _DEFAULT_MAX_INPUT_CHARS)),
            timeout_s=max(5.0, _env_float("OLLAMA_TIMEOUT_S", _DEFAULT_TIMEOUT_S)),
            max_retries=max(0, min(5, _env_int("OLLAMA_MAX_RETRIES", _DEFAULT_MAX_RETRIES))),
            think_enabled=_env_bool("OLLAMA_THINK", True),
            think_level=think_level,
        )
