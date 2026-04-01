import pytest

from diamond_zoned.certifier import _coerce_payload, _extract_json_object, _sanitize_user_text
from diamond_zoned.exceptions import CertificationParseError, ValidationError


def test_sanitize_rejects_nul() -> None:
    with pytest.raises(ValidationError):
        _sanitize_user_text("a\x00b", max_chars=100)


def test_extract_json_object() -> None:
    payload = _extract_json_object('  {"certified": true, "confidence": "high", "alignment_summary": "ok", "principle_checks": [{"principle": "p", "observed": true, "note": "n"}]} ')
    assert payload["certified"] is True


def test_extract_json_with_leading_prose() -> None:
    raw = 'Here is JSON:\n{"certified": true, "confidence": "high", "alignment_summary": "ok", "principle_checks": [{"principle": "p", "observed": true, "note": "n"}]}'
    payload = _extract_json_object(raw)
    assert payload["certified"] is True


def test_coerce_payload() -> None:
    p = {
        "certified": False,
        "confidence": "LOW",
        "alignment_summary": "x",
        "principle_checks": [{"principle": "p", "observed": True, "note": "n"}],
    }
    c, conf, s, checks = _coerce_payload(p)
    assert c is False
    assert conf == "low"
    assert s == "x"
    assert len(checks) == 1


def test_coerce_bad_confidence() -> None:
    with pytest.raises(CertificationParseError):
        _coerce_payload(
            {
                "certified": True,
                "confidence": "maybe",
                "alignment_summary": "x",
                "principle_checks": [{"principle": "p", "observed": True, "note": "n"}],
            }
        )
