"""Tests for split analyze/apply redaction API endpoints."""

from io import BytesIO

from docx import Document as DocxDocument
from fastapi.testclient import TestClient

import server


def _fake_process_document(_content: bytes):
    doc = DocxDocument()
    doc.add_paragraph("[REDACTED_INDIVIDUAL1]")
    out = BytesIO()
    doc.save(out)
    return (
        {"INDIVIDUAL": 1},
        1,
        out.getvalue(),
        [
            {
                "category": "INDIVIDUAL",
                "placeholder": "[REDACTED_INDIVIDUAL1]",
                "location": "Paragraph 1",
                "original_text": "Alice",
            }
        ],
        [],
    )


def test_analyze_stages_document_and_returns_analysis_id(monkeypatch):
    monkeypatch.setattr(server.nlp_engine, "initialize_models", lambda: None)
    monkeypatch.setattr(server, "process_document", _fake_process_document)

    client = TestClient(server.app)
    response = client.post(
        "/api/analyze",
        files={
            "file": (
                "sample.docx",
                b"fake-docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_id"]
    assert payload["total"] == 1
    assert payload["review"]["qa_signal_count"] == 0


def test_apply_redaction_rejects_unknown_analysis_id(monkeypatch):
    monkeypatch.setattr(server.nlp_engine, "initialize_models", lambda: None)

    client = TestClient(server.app)
    response = client.post("/api/apply-redaction", json={"analysis_id": "missing-id"})

    assert response.status_code == 404
    assert "re-analyze" in response.json()["detail"].lower()


def test_apply_redaction_from_analysis_returns_downloadable_result(monkeypatch):
    monkeypatch.setattr(server.nlp_engine, "initialize_models", lambda: None)
    monkeypatch.setattr(server, "process_document", _fake_process_document)

    client = TestClient(server.app)
    analyzed = client.post(
        "/api/analyze",
        files={
            "file": (
                "contract.docx",
                b"fake-docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert analyzed.status_code == 200
    analysis_id = analyzed.json()["analysis_id"]

    applied = client.post("/api/apply-redaction", json={"analysis_id": analysis_id})
    assert applied.status_code == 200

    payload = applied.json()
    assert payload["analysis_id"] == analysis_id
    assert payload["file_id"]
    assert payload["filename"].startswith("redacted_contract")
    assert payload["total"] == 1
