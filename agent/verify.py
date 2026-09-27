"""Evidence verification: prove every cited URL is real and was actually fetched.

Two independent checks, because they catch different failures:
  1. Provenance (offline) — is every evidence URL in the set of pages this run fetched?
     Catches the model inventing or mangling a citation.
  2. Dereference (live HTTP) — does every evidence URL still return a real page?
     Catches a URL that is well-formed and was fetched but has since broken.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

from agent import fetch as fetchmod

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema.json").read_text())
PILOT_DIR = ROOT / "data" / "pilot"
VERIFICATION_DIR = ROOT / "verification"


def app_logs(pilot_dir: Path = PILOT_DIR) -> list[dict]:
    return [
        json.loads(path.read_text())
        for path in sorted(pilot_dir.glob("*.json"))
        if path.name != "records.json"
    ]


def check_provenance(log: dict) -> list[str]:
    """Evidence URLs that were never fetched by this run."""
    fetched = {source["url"] for source in log.get("sources_fetched", [])}
    record = log.get("record") or {}
    return [
        item["url"]
        for item in record.get("evidence", [])
        if item.get("url") not in fetched
    ]


def check_schema(log: dict) -> str | None:
    record = log.get("record")
    if record is None:
        return "no record in log"
    try:
        jsonschema.validate(instance=record, schema=SCHEMA)
    except jsonschema.ValidationError as exc:
        return f"{'/'.join(str(p) for p in exc.path)}: {exc.message}"
    return None


def check_dereference(urls: list[str]) -> dict[str, str]:
    """Live-fetch each URL. Returns {url: 'ok' | reason}."""
    results: dict[str, str] = {}
    with fetchmod.make_client() as client:
        for url in urls:
            outcome = fetchmod.fetch(client, url, max_chars=500)
            results[url] = (
                "ok" if isinstance(outcome, fetchmod.Page) else outcome.reason
            )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify pilot evidence.")
    parser.add_argument(
        "--offline", action="store_true", help="Skip the live dereference check."
    )
    args = parser.parse_args()

    logs = app_logs()
    if not logs:
        raise SystemExit(f"no pilot logs in {PILOT_DIR}")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "apps": [],
    }
    failures = 0

    for log in logs:
        name = log.get("app", "?")
        schema_error = check_schema(log)
        unfetched = check_provenance(log)
        evidence_urls = [e["url"] for e in (log.get("record") or {}).get("evidence", [])]

        deref = {} if args.offline else check_dereference(evidence_urls)
        broken = {u: r for u, r in deref.items() if r != "ok"}

        entry = {
            "app": name,
            "schema_valid": schema_error is None,
            "schema_error": schema_error,
            "evidence_count": len(evidence_urls),
            "evidence_urls_not_fetched": unfetched,
            "dereference": deref,
            "broken_urls": broken,
        }
        report["apps"].append(entry)

        problems = []
        if schema_error:
            problems.append(f"schema: {schema_error}")
        if unfetched:
            problems.append(f"{len(unfetched)} fabricated/unfetched URL(s)")
        if broken:
            problems.append(f"{len(broken)} broken URL(s)")
        if not evidence_urls:
            problems.append("no evidence at all")

        status = "FAIL" if problems else "PASS"
        failures += bool(problems)
        print(f"[{status}] {name}: {len(evidence_urls)} evidence URLs"
              + (f" — {'; '.join(problems)}" if problems else ""))
        for url, reason in broken.items():
            print(f"         broken: {url} -> {reason}")

    VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)
    out = VERIFICATION_DIR / "evidence_report.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\nreport -> {out}")
    if failures:
        raise SystemExit(f"{failures} app(s) failed verification")


if __name__ == "__main__":
    main()
