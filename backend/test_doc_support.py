"""Tests for legacy .doc conversion support."""

from io import BytesIO

from docx import Document as DocxDocument

import server


def test_convert_doc_to_docx_falls_back_when_antiword_missing(monkeypatch):
    def _raise_file_not_found(*_args, **_kwargs):
        raise FileNotFoundError("antiword not found")

    monkeypatch.setattr(server.subprocess, "run", _raise_file_not_found)

    redacted_docx_bytes = server.convert_doc_to_docx(b"Name: Rajesh Sharma")

    doc = DocxDocument(BytesIO(redacted_docx_bytes))
    text_content = "\n".join(p.text for p in doc.paragraphs)
    assert "Name: Rajesh Sharma" in text_content
