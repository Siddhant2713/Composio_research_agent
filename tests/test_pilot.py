"""Phase 1 gate tests.

Structural checks run offline against data/pilot/. The live-URL check is marked
`network` so the suite still runs without connectivity: `pytest -m "not network"`.
"""
import json
from pathlib import Path

import jsonschema
import pytest

from agent import verify

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema.json").read_text())
PILOT_DIR = ROOT / "data" / "pilot"

EXPECTED_APPS = {"Telegram", "Stripe", "DealCloud"}


def load_logs() -> dict[str, dict]:
    logs = {log["app"]: log for log in verify.app_logs(PILOT_DIR)}
    if not logs:
        pytest.skip("no pilot output; run `python -m agent.pilot` first")
    return logs


@pytest.fixture(scope="module")
def logs() -> dict[str, dict]:
    return load_logs()


@pytest.fixture(scope="module")
def records(logs) -> dict[str, dict]:
    return {name: log["record"] for name, log in logs.items() if "record" in log}


def test_all_three_pilot_apps_produced_a_record(records):
    assert EXPECTED_APPS <= set(records), f"missing: {EXPECTED_APPS - set(records)}"


@pytest.mark.parametrize("app", sorted(EXPECTED_APPS))
def test_record_validates_against_schema(records, app):
    jsonschema.validate(instance=records[app], schema=SCHEMA)


@pytest.mark.parametrize("app", sorted(EXPECTED_APPS))
def test_every_evidence_url_was_actually_fetched(logs, app):
    """No citation may point anywhere the pipeline did not really fetch."""
    unfetched = verify.check_provenance(logs[app])
    assert not unfetched, f"{app} cites never-fetched URLs: {unfetched}"


@pytest.mark.parametrize("app", sorted(EXPECTED_APPS))
def test_record_has_evidence(records, app):
    assert records[app]["evidence"], f"{app} has no evidence at all"


def test_telegram_is_self_serve_api_key(records):
    record = records["Telegram"]
    assert record["access"]["tier"] == "self_serve"
    assert record["auth"]["method"] == "api_key", (
        "Telegram's Bot API uses a long-lived bot token, which is an api_key: "
        f"got {record['auth']['method']}"
    )


def test_dealcloud_is_gated_despite_good_docs(records):
    """The trap case: thorough public docs must not be read as self-serve access."""
    record = records["DealCloud"]
    assert record["access"]["tier"] == "gated", (
        f"DealCloud access should be gated, got {record['access']['tier']}"
    )


def test_stripe_is_self_serve(records):
    assert records["Stripe"]["access"]["tier"] in ("self_serve", "mixed")


@pytest.mark.parametrize("app", sorted(EXPECTED_APPS))
def test_no_capability_claimed_from_navigation_alone(records, app):
    """An MCP claim must carry a URL or substantive notes, not just a menu entry."""
    mcp = records[app].get("mcp") or {}
    if mcp.get("exists"):
        notes = (mcp.get("notes") or "").lower()
        assert mcp.get("url") or len(notes) > 40, (
            f"{app} claims MCP exists on thin grounds: {mcp}"
        )


def test_no_credentials_archived_in_logged_pages():
    """Docs pages print sample keys; none may survive into the committed logs."""
    from agent.fetch import SECRET_PATTERNS

    offenders = []
    for path in sorted(PILOT_DIR.glob("*")):
        text = path.read_text(errors="ignore")
        for pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                if "[REDACTED]" not in match.group(0):
                    offenders.append(f"{path.name}: {match.group(0)[:12]}...")
    assert not offenders, f"unredacted credentials in pilot logs: {offenders}"


@pytest.mark.network
@pytest.mark.parametrize("app", sorted(EXPECTED_APPS))
def test_every_evidence_url_dereferences(records, app):
    urls = [item["url"] for item in records[app]["evidence"]]
    results = verify.check_dereference(urls)
    broken = {url: reason for url, reason in results.items() if reason != "ok"}
    assert not broken, f"{app} has broken evidence URLs: {broken}"
