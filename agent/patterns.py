"""Phase 4: cross-tabs and the headline patterns across all 100 apps.

The per-app table is evidence; what the 100 say collectively is the actual finding. Every
sentence in patterns.md has to trace to a count in patterns.json, and every cross-tab has to
sum back to the full denominator — a bucket that quietly drops apps would make a pattern look
sharper than it is.

  python -m agent.patterns --pass pass2
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

# A small fixed vocabulary of blockers, so the reason an app is hard to build against is
# countable rather than 100 different sentences.
BLOCKERS = (
    "none",                            # self-serve credentials, documented API
    "no_public_api",                   # no API for outside developers at all
    "docs_not_machine_readable",       # docs exist but are client-rendered; we could not read
    "paid_plan_gate",                  # API sits behind a paid tier
    "partner_or_sales_gate",           # contact sales, apply, waitlist, partner programme
    "app_review_gate",                 # build freely, but publishing/scopes need review
    "admin_account_only",              # credentials only issuable by a tenant/admin
    "unknown",                         # pages did not say
)

SALES_MARKERS = (
    "contact sales", "contact our sales", "talk to sales", "schedule a demo", "book a demo",
    "request access", "request a demo", "apply for", "waitlist", "account manager",
    "partner program", "partner programme", "become a partner", "enterprise contract",
    "sales team",
)
PAID_MARKERS = (
    "paid plan", "paid subscription", "requires a paid", "professional plan", "enterprise plan",
    "premium plan", "add-on", "upgrade to", "billing must", "subscription required",
    "only available on", "available on the",
)
REVIEW_MARKERS = (
    "app review", "submit your app", "approval process", "reviewed by", "verification process",
    "app must be approved", "review process", "subject to review",
)
ADMIN_MARKERS = (
    "admin", "administrator", "system administrator", "platform manager",
    "must be enabled", "provisioned", "tenant", "workspace owner", "account owner",
)
UNREADABLE_MARKERS = ("client-rendered", "render their content in the browser")
NO_API_MARKERS = ("no public api", "does not offer an api", "no api", "command-line tool", "cli tool")


def _text_of(record: dict) -> str:
    parts = [
        (record.get("access") or {}).get("notes") or "",
        (record.get("buildability") or {}).get("reasoning") or "",
        (record.get("auth") or {}).get("notes") or "",
        (record.get("api_surface") or {}).get("notes") or "",
        record.get("one_liner") or "",
    ]
    return " ".join(parts).lower()


def classify_blocker(record: dict) -> str:
    """Bucket the main thing standing between an outside developer and a working integration.

    Ordered by severity: a hard wall is reported over a soft one when both appear.
    """
    text = _text_of(record)
    access = (record.get("access") or {}).get("tier")
    verdict = (record.get("buildability") or {}).get("verdict")
    surface = record.get("api_surface")

    if any(m in text for m in UNREADABLE_MARKERS):
        return "docs_not_machine_readable"

    if verdict == "no":
        return "no_public_api" if any(m in text for m in NO_API_MARKERS) else "partner_or_sales_gate"

    if surface is None and access == "unknown":
        return "unknown"

    if any(m in text for m in SALES_MARKERS):
        return "partner_or_sales_gate"
    if any(m in text for m in ADMIN_MARKERS):
        return "admin_account_only"
    if any(m in text for m in PAID_MARKERS):
        return "paid_plan_gate"
    if any(m in text for m in REVIEW_MARKERS):
        return "app_review_gate"

    if access == "gated":
        return "partner_or_sales_gate"
    if access == "mixed":
        return "paid_plan_gate"
    if access == "self_serve":
        return "none"
    return "unknown"


def crosstab(records: list[dict], row_of, col_of) -> dict[str, dict[str, int]]:
    table: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for record in records:
        table[row_of(record)][col_of(record)] += 1
    return {row: dict(sorted(cols.items())) for row, cols in sorted(table.items())}


def _total(table: dict[str, dict[str, int]]) -> int:
    return sum(sum(cols.values()) for cols in table.values())


def build(records: list[dict]) -> dict:
    total = len(records)

    def category(r):
        return r["category"]

    def auth(r):
        return (r.get("auth") or {}).get("method") or "unknown"

    def access(r):
        return (r.get("access") or {}).get("tier") or "unknown"

    def verdict(r):
        return (r.get("buildability") or {}).get("verdict") or "unknown"

    blockers = {r["name"]: classify_blocker(r) for r in records}

    def blocker(r):
        return blockers[r["name"]]

    tables = {
        "auth_by_category": crosstab(records, category, auth),
        "access_by_category": crosstab(records, category, access),
        "buildability_by_blocker": crosstab(records, verdict, blocker),
        "access_by_auth": crosstab(records, access, auth),
        "blocker_by_category": crosstab(records, category, blocker),
    }

    # Per-category self-serve share, the figure most of the headlines rest on.
    per_category = {}
    for name in sorted({r["category"] for r in records}):
        rows = [r for r in records if r["category"] == name]
        counts = Counter(access(r) for r in rows)
        per_category[name] = {
            "n": len(rows),
            "self_serve": counts["self_serve"],
            "gated": counts["gated"],
            "mixed": counts["mixed"],
            "unknown": counts["unknown"],
            "self_serve_pct": round(100 * counts["self_serve"] / len(rows), 1),
            "unblocked_pct": round(
                100 * sum(1 for r in rows if blockers[r["name"]] == "none") / len(rows), 1
            ),
        }

    totals = {
        "auth": dict(Counter(auth(r) for r in records).most_common()),
        "access": dict(Counter(access(r) for r in records).most_common()),
        "buildability": dict(Counter(verdict(r) for r in records).most_common()),
        "blocker": dict(Counter(blockers.values()).most_common()),
        "confidence": dict(Counter(r["confidence"] for r in records).most_common()),
        "mcp_exists": dict(
            Counter(str((r.get("mcp") or {}).get("exists")) for r in records).most_common()
        ),
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "denominator": total,
        "blocker_vocabulary": list(BLOCKERS),
        "totals": totals,
        "per_category_access": per_category,
        "crosstabs": tables,
        "crosstab_totals": {name: _total(table) for name, table in tables.items()},
        "blocker_by_app": dict(sorted(blockers.items())),
        "evidence": {
            "total_urls": sum(len(r.get("evidence", [])) for r in records),
            "records_without_evidence": [
                r["name"] for r in records if not r.get("evidence")
            ],
        },
    }


def check(patterns: dict) -> list[str]:
    """Every cross-tab and total must account for exactly the full denominator."""
    problems = []
    n = patterns["denominator"]
    for name, total in patterns["crosstab_totals"].items():
        if total != n:
            problems.append(f"crosstab {name} sums to {total}, expected {n}")
    for name, counts in patterns["totals"].items():
        got = sum(counts.values())
        if got != n:
            problems.append(f"totals.{name} sums to {got}, expected {n}")
    per_cat = sum(v["n"] for v in patterns["per_category_access"].values())
    if per_cat != n:
        problems.append(f"per_category_access sums to {per_cat}, expected {n}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute cross-tabs and patterns.")
    parser.add_argument("--pass", dest="pass_name", default="pass2", choices=("pass1", "pass2"))
    args = parser.parse_args()

    source = DATA_DIR / f"{args.pass_name}_full.json"
    if not source.exists():
        raise SystemExit(f"{source} does not exist yet")

    records = json.loads(source.read_text())
    patterns = build(records)
    patterns["source"] = source.name

    problems = check(patterns)
    out = DATA_DIR / "patterns.json"
    out.write_text(json.dumps(patterns, indent=2) + "\n")

    print(f"{patterns['denominator']} records from {source.name} -> {out}")
    print("access :", patterns["totals"]["access"])
    print("blocker:", patterns["totals"]["blocker"])
    print("\nself-serve share by category:")
    for name, stats in sorted(
        patterns["per_category_access"].items(), key=lambda kv: -kv[1]["self_serve_pct"]
    ):
        print(f"   {stats['self_serve_pct']:5}%  ({stats['self_serve']:2}/{stats['n']:2})  {name}")

    if problems:
        print("\nCROSS-CHECK FAILED:")
        for problem in problems:
            print("  -", problem)
        raise SystemExit(1)
    print(f"\ncross-check ok: every table sums to {patterns['denominator']}")


if __name__ == "__main__":
    main()
