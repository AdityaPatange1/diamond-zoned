from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class PrincipleCheck:
    """One thematic check against a named Diamond-principle lens."""

    principle: str
    observed: bool
    note: str


@dataclass(frozen=True, slots=True)
class CertificationResult:
    """Structured certification outcome from the model (interpretive, not authoritative)."""

    certified: bool
    confidence: str
    alignment_summary: str
    principle_checks: tuple[PrincipleCheck, ...]
    raw_thinking: str | None
    raw_content: str
    parsed_payload: dict[str, Any] = field(repr=False)
