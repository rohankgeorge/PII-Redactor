"""
Global PII detection patterns and helpers.
"""
import re

US_ZIP_PATTERN = r"\d{5}(?:-\d{4})?"
UK_POSTCODE_PATTERN = (
    r"(?:GIR\s?0AA|"
    r"(?:(?:[A-Z][0-9]{1,2})|(?:[A-Z]{2}[0-9]{1,2})|"
    r"(?:[A-Z][0-9][A-Z])|(?:[A-Z]{2}[0-9][A-Z]))\s?[0-9][A-Z]{2})"
)

GLOBAL_POSTAL_CODE_PATTERNS = [
    ("US_ZIP_CODE", re.compile(rf"\b{US_ZIP_PATTERN}\b")),
    ("UK_POSTCODE", re.compile(rf"\b{UK_POSTCODE_PATTERN}\b", re.IGNORECASE)),
]
