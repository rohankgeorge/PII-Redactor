"""Shared helpers for detecting redaction placeholders and their spans."""

from __future__ import annotations

import re

PLACEHOLDER_PATTERN = re.compile(r"\[REDACTED_[A-Z_]+\d+\]")
PLACEHOLDER_INNER_PATTERN = re.compile(r"REDACTED_[A-Z_]+\d+")


def is_inside_placeholder(text: str, start: int) -> bool:
    """Return True if ``start`` falls inside any ``[REDACTED_...]`` placeholder span."""
    for match in PLACEHOLDER_PATTERN.finditer(text):
        if match.start() <= start < match.end():
            return True
    return False


def is_placeholder_internal_text(span: str) -> bool:
    """Return True if ``span`` is placeholder text with or without surrounding brackets."""
    cleaned = span.strip().strip("[]")
    return bool(PLACEHOLDER_INNER_PATTERN.fullmatch(cleaned))
