# diamond-zoned

## Purpose

This repository ships a Python package that calls a local [Ollama](https://ollama.com/) chat model with **thinking / reasoning** enabled (`think` on the `/api/chat` endpoint) and asks the model to judge whether arbitrary user text is **thematically compatible** with principles commonly read from the *Diamond Sutra* (Vajracchedikā Prajñāpāramitā). The program emits a structured boolean `certified` plus supporting fields.

## Facts and limits

- **Not authoritative.** Output is probabilistic LLM inference. It is not a religious credential, legal opinion, or academic certification.
- **Local inference by default.** Traffic goes to the URL in `OLLAMA_HOST` (default `http://127.0.0.1:11434`). If that host is remote, data leaves the machine running this client accordingly.
- **Model-dependent.** Thinking traces and JSON discipline vary by model. A thinking-capable tag is required for `message.thinking` to appear; see Ollama documentation for supported models.
- **gpt-oss note.** That family expects `think` levels `low` / `medium` / `high` (set `OLLAMA_THINK_LEVEL`), not only boolean `true`.

## Requirements

- Python 3.11+
- Running Ollama with a pulled model (example: `ollama pull deepseek-r1`)
- Dependencies listed in `requirements.txt` (`httpx`)

## Install

```bash
cd /path/to/diamond-zoned
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Environment variables

| Variable | Default | Meaning |
|----------|---------|---------|
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama base URL (`http` or `https` only). |
| `OLLAMA_MODEL` | `deepseek-r1` | Model name known to Ollama. |
| `OLLAMA_THINK` | `true` | When true, sends `think: true` (or level below). Set to `false` to disable. |
| `OLLAMA_THINK_LEVEL` | unset | If set to `low`, `medium`, or `high`, sent as `think` value (for gpt-oss). |
| `OLLAMA_TIMEOUT_S` | `120` | HTTP timeout seconds (minimum 5). |
| `OLLAMA_MAX_RETRIES` | `2` | Retries after transport failures (0–5). |
| `DIAMOND_MAX_INPUT_CHARS` | `16000` | Maximum user text length after strip (minimum 256 enforced in code). |

## Module layout

```
diamond_zoned/
  __init__.py       # Public exports
  __main__.py       # python -m diamond_zoned
  certifier.py      # Sanitization, orchestration, JSON validation
  cli.py            # CLI entrypoint
  config.py         # Environment-backed settings
  exceptions.py     # Typed errors
  models.py         # Result dataclasses
  ollama_client.py  # HTTP client for /api/chat
  prompts.py        # System prompt and user wrapper (review criteria)
```

## Usage

CLI (after `pip install -e .`):

```bash
export OLLAMA_MODEL=deepseek-r1
echo "Compassion without clinging to a fixed self-nature." | diamond-certify --pretty --show-thinking
```

Stdin is UTF-8 text. Exit codes: `0` success, `2` validation, `3` Ollama transport, `4` parse/schema.

Library:

```python
from diamond_zoned import certify
from diamond_zoned.config import Settings

result = certify("Your text here.", settings=Settings.from_environ())
print(result.certified, result.confidence)
```

## Security notes

- User text is bounded by `DIAMOND_MAX_INPUT_CHARS`; NUL bytes are rejected.
- `OLLAMA_HOST` is restricted to `http`/`https` with a non-empty host.
- No shell invocation, no `eval`, no pickle. The client uses `httpx` with timeouts and limited connection pooling.
- Do not place secrets in prompts or environment variables logged by process managers.

## License

See `LICENSE`.
