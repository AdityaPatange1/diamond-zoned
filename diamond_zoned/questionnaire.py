from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from diamond_zoned.certifier import certify
from diamond_zoned.config import Settings
from diamond_zoned.exceptions import ValidationError
from diamond_zoned.models import CertificationResult

# Twelve prompts for a structured self-report used as input to Diamond thematic certification.
MONK_QUESTIONS: tuple[tuple[str, str], ...] = (
    (
        "q01_non_grasping",
        "In your practice, how do you understand non-grasping or non-clinging in relation to "
        "identity and daily monastic discipline?",
    ),
    (
        "q02_compassion_rule",
        "When a formal rule or schedule appears to conflict with compassionate action, how do you "
        "reason about what to do?",
    ),
    (
        "q03_emptiness_precepts",
        "How do you hold together the emptiness (non-reification) of dharmas and faithful "
        "observance of precepts?",
    ),
    (
        "q04_words_truth",
        "Do you believe ultimate truth can be finally captured in language? Answer briefly and "
        "explain your caution or confidence.",
    ),
    (
        "q05_reputation",
        "How do you work with attachment to reputation, approval, or the image of 'being a good "
        "monk'?",
    ),
    (
        "q06_labels_lineage",
        "How do you relate to labels such as rank, lineage, or institutional role without "
        "treating them as ultimate?",
    ),
    (
        "q07_correcting_others",
        "When teaching or correcting others, how do you avoid fixing them as permanently "
        "failing selves?",
    ),
    (
        "q08_literalism",
        "What is your stance on literalism versus contextual reading of authoritative texts?",
    ),
    (
        "q09_doubt_certainty",
        "How do you work with doubt without demanding rigid certainty?",
    ),
    (
        "q10_effort_non_attachment",
        "How do you understand the coexistence of diligent effort and non-attachment to outcomes?",
    ),
    (
        "q11_mundane_goals",
        "How do you relate to practical goals (resources, buildings, schedules) without making "
        "them absolute ends?",
    ),
    (
        "q12_vajra_meaning",
        "In one short paragraph: what does 'diamond' (vajra) insight mean on your path?",
    ),
)


def _slug_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_output_dir(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if path.exists() and not path.is_dir():
        raise ValidationError(f"Output path exists and is not a directory: {path}")
    return path


def build_monk_dossier(responses: list[tuple[str, str, str]]) -> str:
    """Format Q&A into a single document for `certify()`. Each item is (id, question, answer)."""
    lines = [
        "Subject: monastic self-report for Diamond Sutra thematic review.",
        "The following are answers to a fixed twelve-question questionnaire.",
        "",
    ]
    for qid, question, answer in responses:
        lines.append(f"[{qid}] {question}")
        lines.append(answer.strip() if answer.strip() else "[no answer provided]")
        lines.append("")
    return "\n".join(lines).strip()


def run_questionnaire(
    *,
    settings: Settings,
    output_dir: str,
    include_thinking: bool,
) -> tuple[Path, dict[str, object]]:
    """
    Run interactive questionnaire, certify the compiled dossier, write JSON to output_dir.

    Returns (written_path, payload_dict).
    """
    cap = per_answer_char_cap(settings)
    responses = collect_answers_interactive_bounded(max_answer_chars=cap)
    dossier = build_monk_dossier(responses)
    result = certify(dossier, settings=settings)

    out_path = _safe_output_dir(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    filename = f"diamond_questionnaire_{_slug_ts()}.json"
    file_path = out_path / filename

    payload = questionnaire_payload(responses, result, dossier=dossier, include_thinking=include_thinking)
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return file_path, payload


def questionnaire_payload(
    responses: list[tuple[str, str, str]],
    result: CertificationResult,
    *,
    dossier: str,
    include_thinking: bool,
) -> dict[str, object]:
    cert: dict[str, object] = {
        "certified": result.certified,
        "confidence": result.confidence,
        "alignment_summary": result.alignment_summary,
        "principle_checks": [
            {"principle": c.principle, "observed": c.observed, "note": c.note}
            for c in result.principle_checks
        ],
        "raw_model_content": result.raw_content,
    }
    if include_thinking and result.raw_thinking:
        cert["thinking"] = result.raw_thinking

    return {
        "schema_version": 1,
        "kind": "diamond_zoned.monk_questionnaire",
        "responses": [
            {"id": qid, "question": question, "answer": answer} for qid, question, answer in responses
        ],
        "dossier_submitted_to_model": dossier,
        "certification": cert,
    }


def validate_answer_line(text: str, max_line_chars: int) -> str:
    """Strip and bound a single line of user input (questionnaire answers are line-based)."""
    if "\x00" in text:
        raise ValidationError("Answer must not contain NUL bytes.")
    s = text.rstrip("\n\r")
    if len(s) > max_line_chars:
        raise ValidationError(f"Answer exceeds maximum length ({max_line_chars} characters).")
    return s


# Allow multi-line answers: user might want paragraphs. For interactive CLI, after first line we could
# use a delimiter. Simpler UX: read until blank line or special ".end" — that complicates tests.
# User asked "series of 12 questions" — one answer per question is enough; use readline per question.
# If answer is long, DIAMOND_MAX_INPUT_CHARS applies to full dossier, not per line.
# Per-answer cap: e.g. 4000 chars per answer to avoid absurd stdin.

_MAX_ANSWER_CHARS = 8000
_DOSSIER_MARGIN_CHARS = 512


def per_answer_char_cap(settings: Settings) -> int:
    """Keep the full dossier within ``settings.max_input_chars``."""
    empty = [(qid, prompt, "") for qid, prompt in MONK_QUESTIONS]
    overhead = len(build_monk_dossier(empty))
    avail = settings.max_input_chars - overhead - _DOSSIER_MARGIN_CHARS
    per = avail // len(MONK_QUESTIONS)
    capped = min(_MAX_ANSWER_CHARS, per)
    if capped < 128:
        raise ValidationError(
            "DIAMOND_MAX_INPUT_CHARS is too small for the twelve-question dossier; increase it."
        )
    return capped


def collect_answers_interactive_bounded(
    *,
    questions: tuple[tuple[str, str], ...] = MONK_QUESTIONS,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    max_answer_chars: int = _MAX_ANSWER_CHARS,
) -> list[tuple[str, str, str]]:
    """Prompt for each question; one line per answer (validated length, no NUL)."""
    import sys

    sin = stdin if stdin is not None else sys.stdin
    sout = stdout if stdout is not None else sys.stdout
    out: list[tuple[str, str, str]] = []
    total = len(questions)
    for n, (qid, prompt) in enumerate(questions, start=1):
        sout.write(
            f"\n[{n}/{total}] ({qid}) — answer on one line, max {max_answer_chars} characters\n"
            f"{prompt}\n> "
        )
        sout.flush()
        line = sin.readline()
        if line == "":
            answer = ""
        else:
            answer = validate_answer_line(line, max_answer_chars)
        out.append((qid, prompt, answer))
    return out
