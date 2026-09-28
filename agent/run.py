"""Phase 2: run the Phase 1 pipeline over all 100 apps.

Same pipeline as the pilot (agent/research.py), wrapped in the machinery a 100-app batch
needs: a per-app result file so a crash loses at most one app, resume-by-default, a hard
per-app time limit so one stuck site cannot stall the run, and no exception path that can
kill the batch.

  python -m agent.run                 # research everything not already done
  python -m agent.run --force         # re-research everything
  python -m agent.run --only Slack Stripe
  python -m agent.run --limit 5       # first 5 outstanding apps
  python -m agent.run --merge-only    # just rebuild data/pass1_full.json
"""
from __future__ import annotations

import argparse
import json
import re
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from agent.gemini import make_client
from agent.models import AppSeed
from agent.research import research_app, summarize

ROOT = Path(__file__).resolve().parent.parent
APPS_FILE = ROOT / "data" / "apps.json"
DEFAULT_TIMEOUT_SECONDS = 420

# Which pass this run reads and writes. Pass 1 stays frozen as the verification baseline, so
# Pass 2 lands in its own directory rather than overwriting it. `--pass` sets this.
_pass_name = "pass1"


def set_pass(name: str) -> None:
    global _pass_name
    _pass_name = name


def pass_dir() -> Path:
    return ROOT / "data" / _pass_name


def sources_dir() -> Path:
    return pass_dir() / "sources"


def merged_file() -> Path:
    return ROOT / "data" / f"{_pass_name}_full.json"


class AppTimeout(Exception):
    pass


def slug(name: str) -> str:
    """Filesystem-safe stem for an app name: 'Monday.com' -> 'monday-com'."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load_apps(path: Path = APPS_FILE) -> list[AppSeed]:
    return [AppSeed.model_validate(entry) for entry in json.loads(path.read_text())]


def result_path(seed: AppSeed) -> Path:
    return pass_dir() / f"{seed.number:03d}-{slug(seed.name)}.json"


def is_done(seed: AppSeed) -> bool:
    """A checkpoint counts as done only if it parses and carries a record."""
    path = result_path(seed)
    if not path.exists():
        return False
    try:
        return "record" in json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return False  # half-written checkpoint from a kill: redo it


def run_with_timeout(client, seed: AppSeed, timeout: int) -> dict:
    """Research one app under a hard wall-clock limit.

    SIGALRM interrupts whatever blocking call is in flight, so a site that trickles bytes
    forever cannot hold up the batch.
    """
    def on_alarm(signum, frame):
        raise AppTimeout(f"exceeded {timeout}s")

    previous = signal.signal(signal.SIGALRM, on_alarm)
    signal.alarm(timeout)
    try:
        return research_app(client, seed)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def merge(apps: list[AppSeed]) -> list[dict]:
    """Collect every checkpointed record into one ordered list."""
    records = []
    for seed in apps:
        path = result_path(seed)
        if not path.exists():
            continue
        try:
            log = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if "record" in log:
            records.append(log["record"])
    merged_file().write_text(json.dumps(records, indent=2) + "\n")
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Research all 100 apps.")
    parser.add_argument("--only", nargs="*", help="Restrict to these app names.")
    parser.add_argument("--limit", type=int, help="Stop after this many apps this run.")
    parser.add_argument("--force", action="store_true", help="Re-research already-done apps.")
    parser.add_argument("--merge-only", action="store_true", help="Only rebuild the merged file.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS,
                        help=f"Per-app time limit in seconds (default {DEFAULT_TIMEOUT_SECONDS}).")
    parser.add_argument("--pass", dest="pass_name", default="pass1", choices=("pass1", "pass2"),
                        help="Which pass to write (default pass1).")
    args = parser.parse_args()

    set_pass(args.pass_name)
    load_dotenv(ROOT / ".env")
    pass_dir().mkdir(parents=True, exist_ok=True)
    sources_dir().mkdir(parents=True, exist_ok=True)

    apps = load_apps()

    if args.merge_only:
        records = merge(apps)
        print(f"merged {len(records)}/{len(apps)} records -> {merged_file()}")
        return

    todo = apps
    if args.only:
        wanted = {name.lower() for name in args.only}
        todo = [a for a in todo if a.name.lower() in wanted]
    if not args.force:
        todo = [a for a in todo if not is_done(a)]
    if args.limit:
        todo = todo[: args.limit]

    already = sum(1 for a in apps if is_done(a))
    print(f"{len(apps)} apps total, {already} already done, {len(todo)} to do this run")
    if not todo:
        records = merge(apps)
        print(f"nothing to do; merged {len(records)} records -> {merged_file()}")
        return

    client = make_client()
    succeeded = failed = 0

    for position, seed in enumerate(todo, 1):
        print(f"\n[{position}/{len(todo)}] #{seed.number} {seed.name} ({seed.category})")
        try:
            log = run_with_timeout(client, seed, args.timeout)
            succeeded += 1
        except KeyboardInterrupt:
            print("\ninterrupted — finished apps are checkpointed; rerun to resume")
            merge(apps)
            sys.exit(130)
        except BaseException as exc:
            # Nothing an app can raise may kill the batch. The failure is checkpointed so
            # the run is resumable and the gap is visible rather than silent.
            log = {
                "app": seed.name,
                "number": seed.number,
                "category": seed.category,
                "error": f"{type(exc).__name__}: {exc}"[:400],
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }
            failed += 1
            print(f"    !! {type(exc).__name__}: {str(exc)[:140]}")

        sources_text = log.pop("sources_text", "")

        # Never let a failed attempt destroy a good result. A transient outage midway
        # through a --force pass would otherwise replace real records with error stubs.
        if "record" not in log and is_done(seed):
            print("    (keeping the existing record; this attempt failed)")
        else:
            if sources_text:
                (sources_dir() / f"{seed.number:03d}-{slug(seed.name)}.txt").write_text(sources_text)
            result_path(seed).write_text(json.dumps(log, indent=2))

        if "record" in log:
            print(f"    {summarize(log)}")

    records = merge(apps)
    print(f"\ndone: {succeeded} ok, {failed} errored this run")
    print(f"{len(records)}/{len(apps)} records merged -> {merged_file()}")

    missing = [a.name for a in apps if not is_done(a)]
    if missing:
        print(f"still missing {len(missing)}: {', '.join(missing[:10])}"
              + (" ..." if len(missing) > 10 else ""))


if __name__ == "__main__":
    main()
