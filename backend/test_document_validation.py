"""Milestone 5: Regression tests against user-provided test documents.

Each test processes a real legal document through the pipeline and validates
that specific PII items are correctly detected and redacted, while legal
boilerplate terms are NOT false-positively redacted.
"""

import io
from pathlib import Path

import pytest
from docx import Document as DocxDocument
from pypdf import PdfReader

from pii_engine import PIITracker, redact_text

# ── Test document paths ──────────────────────────────────────
_TEST_DOCS = Path(__file__).resolve().parent.parent.parent / "Test Docs"
_DOC_COUNTER_AFFIDAVIT = _TEST_DOCS / "230822- Draft Counter Affidavit by SPIL.docx"
_DOC_LEGAL_OPINION_PDF = _TEST_DOCS / "250401 Sundaram_Legal Opinion -PoA and Promissory Note - exec version.pdf"
_DOC_STA = _TEST_DOCS / "250910 Share Transfer Agreement (STA)-Final print version.docx"
_DOC_FINAL_AWARD = _TEST_DOCS / "251219 Compass vs IK Building and Anr - Final Award.docx"


def _has_test_docs() -> bool:
    return _TEST_DOCS.is_dir() and any(_TEST_DOCS.iterdir())


# Skip if test documents not present
pytestmark = pytest.mark.skipif(
    not _has_test_docs(),
    reason="Test documents not found in 'Test Docs/' — skipping validation",
)


# ── Helpers ──────────────────────────────────────────────────

def _process_docx(filepath: Path) -> tuple[PIITracker, str]:
    """Process a DOCX through the pipeline and return tracker + full redacted text."""
    doc = DocxDocument(str(filepath))
    tracker = PIITracker()
    paragraphs = []
    for i, para in enumerate(doc.paragraphs):
        if not para.text.strip():
            continue
        redacted = redact_text(para.text, tracker, f"Para {i + 1}")
        paragraphs.append(redacted)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    if para.text.strip():
                        redacted = redact_text(para.text, tracker, "Table")
                        paragraphs.append(redacted)
    return tracker, " ".join(paragraphs)


def _process_pdf(filepath: Path) -> tuple[PIITracker, str]:
    """Process a PDF through the pipeline and return tracker + full redacted text."""
    reader = PdfReader(str(filepath))
    tracker = PIITracker()
    pages = []
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if not text.strip():
            continue
        redacted = redact_text(text, tracker, f"Page {page_num + 1}")
        pages.append(redacted)
    return tracker, " ".join(pages)


def _assert_redacted(redacted_text: str, pii_value: str, label: str):
    """Assert that a specific PII value has been removed from the output."""
    assert pii_value not in redacted_text, (
        f"{label}: '{pii_value}' should have been redacted but was found in output"
    )


def _assert_not_redacted(redacted_text: str, term: str, label: str):
    """Assert that a non-PII term has NOT been incorrectly redacted."""
    # We check the term is still present or at least not replaced by a placeholder
    # (some terms may be partially consumed by larger spans, so we only check key terms)
    assert term in redacted_text, (
        f"{label}: '{term}' should NOT have been redacted but was not found in output"
    )


def _has_category(tracker: PIITracker, category: str) -> bool:
    return any(row.get("category") == category for row in tracker.audit_log)


# ── DOC 1: Counter Affidavit ────────────────────────────────

