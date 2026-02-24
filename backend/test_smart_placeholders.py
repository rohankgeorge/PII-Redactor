"""Tests for Milestone 1: Context-Preserving Smart Placeholders."""

from pii_engine import PIITracker
from placeholder_utils import is_inside_placeholder, is_placeholder_internal_text


class TestPIITrackerPlaceholderFormat:
    """Verify PIITracker.placeholder() generates correct format for each PII category."""

    def test_aadhaar_format(self):
        tracker = PIITracker()
        ph = tracker.placeholder("AADHAAR_NUMBER", "2345 6789 0123", "Para 1")
        assert ph == "[Aadhaar 1]"

    def test_pan_format(self):
        tracker = PIITracker()
        ph = tracker.placeholder("PAN_NUMBER", "ABCDE1234F", "Para 1")
        assert ph == "[PAN 1]"

    def test_phone_format(self):
        tracker = PIITracker()
        ph = tracker.placeholder("PHONE_NUMBER", "+91 98765 43210", "Para 1")
        assert ph == "[Phone 1]"

    def test_email_format(self):
        tracker = PIITracker()
        ph = tracker.placeholder("EMAIL", "test@example.com", "Para 1")
        assert ph == "[Email 1]"

    def test_bank_account_format(self):
        tracker = PIITracker()
        ph = tracker.placeholder("BANK_ACCOUNT", "1234567890", "Para 1")
        assert ph == "[Bank Account 1]"

    def test_gst_format(self):
        tracker = PIITracker()
        ph = tracker.placeholder("GST_NUMBER", "22AAAAA0000A1Z5", "Para 1")
        assert ph == "[GST 1]"

    def test_ifsc_format(self):
        tracker = PIITracker()
        ph = tracker.placeholder("IFSC_CODE", "SBIN0001234", "Para 1")
        assert ph == "[IFSC 1]"

    def test_passport_format(self):
        tracker = PIITracker()
        ph = tracker.placeholder("PASSPORT_NUMBER", "A1234567", "Para 1")
        assert ph == "[Passport 1]"

    def test_voter_id_format(self):
        tracker = PIITracker()
        ph = tracker.placeholder("VOTER_ID", "ABC1234567", "Para 1")
        assert ph == "[Voter ID 1]"

    def test_dl_format(self):
        tracker = PIITracker()
        ph = tracker.placeholder("DRIVING_LICENSE", "KA0120230001234", "Para 1")
        assert ph == "[DL 1]"

    def test_vehicle_reg_format(self):
        tracker = PIITracker()
        ph = tracker.placeholder("VEHICLE_REGISTRATION", "KA 01 AB 1234", "Para 1")
        assert ph == "[Vehicle Reg 1]"

    def test_upi_format(self):
        tracker = PIITracker()
        ph = tracker.placeholder("UPI_ID", "user@bank", "Para 1")
        assert ph == "[UPI 1]"

    def test_dob_format(self):
        tracker = PIITracker()
        ph = tracker.placeholder("DATE_OF_BIRTH", "15/03/1990", "Para 1")
        assert ph == "[DOB 1]"

    def test_pin_code_format(self):
        tracker = PIITracker()
        ph = tracker.placeholder("PIN_CODE", "560001", "Para 1")
        assert ph == "[PIN 1]"

    def test_location_format(self):
        tracker = PIITracker()
        ph = tracker.placeholder("LOCATION", "Bangalore", "Para 1")
        assert ph == "[Location 1]"

    def test_address_format(self):
        tracker = PIITracker()
        ph = tracker.placeholder("ADDRESS", "123 MG Road, Bangalore 560001", "Para 1")
        assert ph == "[Address 1]"


class TestEntityPlaceholders:
    """Entity names use letter + corporate suffix format."""

    def test_private_limited_entity(self):
        tracker = PIITracker()
        ph = tracker.placeholder("PRIVATE_LIMITED", "NeoSan Private Limited", "Para 1")
        assert ph == "X Private Limited"

    def test_llp_entity(self):
        tracker = PIITracker()
        ph = tracker.placeholder("LLP", "TechCo LLP", "Para 1")
        assert ph == "X LLP"

    def test_ltd_entity(self):
        tracker = PIITracker()
        ph = tracker.placeholder("LIMITED", "InfoSoft Limited", "Para 1")
        assert ph == "X Limited"

    def test_pvt_ltd_entity(self):
        tracker = PIITracker()
        ph = tracker.placeholder("PRIVATE_LIMITED", "Acme Pvt. Ltd.", "Para 1")
        assert ph == "X Pvt. Ltd."

    def test_inc_entity(self):
        tracker = PIITracker()
        ph = tracker.placeholder("ENTITY", "Google Inc", "Para 1")
        assert ph == "X Inc"

    def test_multiple_entities_use_different_letters(self):
        tracker = PIITracker()
        ph1 = tracker.placeholder("PRIVATE_LIMITED", "NeoSan Private Limited", "Para 1")
        ph2 = tracker.placeholder("LLP", "TechCo LLP", "Para 1")
        ph3 = tracker.placeholder("LIMITED", "InfoSoft Limited", "Para 1")
        assert ph1 == "X Private Limited"
        assert ph2 == "Y LLP"
        assert ph3 == "Z Limited"

    def test_entity_without_suffix_uses_letter_only(self):
        tracker = PIITracker()
        ph = tracker.placeholder("ENTITY", "GlobalCorp", "Para 1")
        assert ph == "X"


