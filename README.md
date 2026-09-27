# Composio Research Agent

An agent that researches Composio's 100-app list end to end — auth method, self-serve vs.
gated access, API surface, MCP existence, and a buildability verdict per app, each claim
backed by a real doc URL — checked against a hand-verified sample for accuracy, and
presented as one self-contained HTML page.

## Status

Phase 1 — the extraction loop runs end to end on a 3-app pilot (Telegram, Stripe,
DealCloud). The 100-app pass is not wired up yet.

## Layout

- `agent/` — pipeline code.
  - `fetch.py` — HTTP fetch, HTML→text, nav-chrome removal, link harvesting.
  - `discover.py` — candidate doc-URL generation.
  - `extract.py` — schema-constrained extraction over fetched text.
  - `gemini.py` — Gemini calls with retry and model fallback.
  - `pilot.py` — the Phase 1 pilot runner.
  - `verify.py` — evidence provenance + live-URL verification.
- `data/` — app list, and `data/pilot/` raw logs (sources, raw model output, records).
- `site/` — the self-contained HTML report.
- `verification/` — evidence report and manual review notes.
- `schema.json` — the app record schema (mirrored by `agent/models.py`).

## How evidence is kept honest

Google Search grounding was unavailable on the provided key (429 `RESOURCE_EXHAUSTED` on
every model), and no keyless search endpoint is reachable, so the pipeline does its own
fetching instead of delegating that to the model:

1. **Discover** candidate doc URLs — the seed hint URL, deterministic doc-path patterns,
   and model-proposed URLs. Proposals are only a guess at *where to look*.
2. **Fetch** every candidate over real HTTP, then follow a second hop of auth/access-looking
   links. Anything that 404s, times out, or returns no text is discarded here.
3. **Extract** with Gemini constrained to `response_schema`, over the fetched page text
   only. Any evidence URL the model returns that is not in the fetched set is dropped.

So a URL can only become evidence if the pipeline actually retrieved it. `agent/verify.py`
re-checks both properties (provenance and live dereference) after the fact.

## Run

```bash
python -m agent.pilot              # all 3 pilot apps
python -m agent.pilot --only Telegram
python -m agent.verify             # verify evidence URLs
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in real keys
```

## Test

```bash
pytest                      # everything, including live URL checks
pytest -m "not network"     # offline only
```
