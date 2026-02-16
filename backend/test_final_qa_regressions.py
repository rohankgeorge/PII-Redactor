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

        if fixture.get("must_remain_unredacted"):
            for term in fixture["must_remain_unredacted"]:
                assert term in redacted
        else:
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



def test_total_excludes_manual_review_potential_leaks():
    tracker = PIITracker()
    tracker.audit_log.extend(
        [
            {"category": "EMAIL", "placeholder": "[REDACTED_EMAIL_1]", "location": "Doc"},
            {"category": "POTENTIAL_LEAK", "placeholder": "EMAIL (0.76) foo@example.com", "location": "Doc", "severity": "REVIEW", "highlight": "RED"},
            {"category": "PHONE", "placeholder": "[REDACTED_PHONE_1]", "location": "Doc"},
        ]
    )

    assert tracker.total == 2


def test_allow_list_terms_are_not_re_redacted_by_final_qa():
    import pii_engine as engine

    allow_file = Path(engine.__file__).parent / "user_allow_list.txt"
    original = allow_file.read_text(encoding="utf-8")
    allow_term = "Acme Limited"
    try:
        allow_file.write_text(f"{allow_term}\n", encoding="utf-8")
        tracker = PIITracker()
        output = redact_text(
            f"Vendor name is {allow_term}.",
            tracker,
            context="Allow-list QA ordering",
        )
    finally:
        allow_file.write_text(original, encoding="utf-8")

    assert allow_term in output
    assert "[REDACTED_" not in output
    assert all(signal.get("span") != allow_term for signal in tracker.qa_signals)
