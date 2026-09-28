# Composio Research Agent

An agent that researches Composio's 100-app list end to end — auth method, self-serve vs.
gated access, API surface, MCP existence, and a buildability verdict per app, each claim
backed by a real doc URL — checked against a hand-verified sample for accuracy, and
presented as one self-contained HTML page.

## Status

Phase 2 — the pipeline runs over all 100 apps with checkpointing and resume. Results land
in `data/pass1/` per app and merge into `data/pass1_full.json`.

## Layout

- `agent/` — pipeline code.
  - `fetch.py` — HTTP fetch with retry, HTML→text, nav-chrome removal, secret redaction,
    link harvesting.
  - `discover.py` — candidate doc-URL generation.
  - `extract.py` — schema-constrained extraction over fetched text.
  - `gemini.py` — Gemini calls with retry and model fallback.
  - `research.py` — **the pipeline**: research one app end to end. Shared by both runners.
  - `pilot.py` — Phase 1 pilot (3 stress-case apps).
  - `run.py` — Phase 2 batch over all 100, with checkpointing and resume.
  - `verify.py` — evidence provenance + live-URL verification.
- `data/` — `apps.json` (the 100), `pilot/` (Phase 1 logs), `pass1/` (per-app Phase 2
  results plus `pass1/sources/` page text), `pass1_full.json` (merged records).
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
python -m agent.run                # research all 100; skips apps already done
python -m agent.run --force        # re-research everything
python -m agent.run --only Slack Stripe
python -m agent.run --limit 5      # first 5 outstanding apps
python -m agent.run --merge-only   # just rebuild data/pass1_full.json

python -m agent.pilot              # the 3 Phase 1 stress cases
python -m agent.verify             # verify pilot evidence URLs
```

The batch is safe to interrupt: each app is written to `data/pass1/<nnn>-<app>.json` as it
finishes, and rerunning picks up only what is missing. A per-app `SIGALRM` deadline
(`--timeout`, default 420s) keeps one slow site from stalling the run, and any exception an
app raises is checkpointed as an error rather than killing the batch.

## Known limits

- **JavaScript-rendered docs.** Some reference docs (Salesforce's, for instance) ship an
  empty HTML shell, so plain HTTP fetching sees no text. Those apps come out `unknown` with
  low confidence rather than guessed — correct, but less complete than a browser would get.
- **Geography.** Fetches run from one location, and sites serve region-specific pages
  (Stripe showed "invite only in India"). Access verdicts can reflect the fetch location
  rather than global availability.
- **Bot blocking.** A few hosts return 403 regardless of headers; those URLs are recorded
  as fetch failures rather than silently dropped.

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
