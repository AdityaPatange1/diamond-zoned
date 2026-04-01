from __future__ import annotations

import json
from json import JSONDecoder
from typing import Any

from diamond_zoned.config import Settings
from diamond_zoned.exceptions import CertificationParseError, ValidationError
from diamond_zoned.models import CertificationResult, PrincipleCheck
from diamond_zoned.ollama_client import chat_completion, extract_message_fields
from diamond_zoned.prompts import SYSTEM_PROMPT, USER_WRAPPER


_NUL = "\x00"


def _sanitize_user_text(text: str, max_chars: int) -> str:
    if not isinstance(text, str):
        raise ValidationError("Input must be a string.")
    if _NUL in text:
        raise ValidationError("Input must not contain NUL bytes.")
    stripped = text.strip()
    if len(stripped) > max_chars:
        raise ValidationError(f"Input exceeds maximum length ({max_chars} characters).")
    return stripped


def _extract_json_object(raw: str) -> dict[str, Any]:
    """Parse model output; allow leading/trailing prose by decoding the first JSON object."""
    s = raw.strip()
    try:
        parsed = json.loads(s)
    except json.JSONDecodeError:
        start = s.find("{")
        if start < 0:
            raise CertificationParseError("Model output is not valid JSON.")
        decoder = JSONDecoder()
        try:
            parsed, _end = decoder.raw_decode(s[start:])
        except json.JSONDecodeError as exc:
            raise CertificationParseError("Model output is not valid JSON.") from exc

    if not isinstance(parsed, dict):
        raise CertificationParseError("Top-level JSON must be an object.")
    return parsed


def _coerce_payload(payload: dict[str, Any]) -> tuple[bool, str, str, tuple[PrincipleCheck, ...]]:
    certified = payload.get("certified")
    if not isinstance(certified, bool):
        raise CertificationParseError("Field 'certified' must be a boolean.")

    confidence = payload.get("confidence")
    if not isinstance(confidence, str):
        raise CertificationParseError("Field 'confidence' must be a string.")
    if confidence.lower() not in {"low", "medium", "high"}:
        raise CertificationParseError("Field 'confidence' must be one of: low, medium, high.")

    summary = payload.get("alignment_summary")
    if not isinstance(summary, str) or not summary.strip():
        raise CertificationParseError("Field 'alignment_summary' must be a non-empty string.")

    checks_raw = payload.get("principle_checks")
    if not isinstance(checks_raw, list) or not checks_raw:
        raise CertificationParseError("Field 'principle_checks' must be a non-empty array.")

    checks: list[PrincipleCheck] = []
    for item in checks_raw:
        if not isinstance(item, dict):
            raise CertificationParseError("Each principle_checks item must be an object.")
        p = item.get("principle")
        o = item.get("observed")
        n = item.get("note")
        if not isinstance(p, str) or not p.strip():
            raise CertificationParseError("principle_checks.principle must be a non-empty string.")
        if not isinstance(o, bool):
            raise CertificationParseError("principle_checks.observed must be a boolean.")
        if not isinstance(n, str):
            raise CertificationParseError("principle_checks.note must be a string.")
        checks.append(PrincipleCheck(principle=p.strip(), observed=o, note=n.strip()))

    return certified, confidence.lower(), summary.strip(), tuple(checks)


def certify(
    text: str,
    *,
    settings: Settings | None = None,
) -> CertificationResult:
    """
    Ask Ollama (thinking mode) whether `text` aligns with Diamond Sutra thematic lenses.

    This is an LLM judgment, not a religious or legal certification.
    """
    cfg = settings or Settings.from_environ()
    user_text = _sanitize_user_text(text, cfg.max_input_chars)
    user_message = USER_WRAPPER.format(text=user_text if user_text else "[empty]")

    data = chat_completion(cfg, system=SYSTEM_PROMPT, user=user_message)
    thinking, content = extract_message_fields(data)

    payload = _extract_json_object(content)
    certified, confidence, alignment_summary, principle_checks = _coerce_payload(payload)
    return CertificationResult(
        certified=certified,
        confidence=confidence,
        alignment_summary=alignment_summary,
        principle_checks=principle_checks,
        raw_thinking=thinking,
        raw_content=content,
        parsed_payload=payload,
    )
