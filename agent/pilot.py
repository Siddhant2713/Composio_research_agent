"""Phase 1 pilot: run the full loop on 3 apps chosen to stress different cases.

Telegram  — clean self-serve API key.
Stripe    — self-serve, but with a partner-OAuth wrinkle.
DealCloud — excellent public docs, fully gated. The trap case.

Every fetched source, every fetch failure, and every raw model output is written to
data/pilot/ so the extraction can be audited by hand. The pipeline itself lives in
agent/research.py and is shared with the 100-app batch.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from agent.gemini import make_client
from agent.models import AppSeed
from agent.research import research_app, summarize

ROOT = Path(__file__).resolve().parent.parent
PILOT_SEEDS = ROOT / "data" / "pilot_apps.json"
PILOT_DIR = ROOT / "data" / "pilot"


def load_seeds(only: list[str] | None = None) -> list[AppSeed]:
    seeds = [AppSeed.model_validate(entry) for entry in json.loads(PILOT_SEEDS.read_text())]
    if only:
        wanted = {name.lower() for name in only}
        seeds = [s for s in seeds if s.name.lower() in wanted]
    return seeds


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

    done = 0
    for seed in seeds:
        print(f"\n=== [{seed.number}] {seed.name}")
        try:
            log = research_app(client, seed)
        except Exception as exc:
            # One app blowing up must not cost us the others' results.
            log = {"app": seed.name, "number": seed.number, "error": f"{type(exc).__name__}: {exc}"}
            print(f"    !! failed: {type(exc).__name__}: {str(exc)[:160]}")

        for source in log.get("sources_fetched", []):
            print(f"      - {source['url']}")
        print(f"    {summarize(log)}")

        # The page text is dumped separately so the JSON log stays readable.
        sources_text = log.pop("sources_text", "")
        (PILOT_DIR / f"{seed.name.lower()}.sources.txt").write_text(sources_text)
        (PILOT_DIR / f"{seed.name.lower()}.json").write_text(json.dumps(log, indent=2))
        done += "record" in log

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

    print(f"\n{done}/{len(seeds)} extracted this run; "
          f"{len(all_records)} records total -> {PILOT_DIR}")


if __name__ == "__main__":
    main()
