"""Regression tests ensuring QA ignores placeholder internals."""

import pii_engine


def test_final_qa_skips_detection_starting_at_placeholder_bracket(monkeypatch):
    tracker = pii_engine.PIITracker()
    text = "[REDACTED_EMAIL1]"

    monkeypatch.setattr(pii_engine.nlp_engine, "load_nlp_pipeline", lambda: object())
    monkeypatch.setattr(
        pii_engine.nlp_engine,
        "detect_names_and_locations",
        lambda _text, _nlp: [{"start": 0, "end": len(text), "text": text, "label": "PERSON"}],
    )
    monkeypatch.setattr(pii_engine, "QA_AUTO_REDACT_THRESHOLD", 0.99)

    pii_engine._run_final_qa(text, tracker, "placeholder bracket")

    assert [row for row in tracker.audit_log if row.get("category") == "POTENTIAL_LEAK"] == []


def test_final_qa_skips_detection_starting_at_placeholder_inner_text(monkeypatch):
    tracker = pii_engine.PIITracker()
    text = "[REDACTED_EMAIL1]"

    monkeypatch.setattr(pii_engine.nlp_engine, "load_nlp_pipeline", lambda: object())
    monkeypatch.setattr(
        pii_engine.nlp_engine,
        "detect_names_and_locations",
        lambda _text, _nlp: [{"start": 1, "end": len(text) - 1, "text": "REDACTED_EMAIL1", "label": "PERSON"}],
    )
    monkeypatch.setattr(pii_engine, "QA_AUTO_REDACT_THRESHOLD", 0.99)

    pii_engine._run_final_qa(text, tracker, "placeholder inner")

    assert [row for row in tracker.audit_log if row.get("category") == "POTENTIAL_LEAK"] == []


def test_final_qa_skips_detection_starting_in_middle_of_placeholder(monkeypatch):
    tracker = pii_engine.PIITracker()
    text = "[REDACTED_EMAIL1]"

    monkeypatch.setattr(pii_engine.nlp_engine, "load_nlp_pipeline", lambda: object())
    monkeypatch.setattr(
        pii_engine.nlp_engine,
        "detect_names_and_locations",
        lambda _text, _nlp: [{"start": 5, "end": 14, "text": "CTED_EMAI", "label": "PERSON"}],
    )
    monkeypatch.setattr(pii_engine, "QA_AUTO_REDACT_THRESHOLD", 0.99)

    pii_engine._run_final_qa(text, tracker, "placeholder middle")

    assert [row for row in tracker.audit_log if row.get("category") == "POTENTIAL_LEAK"] == []
