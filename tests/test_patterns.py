"""Phase 4 gate tests: the cross-tabs must account for every app, and every headline
sentence in patterns.md must cite a number that exists in patterns.json."""
import json
import re
from pathlib import Path

import pytest

from agent.patterns import BLOCKERS, build, check, classify_blocker

ROOT = Path(__file__).resolve().parent.parent
PATTERNS_JSON = ROOT / "data" / "patterns.json"
PATTERNS_MD = ROOT / "data" / "patterns.md"


@pytest.fixture(scope="module")
def patterns():
    if not PATTERNS_JSON.exists():
        pytest.skip("run `python -m agent.patterns` first")
    return json.loads(PATTERNS_JSON.read_text())


def test_every_crosstab_sums_to_the_denominator(patterns):
    problems = check(patterns)
    assert not problems, problems


def test_denominator_is_the_full_hundred(patterns):
    assert patterns["denominator"] == 100


def test_blockers_use_the_fixed_vocabulary(patterns):
    used = set(patterns["totals"]["blocker"])
    assert used <= set(BLOCKERS), f"blockers outside the fixed set: {used - set(BLOCKERS)}"


def test_every_app_gets_exactly_one_blocker(patterns):
    assert len(patterns["blocker_by_app"]) == patterns["denominator"]


def test_classify_blocker_is_deterministic():
    record = {
        "access": {"tier": "gated", "notes": "Contact sales to request access."},
        "buildability": {"verdict": "hard", "reasoning": ""},
        "api_surface": {"rest": True},
    }
    assert classify_blocker(record) == classify_blocker(record) == "partner_or_sales_gate"


def test_self_serve_with_docs_has_no_blocker():
    record = {
        "access": {"tier": "self_serve", "notes": "Generate a key in Settings."},
        "buildability": {"verdict": "easy", "reasoning": ""},
        "api_surface": {"rest": True},
    }
    assert classify_blocker(record) == "none"


def test_build_is_stable_across_runs(patterns):
    records = json.loads((ROOT / "data" / "pass2_full.json").read_text())
    first, second = build(records), build(records)
    assert first["crosstabs"] == second["crosstabs"]
    assert first["totals"] == second["totals"]


def test_headline_sentences_cite_real_numbers(patterns):
    """No vague claims: every numbered headline must quote a figure present in the data."""
    if not PATTERNS_MD.exists():
        pytest.skip("patterns.md not written yet")

    body = PATTERNS_MD.read_text()
    headlines = re.findall(r"^\d+\.\s+\*\*(.+?)\*\*", body, re.S | re.M)
    assert 4 <= len(headlines) <= 6, f"expected 4-6 headlines, found {len(headlines)}"

    # Every count that appears anywhere in patterns.json, as strings.
    known = set()

    def harvest(node):
        if isinstance(node, dict):
            for v in node.values():
                harvest(v)
        elif isinstance(node, list):
            for v in node:
                harvest(v)
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            known.add(str(node))
            if float(node).is_integer():
                known.add(str(int(node)))

    harvest(patterns)

    for headline in headlines:
        numbers = re.findall(r"\d+(?:\.\d+)?", headline)
        assert numbers, f"headline cites no number: {headline[:70]}"
        assert any(n in known for n in numbers), (
            f"headline cites no number found in patterns.json: {headline[:70]}"
        )
