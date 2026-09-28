"""Phase 0 gate tests: entrypoint runs, and a hand-written record validates against schema.json."""
import json
import subprocess
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema.json").read_text())

DUMMY_RECORD = {
    "number": 1,
    "name": "Example App",
    "category": "Communication",
    "hint_url": "https://example.com/docs",
    "one_liner": "Example app used only to validate schema.json.",
    "auth": {"method": "oauth2", "notes": "Standard OAuth2 authorization code flow."},
    "access": {"tier": "self_serve", "notes": "Anyone can create a developer app and get a client id/secret."},
    "api_surface": {
        "rest": True,
        "graphql": False,
        "webhooks": True,
        "sdks": ["python", "node"],
        "notes": "REST API with webhook support.",
    },
    "mcp": {"exists": False, "notes": "No known MCP server."},
    "buildability": {"verdict": "easy", "reasoning": "Self-serve OAuth2 with a documented REST API."},
    "evidence": [
        {"url": "https://example.com/docs/auth", "claim": "OAuth2 self-serve auth", "accessed_at": "2026-09-27"}
    ],
    "confidence": "high",
}


def test_dummy_record_validates_against_schema():
    jsonschema.validate(instance=DUMMY_RECORD, schema=SCHEMA)


def test_entrypoint_loads_the_full_app_list():
    """--merge-only exercises the entrypoint and app loading without researching anything."""
    apps = json.loads((ROOT / "data" / "apps.json").read_text())
    assert len(apps) == 100
    result = subprocess.run(
        [sys.executable, "-m", "agent.run", "--merge-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    assert f"/{len(apps)} records" in result.stdout, result.stdout
