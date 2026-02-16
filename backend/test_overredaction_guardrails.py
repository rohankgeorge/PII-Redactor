"""Guardrail tests for preventing over-redaction in name pre-validation."""

from pii_engine import PIITracker, _redact_names


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
    assert "[REDACTED_" not in output
    deny_signals = [s for s in tracker.qa_signals if s["source"] == "NAME_PREVALIDATION"]
    assert deny_signals
    assert all(s["action"] == "REVIEW_ONLY" for s in deny_signals)
    assert {s["reason"] for s in deny_signals} == {"DENY_REDACT_LEXICON"}


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
    assert "[REDACTED_INDIVIDUAL" in forced_output
    assert tracker_force.qa_signals[-1]["action"] == "AUTO_REDACT"
    assert tracker_force.qa_signals[-1]["reason"] == "PASS"
