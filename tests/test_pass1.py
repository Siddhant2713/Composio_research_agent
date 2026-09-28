"""Phase 2 gate tests: the 100-app batch.

Structural checks are offline. The evidence spot-check hits the network and is marked
`network`, so `pytest -m "not network"` stays fast.
"""
import json
import random
from pathlib import Path

import jsonschema
import pytest

from agent import verify
from agent.run import is_done, load_apps, merged_file, result_path, slug

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema.json").read_text())


@pytest.fixture(scope="module")
def apps():
    return load_apps()


@pytest.fixture(scope="module")
def merged():
    path = merged_file()
    if not path.exists():
        pytest.skip("no merged pass1 file; run `python -m agent.run` first")
    return json.loads(path.read_text())


def test_slug_is_filesystem_safe():
    assert slug("Monday.com") == "monday-com"
    assert slug("Magento (Adobe Commerce)") == "magento-adobe-commerce"
    assert slug("systeme.io") == "systeme-io"


def test_app_list_is_the_full_hundred(apps):
    assert len(apps) == 100
    assert [a.number for a in apps] == list(range(1, 101))
    assert len({a.name for a in apps}) == 100


def test_every_app_has_a_record(apps, merged):
    """No silent gaps: every app is either researched or explicitly marked."""
    missing = [a.name for a in apps if not is_done(a)]
    assert not missing, f"{len(missing)} apps have no record: {missing[:15]}"
    assert len(merged) == len(apps)


def test_all_records_validate_against_schema(merged):
    for record in merged:
        jsonschema.validate(instance=record, schema=SCHEMA)


def test_no_record_is_a_silent_blank(merged):
    """A record with no evidence must say so via low confidence, not look confident."""
    offenders = [
        r["name"]
        for r in merged
        if not r["evidence"] and r["confidence"] != "low"
    ]
    assert not offenders, f"evidence-free records not marked low confidence: {offenders}"


def test_confidence_is_not_high_on_an_empty_record(merged):
    """High confidence in a record that established nothing is a contradiction."""
    offenders = []
    for record in merged:
        if record["confidence"] == "low":
            continue
        auth_known = (record["auth"] or {}).get("method", "unknown") != "unknown"
        access_known = (record["access"] or {}).get("tier", "unknown") != "unknown"
        build_known = (record["buildability"] or {}).get("verdict", "unknown") != "unknown"
        if not record["evidence"] or not (auth_known or access_known or build_known):
            offenders.append(f"{record['name']} ({record['confidence']})")
    assert not offenders, f"confident records that establish nothing: {offenders}"


def test_undiscoverable_apps_are_gated_and_not_buildable(apps):
    """Spec: nothing reachable => gated + buildability 'no', never a guessed API shape.

    A site that answered 2xx but rendered client-side is a different case: documentation
    demonstrably exists, so it must be reported unknown rather than falsely called gated.
    """
    offenders = []
    for seed in apps:
        path = result_path(seed)
        if not path.exists():
            continue
        log = json.loads(path.read_text())
        if not log.get("no_public_docs"):
            continue

        record = log["record"]
        unreadable = any(f.get("kind") == "thin" for f in log.get("fetch_failures", []))
        expected_access = "unknown" if unreadable else "gated"
        expected_verdict = "unknown" if unreadable else "no"

        if (
            record["access"]["tier"] != expected_access
            or record["buildability"]["verdict"] != expected_verdict
            or record["api_surface"] is not None
            or record["evidence"]
        ):
            offenders.append(
                f"{seed.name} (unreadable={unreadable}, "
                f"access={record['access']['tier']}, "
                f"verdict={record['buildability']['verdict']})"
            )
    assert not offenders, f"no-docs apps with guessed/incorrect verdicts: {offenders}"


def test_every_evidence_url_was_actually_fetched(apps):
    """Across all 100, no citation may point at a URL the pipeline never fetched."""
    offenders = {}
    for seed in apps:
        path = result_path(seed)
        if not path.exists():
            continue
        log = json.loads(path.read_text())
        if "record" not in log:
            continue
        unfetched = verify.check_provenance(log)
        if unfetched:
            offenders[seed.name] = unfetched
    assert not offenders, f"fabricated/unfetched evidence URLs: {offenders}"


def test_no_credentials_archived_in_sources():
    from agent.fetch import SECRET_PATTERNS

    offenders = []
    for path in sorted((ROOT / "data" / "pass1").rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(errors="ignore")
        for pattern in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                if "[REDACTED]" not in match.group(0):
                    offenders.append(f"{path.name}: {match.group(0)[:12]}...")
    assert not offenders, f"unredacted credentials in pass1 output: {offenders[:10]}"


@pytest.mark.network
def test_spot_check_five_random_apps_evidence_resolves(merged):
    """Gate: spot check 5 random apps' evidence links resolve."""
    with_evidence = [r for r in merged if r["evidence"]]
    if len(with_evidence) < 5:
        pytest.skip("fewer than 5 records carry evidence")

    sample = random.Random(20260927).sample(with_evidence, 5)
    broken = {}
    for record in sample:
        urls = [item["url"] for item in record["evidence"]]
        results = verify.check_dereference(urls)
        bad = {url: reason for url, reason in results.items() if reason != "ok"}
        if bad:
            broken[record["name"]] = bad
    assert not broken, f"broken evidence URLs in spot check: {broken}"