class TestPersonPlaceholders:
    """Person names use 'Person N' format with title preservation."""

    def test_person_name(self):
        tracker = PIITracker()
        ph = tracker.placeholder("INDIVIDUAL", "Rajesh Sharma", "Para 1")
        assert ph == "Person 1"

    def test_person_with_mr_title(self):
        tracker = PIITracker()
        ph = tracker.placeholder("INDIVIDUAL", "Mr. Rajesh Sharma", "Para 1")
        assert ph == "Mr. Person 1"

    def test_person_with_mrs_title(self):
        tracker = PIITracker()
        ph = tracker.placeholder("INDIVIDUAL", "Mrs. Kamala Devi", "Para 1")
        assert ph == "Mrs. Person 1"

    def test_person_with_dr_title(self):
        tracker = PIITracker()
        ph = tracker.placeholder("INDIVIDUAL", "Dr. Kamala Devi", "Para 1")
        assert ph == "Dr. Person 1"

    def test_person_with_shri_title(self):
        tracker = PIITracker()
        ph = tracker.placeholder("INDIVIDUAL", "Shri Ramesh Kumar", "Para 1")
        assert ph == "Shri. Person 1"

    def test_multiple_persons_increment(self):
        tracker = PIITracker()
        ph1 = tracker.placeholder("INDIVIDUAL", "Rajesh Sharma", "Para 1")
        ph2 = tracker.placeholder("INDIVIDUAL", "Kamala Devi", "Para 2")
        assert ph1 == "Person 1"
        assert ph2 == "Person 2"


class TestDeduplication:
    """Same original value always maps to the same placeholder."""

    def test_same_value_same_placeholder(self):
        tracker = PIITracker()
        ph1 = tracker.placeholder("EMAIL", "test@example.com", "Para 1")
        ph2 = tracker.placeholder("EMAIL", "test@example.com", "Para 3")
        assert ph1 == ph2 == "[Email 1]"

    def test_different_values_different_placeholders(self):
        tracker = PIITracker()
        ph1 = tracker.placeholder("EMAIL", "alice@example.com", "Para 1")
        ph2 = tracker.placeholder("EMAIL", "bob@example.com", "Para 2")
        assert ph1 == "[Email 1]"
        assert ph2 == "[Email 2]"

    def test_same_entity_same_letter(self):
        tracker = PIITracker()
        ph1 = tracker.placeholder("PRIVATE_LIMITED", "NeoSan Private Limited", "Para 1")
        ph2 = tracker.placeholder("PRIVATE_LIMITED", "NeoSan Private Limited", "Para 5")
        assert ph1 == ph2 == "X Private Limited"

    def test_entity_categories_share_letter_counter(self):
        """PRIVATE_LIMITED, LIMITED, LLP, ENTITY all share the same letter counter."""
        tracker = PIITracker()
        ph1 = tracker.placeholder("PRIVATE_LIMITED", "NeoSan Private Limited", "Para 1")
        ph2 = tracker.placeholder("LLP", "TechCo LLP", "Para 2")
        assert ph1 == "X Private Limited"
        assert ph2 == "Y LLP"


class TestAuditLog:
    """Audit log stores original text and new placeholder for every item."""

    def test_audit_log_contains_original_and_placeholder(self):
        tracker = PIITracker()
        tracker.placeholder("EMAIL", "alice@example.com", "Para 1")

        assert len(tracker.audit_log) == 1
        entry = tracker.audit_log[0]
        assert entry["original_text"] == "alice@example.com"
        assert entry["placeholder"] == "[Email 1]"
        assert entry["category"] == "EMAIL"
        assert entry["location"] == "Para 1"

    def test_audit_log_entity_placeholder(self):
        tracker = PIITracker()
        tracker.placeholder("PRIVATE_LIMITED", "NeoSan Private Limited", "Para 1")

        entry = tracker.audit_log[0]
        assert entry["original_text"] == "NeoSan Private Limited"
        assert entry["placeholder"] == "X Private Limited"

    def test_audit_log_person_placeholder(self):
        tracker = PIITracker()
        tracker.placeholder("INDIVIDUAL", "Mr. Rajesh Sharma", "Para 1")

        entry = tracker.audit_log[0]
        assert entry["original_text"] == "Mr. Rajesh Sharma"
        assert entry["placeholder"] == "Mr. Person 1"


class TestPlaceholderUtilsRecognizeBothFormats:
    """is_inside_placeholder and is_placeholder_internal_text recognize old and new formats."""

    def test_old_format_inside(self):
        text = "Hello [REDACTED_EMAIL1] world"
        assert is_inside_placeholder(text, 6) is True
        assert is_inside_placeholder(text, 10) is True
        assert is_inside_placeholder(text, 0) is False

    def test_new_bracket_format_inside(self):
        text = "Hello [Email 1] world"
        assert is_inside_placeholder(text, 6) is True
        assert is_inside_placeholder(text, 10) is True
        assert is_inside_placeholder(text, 0) is False

    def test_person_format_inside(self):
        text = "Hello Person 1 world"
        assert is_inside_placeholder(text, 6) is True
        assert is_inside_placeholder(text, 12) is True
        assert is_inside_placeholder(text, 0) is False

    def test_entity_format_inside(self):
        text = "Hello X Private Limited world"
        assert is_inside_placeholder(text, 6) is True
        assert is_inside_placeholder(text, 0) is False

    def test_old_internal_text(self):
        assert is_placeholder_internal_text("REDACTED_EMAIL1") is True
        assert is_placeholder_internal_text("[REDACTED_EMAIL1]") is True

    def test_new_bracket_internal_text(self):
        assert is_placeholder_internal_text("Email 1") is True
        assert is_placeholder_internal_text("[Email 1]") is True

    def test_person_internal_text(self):
        assert is_placeholder_internal_text("Person 1") is True
        assert is_placeholder_internal_text("Mr. Person 1") is True

    def test_non_placeholder_text(self):
        assert is_placeholder_internal_text("Hello World") is False
        assert is_placeholder_internal_text("random text") is False
