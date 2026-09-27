"""Phase 1 pilot: run the full loop on 3 apps chosen to stress different cases.

Telegram  — clean self-serve API key.
Stripe    — self-serve, but with a partner-OAuth wrinkle.
DealCloud — excellent public docs, fully gated. The trap case.

Every fetched source, every fetch failure, and every raw model output is written to
data/pilot/ so the extraction can be audited by hand.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from agent import discover, fetch as fetchmod
from agent.extract import extract_record
from agent.gemini import make_client, model_chain
from agent.models import AppSeed

ROOT = Path(__file__).resolve().parent.parent
PILOT_SEEDS = ROOT / "data" / "pilot_apps.json"
PILOT_DIR = ROOT / "data" / "pilot"

MAX_FIRST_HOP = 8
MAX_SECOND_HOP = 5
MAX_PAGES = 10
PAGE_CHARS = 5000


def load_seeds(only: list[str] | None = None) -> list[AppSeed]:
    seeds = [AppSeed.model_validate(entry) for entry in json.loads(PILOT_SEEDS.read_text())]
    if only:
        wanted = {name.lower() for name in only}
        seeds = [s for s in seeds if s.name.lower() in wanted]
    return seeds


def gather_pages(client, seed: AppSeed, log: dict) -> list[fetchmod.Page]:
    """Discover candidate URLs, fetch them, then fetch a second hop of relevant links."""
    proposed, raw_proposals, proposal_model = discover.propose_candidates(client, seed)
    log["raw_candidate_proposals"] = raw_proposals
    log["candidate_proposal_model"] = proposal_model

    domain = discover.root_domain(seed.hint_url)
    candidates = discover.dedupe(
        ([seed.hint_url] if seed.hint_url else [])
        + proposed
        + discover.pattern_candidates(domain)
    )
    log["candidates_considered"] = candidates

    pages: list[fetchmod.Page] = []
    failures: list[dict] = []

    with fetchmod.make_client() as http:
        for url in candidates[:MAX_FIRST_HOP]:
            result = fetchmod.fetch(http, url, max_chars=PAGE_CHARS)
            if isinstance(result, fetchmod.Page):
                if all(result.url != p.url for p in pages):
                    pages.append(result)
            else:
                failures.append(asdict(result))

        # Second hop: follow auth/access-looking links off the pages that worked, biased
        # toward the section the hint URL points at.
        prefer = None
        if seed.hint_url:
            segments = [s for s in urlparse(seed.hint_url).path.split("/") if s]
            prefer = f"/{segments[0]}" if segments else None

        second_hop: list[str] = []
        for page in list(pages):
            second_hop.extend(fetchmod.harvest_links(page, limit=6, prefer_prefix=prefer))
        already = {p.url.rstrip("/").lower() for p in pages}
        second_hop = [
            u for u in discover.dedupe(second_hop) if u.rstrip("/").lower() not in already
        ]
        log["second_hop_considered"] = second_hop

        for url in second_hop[:MAX_SECOND_HOP]:
            if len(pages) >= MAX_PAGES:
                break
            result = fetchmod.fetch(http, url, max_chars=PAGE_CHARS)
            if isinstance(result, fetchmod.Page):
                if all(result.url != p.url for p in pages):
                    pages.append(result)
            else:
                failures.append(asdict(result))

    removed = fetchmod.strip_shared_boilerplate(pages)
    log["boilerplate_lines_removed"] = removed

    log["fetch_failures"] = failures
    log["sources_fetched"] = [
        {
            "url": p.url,
            "requested_url": p.requested_url,
            "status": p.status,
            "title": p.title,
            "chars": len(p.text),
            "accessed_at": p.accessed_at,
        }
        for p in pages
    ]
    return pages[:MAX_PAGES]


def run_app(client, seed: AppSeed) -> dict:
    log: dict = {
        "app": seed.name,
        "number": seed.number,
        "model_chain": model_chain(),
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    print(f"\n=== [{seed.number}] {seed.name}")

    pages = gather_pages(client, seed, log)
    print(f"    fetched {len(pages)} pages, {len(log['fetch_failures'])} failures")
    for page in pages:
        print(f"      - {page.url}")

    if not pages:
        log["error"] = "no pages fetched; cannot extract"
        print("    !! no pages fetched — skipping extraction")
        return log

    record, raw, extraction_model = extract_record(client, seed, pages)
    log["raw_extraction_output"] = raw
    log["extraction_model"] = extraction_model
    log["record"] = record.model_dump(mode="json")
    log["finished_at"] = datetime.now(timezone.utc).isoformat()

    access = record.access.type.value if record.access else "null"
    auth = record.auth.method.value if record.auth else "null"
    build = record.buildability.verdict.value if record.buildability else "null"
    print(f"    auth={auth}  access={access}  buildability={build}  "
          f"confidence={record.confidence.value}  evidence={len(record.evidence)}")

    # Text dump of every page that fed the extraction, for the manual no-invented-facts read.
    corpus_path = PILOT_DIR / f"{seed.name.lower()}.sources.txt"
    corpus_path.write_text(
        "\n".join(
            f"===== {p.url}\nTITLE: {p.title}\nACCESSED: {p.accessed_at}\n\n{p.text}\n"
            for p in pages
        )
    )
    return log


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Phase 1 pilot.")
    parser.add_argument("--only", nargs="*", help="Restrict to these app names.")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    PILOT_DIR.mkdir(parents=True, exist_ok=True)

    client = make_client()
    seeds = load_seeds(args.only)
    if not seeds:
        raise SystemExit("no matching pilot apps")

    logs, records = [], []
    for seed in seeds:
        try:
            log = run_app(client, seed)
        except Exception as exc:
            # One app blowing up must not cost us the others' results.
            log = {"app": seed.name, "number": seed.number, "error": f"{type(exc).__name__}: {exc}"}
            print(f"    !! {seed.name} failed: {type(exc).__name__}: {str(exc)[:160]}")
        logs.append(log)
        (PILOT_DIR / f"{seed.name.lower()}.json").write_text(json.dumps(log, indent=2))
        if "record" in log:
            records.append(log["record"])

    # Rebuild records.json from every per-app log on disk, so a partial `--only` run
    # never discards records from a previous run.
    all_records = []
    for seed in load_seeds():
        path = PILOT_DIR / f"{seed.name.lower()}.json"
        if path.exists():
            saved = json.loads(path.read_text())
            if "record" in saved:
                all_records.append(saved["record"])
    (PILOT_DIR / "records.json").write_text(json.dumps(all_records, indent=2))

    print(f"\n{len(records)}/{len(seeds)} extracted this run; "
          f"{len(all_records)} records total -> {PILOT_DIR}")


if __name__ == "__main__":
    main()
