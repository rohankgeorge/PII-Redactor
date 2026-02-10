"""Regression tests for the final QA leak detection stage."""

import json
from pathlib import Path

from pii_engine import PIITracker, QA_AUTO_REDACT_THRESHOLD, redact_text


FIXTURE_PATH = Path(__file__).parent / "data" / "qa_regression_fixtures.json"


def _load_fixtures() -> list[dict]:
    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_final_qa_returns_signals_for_regression_fixtures():
    fixtures = _load_fixtures()
    assert fixtures, "Expected non-empty QA regression fixtures"

    for fixture in fixtures:
        tracker = PIITracker()
        redacted = redact_text(fixture["input"], tracker, context=f"Fixture: {fixture['name']}")

        assert "[REDACTED_" in redacted
        assert tracker.qa_signals is not None
        assert all({"type", "span", "confidence", "action", "severity", "highlight"}.issubset(signal) for signal in tracker.qa_signals)


def test_final_qa_has_zero_high_confidence_manual_leaks():
    fixtures = _load_fixtures()

    high_confidence_manual = []
    for fixture in fixtures:
        tracker = PIITracker()
        redact_text(fixture["input"], tracker, context=f"Fixture: {fixture['name']}")
        high_confidence_manual.extend(
            [
                signal
                for signal in tracker.qa_signals
                if signal["action"] == "MANUAL_REVIEW" and signal["confidence"] >= QA_AUTO_REDACT_THRESHOLD
            ]
        )

    assert high_confidence_manual == []


def test_potential_leak_entries_are_marked_red_for_portable_clients():
    fixtures = _load_fixtures()

    for fixture in fixtures:
        tracker = PIITracker()
        redact_text(fixture["input"], tracker, context=f"Fixture: {fixture['name']}")
        for row in tracker.audit_log:
            if row.get("category") == "POTENTIAL_LEAK":
                assert row.get("severity") == "REVIEW"
                assert row.get("highlight") == "RED"