class TestCounterAffidavit:
    @pytest.fixture(autouse=True)
    def setup(self):
        if not _DOC_COUNTER_AFFIDAVIT.exists():
            pytest.skip("Counter Affidavit document not found")
        self.tracker, self.redacted = _process_docx(_DOC_COUNTER_AFFIDAVIT)

    def test_detects_person_names(self):
        """Key individual names are redacted."""
        _assert_redacted(self.redacted, "Padmanabhan", "Person name S. Padmanabhan")

    def test_detects_entity_names(self):
        """Corporate entity names are redacted."""
        _assert_redacted(self.redacted, "Cheran Holdings", "Entity Cheran Holdings")

    def test_detects_addresses(self):
        """Physical addresses are redacted."""
        _assert_redacted(self.redacted, "Anna Salai", "Address Anna Salai")

    def test_has_individual_category(self):
        assert _has_category(self.tracker, "INDIVIDUAL")

    def test_has_entity_category(self):
        assert _has_category(self.tracker, "ENTITY") or _has_category(self.tracker, "LIMITED")

    def test_total_redactions_nonzero(self):
        assert self.tracker.total > 0

    def test_placeholder_format_person(self):
        """Person placeholders use 'Person N' format."""
        assert any(
            "Person " in row.get("placeholder", "")
            for row in self.tracker.audit_log
            if row.get("category") == "INDIVIDUAL"
        )


# ── DOC 2: Legal Opinion (PDF) ──────────────────────────────

class TestLegalOpinionPDF:
    @pytest.fixture(autouse=True)
    def setup(self):
        if not _DOC_LEGAL_OPINION_PDF.exists():
            pytest.skip("Legal Opinion PDF not found")
        self.tracker, self.redacted = _process_pdf(_DOC_LEGAL_OPINION_PDF)

    def test_detects_email(self):
        """Email addresses are redacted."""
        _assert_redacted(self.redacted, "rohangeorge@gmail.com", "Email address")

    def test_detects_pin_code(self):
        """Indian PIN codes are redacted."""
        _assert_redacted(self.redacted, "600010", "PIN code 600010")

    def test_has_email_category(self):
        assert _has_category(self.tracker, "EMAIL")

    def test_has_address_category(self):
        assert _has_category(self.tracker, "ADDRESS")

    def test_total_redactions_nonzero(self):
        assert self.tracker.total > 0

    def test_placeholder_format_email(self):
        """Email placeholders use '[Email N]' format."""
        assert any(
            "[Email " in row.get("placeholder", "")
            for row in self.tracker.audit_log
            if row.get("category") == "EMAIL"
        )


# ── DOC 3: Share Transfer Agreement ─────────────────────────

class TestShareTransferAgreement:
    @pytest.fixture(autouse=True)
    def setup(self):
        if not _DOC_STA.exists():
            pytest.skip("Share Transfer Agreement document not found")
        self.tracker, self.redacted = _process_docx(_DOC_STA)

    def test_detects_aadhaar(self):
        """Aadhaar number is redacted."""
        _assert_redacted(self.redacted, "773174005387", "Aadhaar number")

    def test_detects_pan(self):
        """PAN number is redacted."""
        _assert_redacted(self.redacted, "BJXPA0288D", "PAN number")

    def test_detects_entity_private_limited(self):
        """Entity with 'Private Limited' suffix is redacted."""
        _assert_redacted(self.redacted, "NeoSan Private Limited", "Entity NeoSan Pvt Ltd")

    def test_detects_person_with_apostrophe(self):
        """Person name with apostrophe (D'Rozario) is redacted."""
        _assert_redacted(self.redacted, "D'Rozario", "Person D'Rozario")

    def test_detects_pin_code(self):
        """PIN code is redacted."""
        _assert_redacted(self.redacted, "560022", "PIN code 560022")

    def test_detects_address(self):
        """Physical addresses are redacted."""
        _assert_redacted(self.redacted, "Yeshwantpur", "Address Yeshwantpur")

    def test_has_aadhaar_category(self):
        assert _has_category(self.tracker, "AADHAAR_NUMBER")

    def test_has_pan_category(self):
        assert _has_category(self.tracker, "PAN_NUMBER")

    def test_has_private_limited_category(self):
        assert _has_category(self.tracker, "PRIVATE_LIMITED")

    def test_placeholder_format_aadhaar(self):
        """Aadhaar placeholder uses '[Aadhaar N]' format."""
        assert any(
            "[Aadhaar " in row.get("placeholder", "")
            for row in self.tracker.audit_log
            if row.get("category") == "AADHAAR_NUMBER"
        )

    def test_placeholder_format_pan(self):
        """PAN placeholder uses '[PAN N]' format."""
        assert any(
            "[PAN " in row.get("placeholder", "")
            for row in self.tracker.audit_log
            if row.get("category") == "PAN_NUMBER"
        )

    def test_placeholder_format_entity(self):
        """Entity placeholder preserves corporate suffix."""
        entity_rows = [
            row for row in self.tracker.audit_log
            if row.get("category") == "PRIVATE_LIMITED"
        ]
        assert entity_rows
        assert any("Private Limited" in row.get("placeholder", "") for row in entity_rows)

    def test_total_redactions_significant(self):
        """STA is PII-heavy — expect substantial redactions."""
        assert self.tracker.total >= 50

    def test_audit_log_has_original_text(self):
        """Every audit entry has original_text populated."""
        for row in self.tracker.audit_log:
            if row.get("category") == "POTENTIAL_LEAK":
                continue
            assert row.get("original_text"), f"Audit entry missing original_text: {row}"


