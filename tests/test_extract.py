"""Unit tests for extraction post-processing."""
from agent.extract import downgrade_unsupported_confidence
from agent.models import AppRecord


def record(**overrides) -> AppRecord:
    base = {
        "number": 1,
        "name": "Example",
        "category": "Test",
        "auth": {"method": "api_key", "notes": "n"},
        "access": {"tier": "self_serve", "notes": "n"},
        "buildability": {"verdict": "easy", "reasoning": "n"},
        "evidence": [{"url": "https://example.com", "claim": "c"}],
        "confidence": "high",
    }
    base.update(overrides)
    return AppRecord.model_validate(base)


def test_substantiated_record_keeps_its_confidence():
    assert downgrade_unsupported_confidence(record()).confidence.value == "high"


def test_confidence_downgraded_when_no_evidence():
    result = downgrade_unsupported_confidence(record(evidence=[]))
    assert result.confidence.value == "low"


def test_confidence_downgraded_when_everything_unknown():
    result = downgrade_unsupported_confidence(
        record(
            auth={"method": "unknown", "notes": None},
            access={"tier": "unknown", "notes": None},
            buildability={"verdict": "unknown", "reasoning": None},
        )
    )
    assert result.confidence.value == "low"


def test_partial_knowledge_is_enough_to_keep_confidence():
    """Knowing access but not auth is still a real finding."""
    result = downgrade_unsupported_confidence(
        record(
            auth={"method": "unknown", "notes": None},
            buildability={"verdict": "unknown", "reasoning": None},
        )
    )
    assert result.confidence.value == "high"
