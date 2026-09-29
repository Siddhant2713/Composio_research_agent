# Composio App Research Agent

An agent that researches 100 apps end to end — how you authenticate, how a first-time
developer actually gets credentials, what the API surface looks like, whether an MCP server
exists, and whether an outside developer could realistically build against it — with every
claim tied to a documentation page the pipeline actually fetched.

It then **checks its own work**: a stratified sample is re-read by a second, adversarial
model that demands the exact supporting line; the failure patterns become prompt changes; all
100 apps are researched again; and both passes are scored with the same instrument.

The report is one self-contained page: [`site/index.html`](site/index.html).

---

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add GEMINI_API_KEY (and GROQ_API_KEY for verification)

python -m agent.run --pass pass2      # research all 100 apps
python -m agent.patterns --pass pass2 # cross-tabs -> data/patterns.json
python -m agent.site --pass pass2     # build site/index.html
```

Open `site/index.html` directly from disk — no server, no build step, no network calls.

### Environment

| Variable | Needed for | Notes |
| --- | --- | --- |
| `GEMINI_API_KEY` | everything | extraction and candidate-URL proposals |
| `GROQ_API_KEY` | verification | the adversarial re-check. Falls back to Gemini if unset |
| `GEMINI_MODELS` | optional | comma-separated fallback chain, most-preferred first |
| | | The default chain is the six live Flash models. Pro has no free-tier quota; on a paid key, prepend it: `GEMINI_MODELS=gemini-3.1-pro-preview,gemini-3.8-flash,gemini-3.6-flash,gemini-3-flash-preview,gemini-3.5-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite` |
| `GROQ_MODEL` | optional | defaults to `openai/gpt-oss-120b` |
| `AUDIT_PACE_SECONDS` | optional | seconds between audit calls (default 40) |

### Reproducing a subset

Re-running all 100 costs real quota and takes hours on a free tier. A representative slice:

```bash
python -m agent.run --pass pass2 --only Telegram Stripe DealCloud "LinkedIn Ads"
```

Those four cover the interesting cases: a clean self-serve API key, a self-serve payments API,
a fully gated platform with excellent public docs, and an app whose docs contain *both*
self-serve signup and an approval gate.

The batch is safe to interrupt. Every app is written to `data/pass2/<nnn>-<app>.json` as it
finishes and a rerun resumes from the gap; `--force` re-researches, but a failed attempt can
never overwrite a good record.

---

## How the pipeline works

```
discover → fetch → extract → verify → re-run
```

1. **Discover** (`agent/discover.py`) — candidate documentation URLs from the seed hint URL,
   deterministic doc-path patterns, and model-proposed URLs. These are guesses about *where
   to look*, nothing more.
2. **Fetch** (`agent/fetch.py`) — real HTTP with retries and full browser headers. Navigation
   chrome is stripped, boilerplate repeated across a site's pages is removed, and a second hop
   follows auth/access-looking links. Anything that 404s or returns no text dies here.
3. **Extract** (`agent/extract.py`) — Gemini, schema-constrained, over the fetched text only.
   Every field must cite a `{url, quote}` and the quote is **verified as a real substring of
   that page**. Unverifiable fields are reset to unknown.
4. **Verify** (`agent/audit.py`, `agent/verification.py`) — a second model re-reads each
   answer adversarially and must produce the exact supporting line, classifying it as
   access-docs, usage-docs or marketing.
5. **Re-run** (`agent/run.py`) — failure patterns become prompt changes; all 100 run again and
   both passes are re-scored.

### Where a human was required

Two places, and neither is automatable:

- **The ground truth.** `verification/sample_sheet.json` holds 20 stratified apps × 6 fields.
  A person opens the real docs and marks each field correct / incorrect / partial. Everything
  else is measured against that; an agent grading its own homework cannot establish whether it
  is right. The adversarial pass pre-fills a suggested verdict with a quoted line to make the
  marking fast, but the mark is a human call.
- **Choosing the worked example.** The automatic ranking picked a "correction" that was
  actually a regression (see below). A person had to read the page to catch it.

---

## What's in here

| Path | What it is |
| --- | --- |
| `agent/research.py` | the pipeline for one app — shared by the pilot and the batch |
| `agent/run.py` | the 100-app batch: checkpointing, resume, per-app timeout |
| `agent/fetch.py` | HTTP, HTML→text, chrome stripping, secret redaction |
| `agent/extract.py` | schema-constrained extraction, quote verification, gate reconciliation |
| `agent/audit.py` | the adversarial judge |
| `agent/sample.py` | stratified sampling for hand verification |
| `agent/verification.py` | sample / audit / score / compare / worked-example |
| `agent/patterns.py` | cross-tabs and the blocker vocabulary |
| `agent/site.py` | builds the single-file report |
| `data/apps.json` | the 100 apps |
| `data/pass1_full.json` | Pass 1 records — **kept so the two passes can be diffed** |
| `data/pass2_full.json` | Pass 2 records |
| `data/pass1/`, `data/pass2/` | per-app logs: candidates, fetch failures, raw model output |
| `data/pass*/sources/` | the exact page text every claim was extracted from |
| `data/patterns.json`, `patterns.md` | the cross-tabs and the headline findings |
| `verification/` | sample sheet, audits, accuracy, worked example, review write-ups |
| `site/index.html` | the report |

Both passes are kept deliberately: a reviewer can diff any app's answer between them and see
exactly what changed and why.

---

## Testing

```bash
pytest                    # everything, including live evidence-URL checks
pytest -m "not network"   # offline only
```

The suite enforces the things that matter: every evidence URL was genuinely fetched, no
credential-shaped string is archived, cross-tabs sum to 100, every headline in `patterns.md`
cites a number that exists in `patterns.json`, no capability is claimed from a navigation
entry, and buildability is derived deterministically.

---

## What went wrong, and what was done about it

The most useful part of this project is the list of mistakes the agent made and how they were
caught. Full detail in `verification/pilot_manual_review.md`, `pass1_review.md` and
`pass2_review.md`.

**Navigation chrome read as evidence.** Stripe and DealCloud were both tagged as having an MCP
server. The entire basis was the phrase "Model Context Protocol" appearing in a **sidebar
menu** — on DealCloud, the same menu repeated across all 9 fetched pages, so one nav block
looked like nine corroborating sources. Fixed in the markup parser, by removing boilerplate
that repeats across a site, and in the prompt. A regression test now fails any MCP claim
resting on a bare label.

**Documentation that can't be read reported as "gated".** Five apps (Lark, Gumroad, Binance,
QuickBooks, Consensus) answered **HTTP 200** with an empty client-rendered shell. The pipeline
called that "no public docs" and asserted `gated` + `buildability: no` — a confident false
claim about products that are in fact self-serve. Unreachable and unreadable are now handled
separately; only genuinely unreachable gets the gated verdict.

**An over-correction in the opposite direction.** After hardening the rule that good docs ≠
self-serve access, 26 records came back `unknown` while their own notes described a developer
generating their own key. Stripe regressed from `self_serve` to `unknown`. The rule is now
symmetric — positive signals on both sides.

**A quote requirement that rewarded cherry-picking.** Requiring one supporting quote proves a
claim is *sourced*, not that it is *right*. For LinkedIn Ads, Pass 2 quoted "Create a
developer application in the Developer Portal" and answered `self_serve`, while the same page
said "apply for Standard tier access" and described a required video demonstration. Pass 1's
`mixed` was the better answer. Gate language is now detected **in code** and injected into the
prompt as lines that must be reconciled before `access` can be answered; LinkedIn Ads now
returns `mixed` with its reasoning recorded in `access.reconciliation`.

**A measuring instrument that punished honesty.** The first auditor returned *zero* "yes"
verdicts across 78 rows, 54 of them self-contradictory — it answered "no" while quoting a line
that supported the claim. The cause was ordering: it committed to a verdict before looking for
evidence. The schema now asks for the quote first. Separately, the auditor scored an
abstention by asking "does the page confirm 'unknown'?", which is almost never true, so
declining to answer was punished as hard as being wrong.

**Secrets archived from vendor docs.** Documentation pages print sample credentials, and the
pipeline was storing the fetched text verbatim. Stripe, Discord and Notion example tokens are
now redacted where page text is written to disk, with a test guarding it.

---

## Honest limitations

- **JavaScript-rendered documentation is invisible.** Some reference docs ship an empty HTML
  shell. Those apps are reported `unknown`, never guessed. A headless browser would close this
  gap and is the single highest-value improvement available.
- **Fetch geography changes answers.** Requests ran from one location and sites serve
  region-specific pages — Stripe's said "invite only in India". Access verdicts can reflect
  where the fetch ran from.
- **Model capability is a confound in the pass comparison.** Pass 2 ran entirely on the
  weakest model in the fallback chain because the stronger ones were quota-exhausted, while
  Pass 1 had better ones. Some of Pass 2's extra `unknown` answers are that, not genuinely
  missing evidence. Documented in `verification/pass2_review.md`.
- **The accuracy figures are a model-judged proxy** unless the sample sheet has been
  hand-marked. Human marks and judge verdicts are computed and reported separately, never
  blended.
- **Free-tier quota shapes everything.** Gemini quota is per-model, so the client walks a
  fallback chain and skips exhausted models; Groq allows ~8k tokens/minute, so audit calls are
  paced beneath it.