# ── DOC 4: Final Award ──────────────────────────────────────

class TestFinalAward:
    @pytest.fixture(autouse=True)
    def setup(self):
        if not _DOC_FINAL_AWARD.exists():
            pytest.skip("Final Award document not found")
        self.tracker, self.redacted = _process_docx(_DOC_FINAL_AWARD)

    def test_detects_person_names(self):
        """Key person names are redacted."""
        _assert_redacted(self.redacted, "Chandrakanth", "Person Chandrakanth Reddy")

    def test_detects_llp_entity(self):
        """LLP entity is detected."""
        _assert_redacted(self.redacted, "Fantasy Fab", "Entity Fantasy Fab and Buildtech LLP")

    def test_detects_addresses(self):
        """Physical addresses are redacted."""
        _assert_redacted(self.redacted, "Banjara Hills", "Address Banjara Hills")

    def test_has_llp_or_entity_category(self):
        assert _has_category(self.tracker, "LLP") or _has_category(self.tracker, "ENTITY")

    def test_has_address_category(self):
        assert _has_category(self.tracker, "ADDRESS")

    def test_total_redactions_nonzero(self):
        assert self.tracker.total > 0

    def test_placeholder_format_address(self):
        """Address placeholder uses '[Address N]' format."""
        assert any(
            "[Address " in row.get("placeholder", "")
            for row in self.tracker.audit_log
            if row.get("category") == "ADDRESS"
        )


# ── Cross-document: PII type coverage ───────────────────────

class TestPIITypeCoverage:
    """Verify that every major PII category from TYPES OF PII.docx has
    at least one passing detection across the test documents."""

    @pytest.fixture(autouse=True)
    def setup(self):
        if not _has_test_docs():
            pytest.skip("Test documents not available")
        self.trackers = []
        for doc_path in [_DOC_COUNTER_AFFIDAVIT, _DOC_STA, _DOC_FINAL_AWARD]:
            if doc_path.exists():
                t, _ = _process_docx(doc_path)
                self.trackers.append(t)
        if _DOC_LEGAL_OPINION_PDF.exists():
            t, _ = _process_pdf(_DOC_LEGAL_OPINION_PDF)
            self.trackers.append(t)
        self.all_categories = set()
        for t in self.trackers:
            for row in t.audit_log:
                cat = row.get("category", "")
                if cat and cat != "POTENTIAL_LEAK":
                    self.all_categories.add(cat)

    def test_individual_detected(self):
        assert "INDIVIDUAL" in self.all_categories

    def test_entity_detected(self):
        assert self.all_categories & {"ENTITY", "PRIVATE_LIMITED", "LIMITED", "LLP"}

    def test_address_detected(self):
        assert "ADDRESS" in self.all_categories

    def test_aadhaar_detected(self):
        assert "AADHAAR_NUMBER" in self.all_categories

    def test_pan_detected(self):
        assert "PAN_NUMBER" in self.all_categories

    def test_email_detected(self):
        assert "EMAIL" in self.all_categories
