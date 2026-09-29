"""Adversarial second pass: challenge every Pass-N answer against the text it came from.

The extraction pass is asked to *produce* an answer, which biases it toward producing one.
This pass asks the opposite question — "does the page actually confirm this?" — and demands
the exact supporting line. A claim that cannot be quoted is the signal we want.

The distinction it is built to catch: documentation that explains how to CALL an API
(usage docs) being used to answer how a developer GETS credentials (access docs). Good usage
docs say nothing about access, and that conflation was the main Pass-1 error.

All of one app's fields are judged in a single request. Per-field calls meant sending the
same page corpus six times over, which exhausted the rate limit almost immediately.

Runs on Groq when GROQ_API_KEY is set — a cheap, high-volume yes/no judgement needing no
grounding — and falls back to Gemini otherwise.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import httpx

from agent.gemini import generate_json, make_client as make_gemini_client

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

# Groq's free tier allows ~8k tokens per minute and one audit call is several thousand, so
# back-to-back apps trip the limit. Pacing between apps keeps the run under it, which is
# faster overall than repeatedly hitting 429 and waiting out a long retry-after.
PACE_SECONDS = int(os.environ.get("AUDIT_PACE_SECONDS", "40"))
MAX_RETRY_WAIT = 180

VERDICT_VALUES = ("yes", "no", "partial")
EVIDENCE_TYPES = ("access_docs", "usage_docs", "marketing", "none")

# Order matters: the judge must quote its best candidate line and classify it BEFORE
# committing to a verdict. Asking for the verdict first produced a reflexive "no" on almost
# every row, even where the model went on to quote a line that supported the claim.
_VERDICT_PROPERTIES = {
    "supporting_line": {"type": "string", "nullable": True},
    "evidence_type": {"type": "string", "enum": list(EVIDENCE_TYPES)},
    "confirmed": {"type": "string", "enum": list(VERDICT_VALUES)},
    "problem": {"type": "string", "nullable": True},
}


def verdict_schema(fields: list[str]) -> dict[str, Any]:
    """One verdict object per audited field, in a single response."""
    return {
        "type": "object",
        "properties": {
            field: {
                "type": "object",
                "properties": dict(_VERDICT_PROPERTIES),
                "required": list(_VERDICT_PROPERTIES),
            }
            for field in fields
        },
        "required": list(fields),
    }


PROMPT = """You are fact-checking another system's research claims about the app "{app}"
against the ONLY text that was available when those claims were made.

Be accurate, not harsh. A claim the text genuinely supports must be marked "yes" — marking
supported claims wrong is just as much a failure as letting unsupported ones through.

For EACH claim, work in this order:

1. `supporting_line` — search the text for the single best sentence bearing on the claim and
   quote it VERBATIM. If nothing in the text bears on the claim at all, use null.
2. `evidence_type` — classify the line you just quoted:
   - "access_docs": about OBTAINING credentials (signing up, generating a key in settings or
     a developer console, requesting access, contacting sales, partner approval).
   - "usage_docs": about CALLING the API once you already hold credentials.
   - "marketing": product or pricing copy.
   - "none": you found nothing.
3. `confirmed` — now judge, based on the line you quoted:
   - "yes": the line supports the claim. Wording need not match; meaning must.
   - "partial": the line supports a weaker version of the claim, or the only trace is a bare
     capability name in a navigation list, menu, or feature bullet with nothing explaining it.
   - "no": you found no relevant line (supporting_line is null), or the text contradicts the
     claim. Do not answer "no" while quoting a line that supports the claim.
4. `problem` — if not "yes", what is wrong with the claim. Otherwise null.

Field-specific rule for `access.tier` — the one error most worth catching: only
"access_docs" can confirm it. Detailed documentation about *using* an API says nothing about
how a newcomer *obtains credentials*, and many gated platforms publish excellent usage docs.
If the access claim rests only on usage docs or marketing, mark it "no" or "partial" and say
so in `problem`. Conversely, a line showing a developer generating their own key in the
product's settings or console DOES confirm "self_serve" — that is access_docs, mark it "yes".

Also for `access.tier`: if the text shows BOTH a self-serve signup AND an approval, review,
waitlist or tier-upgrade step for fuller API access, then "mixed" is the correct claim and
"self_serve" is wrong. Do not confirm "self_serve" just because one line supports it while
the same text gates fuller access elsewhere.

