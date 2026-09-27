"""Pipeline entrypoint. Phase 0: load apps.json and report the count — no LLM calls yet."""
from __future__ import annotations

import json
from pathlib import Path

from agent.models import AppSeed

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
APPS_FILE = DATA_DIR / "apps.json"


def load_apps(path: Path = APPS_FILE) -> list[AppSeed]:
    raw = json.loads(path.read_text())
    return [AppSeed.model_validate(entry) for entry in raw]


def main() -> None:
    apps = load_apps()
    print(f"{len(apps)} apps loaded")


if __name__ == "__main__":
    main()
