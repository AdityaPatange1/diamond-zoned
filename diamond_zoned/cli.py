from __future__ import annotations

import argparse
import json
import sys

from diamond_zoned.certifier import certify
from diamond_zoned.config import Settings
from diamond_zoned.questionnaire import run_questionnaire
from diamond_zoned.exceptions import (
    CertificationParseError,
    DiamondZonedError,
    OllamaTransportError,
    ValidationError,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="diamond-certify",
        description="Certify user text against Diamond Sutra thematic lenses via Ollama (thinking mode).",
    )
    p.add_argument(
        "-i",
        "--input",
        help="Text to evaluate. If omitted, read stdin (UTF-8).",
    )
    p.add_argument(
        "--show-thinking",
        action="store_true",
        help="Include model thinking trace in JSON output when Ollama provides it.",
    )
    p.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON to stdout.",
    )
    p.add_argument(
        "--questionnaire",
        action="store_true",
        help="Run the twelve-question monastic self-report quiz, certify the dossier, write JSON under outputs/.",
    )
    p.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory for --questionnaire JSON artifacts (default: outputs).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        settings = Settings.from_environ()
        if args.questionnaire:
            if args.input is not None:
                raise ValidationError("--questionnaire cannot be used with --input.")

            path, payload = run_questionnaire(
                settings=settings,
                output_dir=args.output_dir,
                include_thinking=args.show_thinking,
            )
            print(f"wrote {path}", file=sys.stderr)
            dump_kw: dict[str, object] = {"ensure_ascii": False}
            if args.pretty:
                dump_kw["indent"] = 2
            print(json.dumps(payload, **dump_kw))
            return 0

        if args.input is not None:
            text = args.input
        else:
            text = sys.stdin.read()

        result = certify(text, settings=settings)
        out: dict[str, object] = {
            "certified": result.certified,
            "confidence": result.confidence,
            "alignment_summary": result.alignment_summary,
            "principle_checks": [
                {"principle": c.principle, "observed": c.observed, "note": c.note}
                for c in result.principle_checks
            ],
        }
        if args.show_thinking and result.raw_thinking:
            out["thinking"] = result.raw_thinking
        out["raw_model_content"] = result.raw_content

        dump_kw: dict[str, object] = {"ensure_ascii": False}
        if args.pretty:
            dump_kw["indent"] = 2
        print(json.dumps(out, **dump_kw))
        return 0
    except ValidationError as exc:
        print(f"validation error: {exc}", file=sys.stderr)
        return 2
    except OllamaTransportError as exc:
        print(f"ollama error: {exc}", file=sys.stderr)
        return 3
    except CertificationParseError as exc:
        print(f"parse error: {exc}", file=sys.stderr)
        return 4
    except DiamondZonedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
