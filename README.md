# Composio Research Agent

An agent that researches Composio's 100-app list end to end — auth method, self-serve vs.
gated access, API surface, MCP existence, and a buildability verdict per app, each claim
backed by a real doc URL — checked against a hand-verified sample for accuracy, and
presented as one self-contained HTML page.

## Status

Phase 0 (scaffold) — no research runs yet. The pipeline currently just loads
`data/apps.json` and reports the app count.

## Layout

- `agent/` — pipeline code (models, research passes, entrypoint).
- `data/` — raw app list and processed JSON output per pass.
- `site/` — the self-contained HTML report.
- `verification/` — hand-verified sample tracking sheet.
- `schema.json` — the app record schema (mirrored by `agent/models.py`).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in real keys
```

## Run

```bash
python -m agent.run
```

## Test

```bash
pytest
```
