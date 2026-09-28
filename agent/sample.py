"""Stratified sampling for hand verification.

The sample deliberately over-weights the records most likely to be wrong. A random 20 of 100
would be dominated by well-documented, self-serve apps that the pipeline gets right, which
would flatter the accuracy number and teach us nothing. So half the sample is well-known
apps that are fast for a human to check, and half is the awkward tail — gated, unknown,
low-confidence, thin-evidence, or obscure — where errors actually live.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERIFICATION_DIR = ROOT / "verification"

# Household-name apps: a human can verify these quickly from memory plus one page load.
WELL_KNOWN = {
    "Salesforce", "HubSpot", "Zendesk", "Intercom", "Slack", "Twilio", "Discord",
    "Telegram", "Google Ads", "Mailchimp", "SendGrid", "Shopify", "WooCommerce",
    "Amazon Selling Partner", "GitHub", "Cloudflare", "Snowflake", "Datadog", "Sentry",
    "Notion", "Airtable", "Linear", "Jira", "Asana", "Stripe", "Plaid", "QuickBooks",
    "Xero", "Pinterest", "Vercel", "Supabase", "Klaviyo", "Zoho CRM", "Binance",
}

# The six fields a human marks per app. `evidence_supports_claims` is about provenance
# rather than a value: do the cited URLs actually say what the record claims?
FIELDS = (
    "auth.method",
    "access.tier",
    "api_surface",
    "mcp.exists",
    "buildability.verdict",
    "evidence_supports_claims",
)


def is_suspect(record: dict) -> bool:
    """Whether a record carries a signal that it may be wrong."""
    access = (record.get("access") or {}).get("tier")
    auth = (record.get("auth") or {}).get("method")
    verdict = (record.get("buildability") or {}).get("verdict")
    return (
        record.get("confidence") != "high"
        or access in ("gated", "unknown", "mixed")
        or auth == "unknown"
        or verdict in ("unknown", "no")
        or len(record.get("evidence", [])) < 3
    )


def stratify(records: list[dict]) -> dict[str, list[dict]]:
    well_known = [r for r in records if r["name"] in WELL_KNOWN]
    suspect = [r for r in records if r["name"] not in WELL_KNOWN and is_suspect(r)]
    clean = [
        r for r in records
        if r["name"] not in WELL_KNOWN and not is_suspect(r)
    ]
    return {"well_known": well_known, "suspect": suspect, "clean": clean}


def spread_by_category(pool: list[dict], count: int, rng: random.Random) -> list[dict]:
    """Take `count` records from `pool`, round-robin across categories for coverage."""
    by_category: dict[str, list[dict]] = {}
    for record in pool:
        by_category.setdefault(record["category"], []).append(record)
    for bucket in by_category.values():
        rng.shuffle(bucket)

    picked: list[dict] = []
    categories = sorted(by_category)
    rng.shuffle(categories)
    while len(picked) < count and any(by_category[c] for c in categories):
        for category in categories:
            if by_category[category] and len(picked) < count:
                picked.append(by_category[category].pop())
    return picked


def select(records: list[dict], size: int = 20, seed: int = 20260927) -> list[dict]:
    """Pick the sample: half well-known, half suspect tail, topped up if a stratum is short."""
    rng = random.Random(seed)
    strata = stratify(records)

    half = size // 2
    chosen = spread_by_category(strata["well_known"], half, rng)
    chosen += spread_by_category(strata["suspect"], size - len(chosen), rng)

    if len(chosen) < size:  # thin strata: top up from whatever is left
        taken = {r["name"] for r in chosen}
        leftovers = [r for r in records if r["name"] not in taken]
        chosen += spread_by_category(leftovers, size - len(chosen), rng)

    return sorted(chosen, key=lambda r: r["number"])


def stratum_of(record: dict) -> str:
    if record["name"] in WELL_KNOWN:
        return "well_known"
    return "suspect" if is_suspect(record) else "clean"


def field_value(record: dict, field: str):
    """The Pass-N answer for one markable field, as shown to the human."""
    if field == "evidence_supports_claims":
        return [
            {"url": item["url"], "claim": item["claim"]}
            for item in record.get("evidence", [])
        ]
    if field == "api_surface":
        return record.get("api_surface")
    section, _, key = field.partition(".")
    block = record.get(section) or {}
    return block.get(key)


def build_sheet(records: list[dict], sample: list[dict], pass_name: str) -> dict:
    """One row per sampled app per field, with empty slots for the human mark."""
    rows = []
    for record in sample:
        for field in FIELDS:
            rows.append(
                {
                    "app": record["name"],
                    "number": record["number"],
                    "category": record["category"],
                    "stratum": stratum_of(record),
                    "field": field,
                    f"{pass_name}_answer": field_value(record, field),
                    "notes_from_record": _notes_for(record, field),
                    "evidence_urls": [e["url"] for e in record.get("evidence", [])],
                    # Human fills exactly one of these with true.
                    "correct": None,
                    "incorrect": None,
                    "partial": None,
                    "marked_by": None,
                    "human_note": "",
                }
            )
    return {
        "pass": pass_name,
        "sample_size": len(sample),
        "total_records": len(records),
        "fields": list(FIELDS),
        "strata": {
            name: sum(1 for r in sample if stratum_of(r) == name)
            for name in ("well_known", "suspect", "clean")
        },
        "apps": [{"number": r["number"], "name": r["name"], "stratum": stratum_of(r)} for r in sample],
        "rows": rows,
    }


def _notes_for(record: dict, field: str) -> str:
    if field == "evidence_supports_claims":
        return ""
    if field == "api_surface":
        return (record.get("api_surface") or {}).get("notes") or ""
    section, _, _key = field.partition(".")
    block = record.get(section) or {}
    return block.get("notes") or block.get("reasoning") or ""
