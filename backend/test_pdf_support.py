"""Tests for text-based PDF support in the redaction API."""

from io import BytesIO

from fastapi.testclient import TestClient
from docx import Document as DocxDocument
from pypdf import PdfWriter

import server


class _FakePage:
    def __init__(self, text: str):
        self._text = text

    def extract_text(self):
        return self._text


class _FakeReader:
    def __init__(self, _stream):
        self.pages = [
            _FakePage("Mr. Rajesh Sharma lives in Bangalore."),
            _FakePage("PAN: ABCDE1234F"),
        ]


def test_process_pdf_document_redacts_text(monkeypatch):
    monkeypatch.setattr(server, "PdfReader", _FakeReader)

    def _fake_redact_text(text, tracker, context):
        return tracker.placeholder("INDIVIDUAL", "Rajesh Sharma", context) if "Rajesh" in text else text

    monkeypatch.setattr(server, "redact_text", _fake_redact_text)

    stats, total, redacted_bytes, audit_log, qa_signals = server.process_pdf_document(b"%PDF-1.4")

    assert total > 0
    assert stats
    assert audit_log
    assert qa_signals is not None
    assert redacted_bytes


def test_process_pdf_document_rejects_non_extractable_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buf = BytesIO()
    writer.write(buf)

    try:
        server.process_pdf_document(buf.getvalue())
        assert False, "Expected ValueError for non-extractable PDF text layer"
    except ValueError as exc:
        assert "no extractable text layer" in str(exc).lower()


def test_api_accepts_pdf_upload(monkeypatch):
    monkeypatch.setattr(server.nlp_engine, "initialize_models", lambda: None)

    def _fake_process_pdf_document(_content: bytes):
        return ({"INDIVIDUAL": 1}, 1, b"docx-bytes", [{"category": "INDIVIDUAL", "placeholder": "[REDACTED_INDIVIDUAL1]", "location": "Page 1"}], [])

    monkeypatch.setattr(server, "process_pdf_document", _fake_process_pdf_document)

    client = TestClient(server.app)
    response = client.post(
        "/api/redact",
        files={"file": ("sample.pdf", b"%PDF-1.4\n...", "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["filename"].endswith(".docx")



def test_process_pdf_document_redacts_full_page_before_splitting(monkeypatch):
    class _MultilineReader:
        def __init__(self, _stream):
            self.pages = [_FakePage("No. 97, 3rd Cross\nDomlur Layout, Bangalore - 560022")]

    calls = []

    def _fake_redact_text(text, _tracker, context):
        calls.append((text, context))
        return text.replace("No. 97, 3rd Cross\nDomlur Layout, Bangalore - 560022", "[REDACTED_ADDRESS1]")

    monkeypatch.setattr(server, "PdfReader", _MultilineReader)
    monkeypatch.setattr(server, "redact_text", _fake_redact_text)

    _stats, _total, redacted_bytes, _audit_log, _qa_signals = server.process_pdf_document(b"%PDF-1.4")

    assert len(calls) == 1
    assert "\n" in calls[0][0]
    assert calls[0][1] == "Page 1"

    doc = DocxDocument(BytesIO(redacted_bytes))
    text_content = "\n".join(p.text for p in doc.paragraphs)
    assert "[REDACTED_ADDRESS1]" in text_content
