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


def test_clause_text_with_formed_and_st_is_not_redacted():
    text = "The committee formed Marina St with you as convenor for the annual event."
    redacted = _redact(text)
    assert "[REDACTED_ADDRESS" not in redacted
    assert "Marina St" in redacted


def test_clause_text_with_authorize_and_pl_is_not_redacted():
    text = "We authorize Lakeview Pl with you as records owner for correspondence."
    redacted = _redact(text)
    assert "[REDACTED_ADDRESS" not in redacted
    assert "Lakeview Pl" in redacted


def test_clause_text_with_with_you_as_and_st_is_not_redacted():
    text = "The panel proceeded with you as advisor on Queen St for this policy draft."
    redacted = _redact(text)
    assert "[REDACTED_ADDRESS" not in redacted
    assert "Queen St" in redacted


def test_abbreviated_street_with_house_and_pin_is_redacted():
    text = "Address: No. 44, Queen St, Chennai - 600001"
    redacted = _redact(text)
    assert "[REDACTED_ADDRESS" in redacted
    assert "Queen St" not in redacted


def test_abbreviated_place_with_house_and_pin_is_redacted():
    text = "Residence: Flat 12B, Lakeview Pl, Bengaluru 560001"
    redacted = _redact(text)
    assert "[REDACTED_ADDRESS" in redacted
    assert "Lakeview Pl" not in redacted
