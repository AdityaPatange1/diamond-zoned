import io

import pytest

from diamond_zoned.models import CertificationResult, PrincipleCheck
from diamond_zoned.config import Settings
from diamond_zoned.questionnaire import (
    MONK_QUESTIONS,
    build_monk_dossier,
    collect_answers_interactive_bounded,
    per_answer_char_cap,
    questionnaire_payload,
    validate_answer_line,
)
from diamond_zoned.exceptions import ValidationError


def test_monk_questions_count() -> None:
    assert len(MONK_QUESTIONS) == 12


def test_validate_answer_line_nul() -> None:
    with pytest.raises(ValidationError):
        validate_answer_line("a\x00b", 100)


def test_validate_answer_line_too_long() -> None:
    with pytest.raises(ValidationError):
        validate_answer_line("x" * 10, 9)


def test_build_monk_dossier() -> None:
    r = [
        ("q01", "Q one?", "A one"),
        ("q02", "Q two?", "A two"),
    ]
    d = build_monk_dossier(r)
    assert "q01" in d and "A one" in d
    assert "Q two?" in d


def test_collect_answers_interactive_bounded() -> None:
    lines = "\n".join([f"answer{i}" for i in range(12)]) + "\n"
    sin = io.StringIO(lines)
    sout = io.StringIO()
    out = collect_answers_interactive_bounded(questions=MONK_QUESTIONS, stdin=sin, stdout=sout)
    assert len(out) == 12
    assert out[0][2] == "answer0"
    assert out[11][2] == "answer11"


def test_per_answer_char_cap_default_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DIAMOND_MAX_INPUT_CHARS", "16000")
    cap = per_answer_char_cap(Settings.from_environ())
    assert cap >= 128
    assert cap <= 8000


def test_per_answer_char_cap_raises_when_too_small(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DIAMOND_MAX_INPUT_CHARS", "400")
    with pytest.raises(ValidationError):
        per_answer_char_cap(Settings.from_environ())


def test_questionnaire_payload_shape() -> None:
    responses = [("q01", "Q?", "A")]
    result = CertificationResult(
        certified=True,
        confidence="high",
        alignment_summary="ok",
        principle_checks=(PrincipleCheck(principle="p", observed=True, note="n"),),
        raw_thinking=None,
        raw_content="{}",
        parsed_payload={},
    )
    dossier = build_monk_dossier(responses)
    p = questionnaire_payload(responses, result, dossier=dossier, include_thinking=False)
    assert p["kind"] == "diamond_zoned.monk_questionnaire"
    assert len(p["responses"]) == 1
    assert p["certification"]["certified"] is True
    assert "dossier_submitted_to_model" in p
