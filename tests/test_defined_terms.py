import sys
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from pii_engine import NameDetectionConfig, PIITracker, redact_text  # noqa: E402


class TestDefinedTermAliases(unittest.TestCase):
    def setUp(self) -> None:
        self.name_config = NameDetectionConfig(
            use_title=False,
            use_context_label=False,
            use_contextual_cues=False,
            use_consecutive_caps=False,
            use_dictionary=False,
        )

    def test_hereinafter_referred_to_as_alias_replaced(self) -> None:
        text = (
            "Acme Private Limited (hereinafter referred to as the \"Company\") agrees. "
            "Clause 1.1 The Company shall pay."
        )
        tracker = PIITracker()
        redacted = redact_text(text, tracker, context="test", name_config=self.name_config)

        self.assertIn("Entity 1", redacted)
        self.assertNotIn("Company", redacted)

    def test_defined_as_plain_alias_replaced(self) -> None:
        text = (
            "Beta Industries LLP (defined as Buyer) agrees. "
            "Clause 1.1 Buyer shall pay."
        )
        tracker = PIITracker()
        redacted = redact_text(text, tracker, context="test", name_config=self.name_config)

        self.assertIn("Entity 1", redacted)
        self.assertNotIn("Buyer", redacted)


if __name__ == "__main__":
    unittest.main()
