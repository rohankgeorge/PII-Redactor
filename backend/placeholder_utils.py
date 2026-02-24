"""Shared helpers for detecting redaction placeholders and their spans."""

from __future__ import annotations

import re

# Old format: [REDACTED_CATEGORY_N]
PLACEHOLDER_PATTERN_OLD = re.compile(r"\[REDACTED_[A-Z_]+\d+\]")
PLACEHOLDER_INNER_PATTERN_OLD = re.compile(r"REDACTED_[A-Z_]+\d+")

# New format: [Category N] (e.g., [Aadhaar 1], [Location 2], [Email 1])
PLACEHOLDER_PATTERN_BRACKET = re.compile(
    r"\[(?:Aadhaar|PAN|Phone|Email|Bank Account|GST|IFSC|Passport|Voter ID|DL|"
    r"Vehicle Reg|UPI|DOB|PIN|Location|Address|ZIP|Postcode)\s+\d+\]"
)

# New format: Person N (with optional title prefix)
PLACEHOLDER_PATTERN_PERSON = re.compile(
    r"(?:(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.|Shri\.|Smt\.|Sri\.)\s+)?Person\s+\d+"
)

# New format: Entity letters with corporate suffix (e.g., "X Private Limited", "Y LLP")
PLACEHOLDER_PATTERN_ENTITY = re.compile(
    r"\b[A-Z]\s+(?:Private\s+Limited|Pvt\.?\s*Ltd\.?|Limited|Ltd\.?|LLP|LLC|"
    r"Inc\.?|Corporation|Corp\.?|Co\.?|Foundation|Trust|Associates|"
    r"Enterprises|Industries|Services|Holdings|Group|Partners|Bank|"
    r"Associations?|Owners?\s*(?:'s\s*)?Association|Society|Federation|"
    r"Chamber|Firm|Audit\s+Firm)\b",
    re.IGNORECASE,
)

# Combined pattern matching any placeholder format
PLACEHOLDER_PATTERN = re.compile(
    r"(?:" + PLACEHOLDER_PATTERN_OLD.pattern + r")"
    r"|(?:" + PLACEHOLDER_PATTERN_BRACKET.pattern + r")"
    r"|(?:" + PLACEHOLDER_PATTERN_PERSON.pattern + r")"
    r"|(?:" + PLACEHOLDER_PATTERN_ENTITY.pattern + r")",
    re.IGNORECASE,
)

PLACEHOLDER_INNER_PATTERN = PLACEHOLDER_INNER_PATTERN_OLD


def is_inside_placeholder(text: str, start: int) -> bool:
    """Return True if ``start`` falls inside any placeholder span (old or new format)."""
    for match in PLACEHOLDER_PATTERN.finditer(text):
        if match.start() <= start < match.end():
            return True
    return False


def is_placeholder_internal_text(span: str) -> bool:
    """Return True if ``span`` is placeholder text with or without surrounding brackets."""
    cleaned = span.strip().strip("[]")
    # Check old format
    if PLACEHOLDER_INNER_PATTERN_OLD.fullmatch(cleaned):
        return True
    # Check new bracket format (without brackets)
    bracket_inner = re.compile(
        r"(?:Aadhaar|PAN|Phone|Email|Bank Account|GST|IFSC|Passport|Voter ID|DL|"
        r"Vehicle Reg|UPI|DOB|PIN|Location|Address|ZIP|Postcode)\s+\d+"
    )
    if bracket_inner.fullmatch(cleaned):
        return True
    # Check Person N format
    if re.fullmatch(r"(?:(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.|Shri\.|Smt\.|Sri\.)\s+)?Person\s+\d+", span.strip()):
        return True
    return False
