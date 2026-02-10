"""Tests for fallback address detection heuristics."""

from pii_engine import PIITracker, redact_text


def _redact(sample: str) -> str:
    tracker = PIITracker()
    return redact_text(sample, tracker)


def test_fragmented_single_line_address_without_pin():
    text = "Respondent resides at No. 17, 4th Seaward Road"
    redacted = _redact(text)
    assert "[REDACTED_ADDRESS" in redacted
    assert "Seaward Road" not in redacted


def test_multiline_fragmented_address_without_pin():
    text = """Address for service:
Flat B-4, Oceanic Residency
No. 17, 4th Seaward Road
Chennai"""
    redacted = _redact(text)
    assert "[REDACTED_ADDRESS" in redacted
    assert "Flat B-4" not in redacted
    assert "Seaward Road" not in redacted


def test_address_like_pleading_line_without_prefix():
    text = "No. 21, Lakshmi Nagar Layout, Bengaluru"
    redacted = _redact(text)
    assert "[REDACTED_ADDRESS" in redacted
    assert "Lakshmi Nagar" not in redacted
