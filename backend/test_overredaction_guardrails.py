"""Guardrail tests for preventing over-redaction in name pre-validation."""

from pii_engine import PIITracker, _redact_names, _redact_entities


def _patch_nlp(monkeypatch, entities):
    monkeypatch.setattr("pii_engine.nlp_engine.load_nlp_pipeline", lambda: object())
    monkeypatch.setattr("pii_engine.nlp_engine.detect_names_and_locations", lambda text, nlp: entities)


def test_deny_redact_lexicon_terms_are_review_only(monkeypatch):
    text = "The ToS for this Dataset protects IP and trademark rights."
    entities = [
        {"start": 4, "end": 7, "text": "ToS", "label": "ORG"},
        {"start": 17, "end": 24, "text": "Dataset", "label": "ORG"},
        {"start": 34, "end": 36, "text": "IP", "label": "ORG"},
    ]
    _patch_nlp(monkeypatch, entities)

    tracker = PIITracker()
    output = _redact_names(text, tracker, "guardrail-test")

    assert output == text
    from placeholder_utils import PLACEHOLDER_PATTERN
    assert not PLACEHOLDER_PATTERN.search(output)
    deny_signals = [s for s in tracker.qa_signals if s["source"] == "NAME_PREVALIDATION"]
    assert deny_signals
    assert all(s["action"] == "REVIEW_ONLY" for s in deny_signals)
    # "IP" (2 chars) may hit SINGLE_TOKEN_TOO_SHORT before DENY_REDACT_LEXICON — both are valid blocks
    valid_block_reasons = {"DENY_REDACT_LEXICON", "SINGLE_TOKEN_TOO_SHORT"}
    assert {s["reason"] for s in deny_signals} <= valid_block_reasons


def test_short_single_token_skips_auto_redact_unless_forced(monkeypatch):
    text = "Witness Al signed the statement."
    entities = [{"start": 8, "end": 10, "text": "Al", "label": "PERSON"}]
    _patch_nlp(monkeypatch, entities)

    tracker = PIITracker()
    output = _redact_names(text, tracker, "guardrail-test")
    assert output == text
    assert tracker.qa_signals[-1]["action"] == "REVIEW_ONLY"
    assert tracker.qa_signals[-1]["reason"] == "SINGLE_TOKEN_TOO_SHORT"

    tracker_force = PIITracker()
    forced_output = _redact_names(text, tracker_force, "guardrail-test", force_redact_terms={"Al"})
    assert "Person " in forced_output
    assert tracker_force.qa_signals[-1]["action"] == "AUTO_REDACT"
    assert tracker_force.qa_signals[-1]["reason"] == "PASS"


def test_stop_phrase_terms_are_review_only(monkeypatch):
    """Stop-phrase terms must not be auto-redacted even when NLP labels them as ORG."""
    text = "This agreement includes a Non-Compete and Confidential Information clause."
    entities = [
        {"start": 25, "end": 36, "text": "Non-Compete", "label": "ORG"},
        {"start": 41, "end": 63, "text": "Confidential Information", "label": "ORG"},
    ]
    _patch_nlp(monkeypatch, entities)

    tracker = PIITracker()
    output = _redact_names(text, tracker, "guardrail-test")

    assert output == text, f"Expected no redaction, got: {output!r}"
    from placeholder_utils import PLACEHOLDER_PATTERN
    assert not PLACEHOLDER_PATTERN.search(output)
    signals = [s for s in tracker.qa_signals if s["source"] == "NAME_PREVALIDATION"]
    assert signals
    assert all(s["action"] == "REVIEW_ONLY" for s in signals)
    reasons = {s["reason"] for s in signals}
    # Both STOP_PHRASE and DENY_REDACT_LEXICON are valid block reasons (deny-lexicon runs first)
    assert reasons <= {"STOP_PHRASE", "DENY_REDACT_LEXICON"}, f"Unexpected reasons: {reasons}"


def test_single_token_org_is_review_only(monkeypatch):
    """Single-token ORG detections (e.g. 'STA', 'Shares') must be review-only by default."""
    text = "The STA requires a transfer of Shares to the buyer."
    entities = [
        {"start": 4, "end": 7, "text": "STA", "label": "ORG"},
        {"start": 31, "end": 37, "text": "Shares", "label": "ORG"},
    ]
    _patch_nlp(monkeypatch, entities)

    tracker = PIITracker()
    output = _redact_names(text, tracker, "guardrail-test")

    assert output == text, f"Expected no redaction, got: {output!r}"
    from placeholder_utils import PLACEHOLDER_PATTERN
    assert not PLACEHOLDER_PATTERN.search(output)
    signals = [s for s in tracker.qa_signals if s["source"] == "NAME_PREVALIDATION"]
    assert signals
    assert all(s["action"] == "REVIEW_ONLY" for s in signals)


def test_entity_first_word_fallback_does_not_over_redact():
    """Standalone occurrences of the first word of a company name must not be redacted."""
    # "Shares India Ltd" is a valid company name; standalone "Shares" later must not be redacted.
    text = "Shares India Ltd (the Company) shall transfer the Shares to the buyer."
    tracker = PIITracker()
    output = _redact_entities(text, tracker, "guardrail-test")

    # The full entity "Shares India Ltd" must be redacted (letter + suffix format)
    assert "Ltd" in output and "Shares India Ltd" not in output, "Expected company name to be redacted"
    # But the standalone word "Shares" after the company must remain plain
    assert "the Shares to" in output, (
        f"Standalone 'Shares' should not be redacted, but got: {output!r}"
    )