## When the claim is "unknown" or null
The record declined to answer. Judge whether declining was CORRECT, not whether the text
confirms the word "unknown":
- "yes" — the text really is silent or too ambiguous to settle this field. Declining was the
  right call. Put the closest relevant line in `supporting_line`, or null if nothing relates.
- "no" — the text clearly establishes an answer that the record should have given. Quote the
  line it missed and say in `problem` what the answer should have been.
- "partial" — the text hints at an answer but does not establish it.
An honest "unknown" against silent documentation is a correct record, not a failure.

CLAIMS:
{claims}

TEXT:
{corpus}

Return only a JSON object with one entry per claim field name, each containing
supporting_line, evidence_type, confirmed and problem.
"""


def _groq_key() -> str | None:
    return os.environ.get("GROQ_API_KEY") or None


def _ask_groq(prompt: str, retries: int = 5) -> dict:
    headers = {"Authorization": f"Bearer {_groq_key()}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    last = None
    for attempt in range(retries):
        try:
            with httpx.Client(timeout=120) as client:
                resp = client.post(GROQ_URL, headers=headers, json=payload)
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(5 * (attempt + 1))
            continue

        if resp.status_code == 429 or resp.status_code >= 500:
            # Groq tells us how long to wait, but it sometimes asks for half an hour once a
            # longer window is exhausted. Blocking that long stalls the whole batch, so the
            # wait is capped and the app is skipped instead — the run is resumable, and a
            # skipped app is visible rather than silently missing.
            asked = float(resp.headers.get("retry-after", 0) or 0)
            wait = min(asked or 8 * (attempt + 1), MAX_RETRY_WAIT)
            last = f"HTTP {resp.status_code}"
            if asked > MAX_RETRY_WAIT:
                print(f"        (groq asked for {asked:.0f}s; capped at {wait:.0f}s)")
            else:
                print(f"        (groq {last}, waiting {wait:.0f}s)")
            time.sleep(wait + 1)
            continue

        resp.raise_for_status()
        return json.loads(resp.json()["choices"][0]["message"]["content"])

    raise RuntimeError(f"groq failed after {retries} attempts: {last}")


def _normalise_one(raw: dict) -> dict:
    """Coerce a single verdict into shape, and record self-contradiction rather than hide it."""
    raw = raw if isinstance(raw, dict) else {}

    confirmed = str(raw.get("confirmed", "no")).strip().lower()
    confirmed = (
        "yes" if confirmed.startswith("y")
        else "partial" if confirmed.startswith("p")
        else "no"
    )

    line = raw.get("supporting_line") or None
    if isinstance(line, str) and not line.strip():
        line = None

    evidence_type = re.sub(r"[^a-z_]", "", str(raw.get("evidence_type") or "none").lower().replace(" ", "_"))
    if evidence_type not in EVIDENCE_TYPES:
        evidence_type = "none"

    # "no" while quoting a supporting line is incoherent. Treat it as the honest middle and
    # flag it, so judge noise is visible in the report instead of silently scoring a record.
    inconsistent = confirmed == "no" and line is not None
    if inconsistent:
        confirmed = "partial"

    return {
        "confirmed": confirmed,
        "supporting_line": line,
        "problem": raw.get("problem") or None,
        "evidence_type": evidence_type,
        "judge_inconsistent": inconsistent,
    }


def audit_record(
    app: str,
    claims: dict[str, dict],
    corpus: str,
    gemini_client=None,
    max_corpus: int = 14000,
) -> dict[str, dict]:
    """Challenge every claim for one app in a single request.

    `claims` maps field name -> {"claim": <value>, "notes": <reasoning>}.
    Returns field name -> verdict.
    """
    fields = list(claims)
    rendered = "\n".join(
        f"- {field}: claim={json.dumps(spec['claim'], ensure_ascii=False)}"
        f"  stated_reasoning={json.dumps((spec.get('notes') or '')[:400], ensure_ascii=False)}"
        for field, spec in claims.items()
    )
    prompt = PROMPT.format(
        app=app,
        claims=rendered,
        corpus=corpus[:max_corpus] or "(no text was fetched)",
    )

    if _groq_key():
        raw = _ask_groq(prompt)
        judge = f"groq:{GROQ_MODEL}"
    else:
        client = gemini_client or make_gemini_client()
        raw, _text, model = generate_json(client, prompt, verdict_schema(fields))
        judge = f"gemini:{model}"

    verdicts = {}
    for field in fields:
        verdict = _normalise_one(raw.get(field) or {})
        verdict["judge"] = judge
        verdicts[field] = verdict
    return verdicts
