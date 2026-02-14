"""Reusable helpers for cleaning and validating person-name tokens."""

from __future__ import annotations

import re
import unicodedata

_NOISE_CHARS = "\"'`´‘’“”.,;:!?()[]{}<>|/\\"
_HEADER_STOPLIST = {
    "name",
    "names",
    "first",
    "last",
    "first_name",
    "first names",
    "firstname",
    "last_name",
    "last names",
    "lastname",
    "surname",
    "surnames",
    "given_name",
    "given names",
    "givenname",
    "full_name",
    "full names",
    "fullname",
}


def normalize_name_token(raw_token: str) -> str:
    """Normalize one name token without destructive title-casing.

    - strips wrapping punctuation/quotes noise
    - preserves apostrophes and hyphens between letters (for example O'Neil, D'Souza)
    - keeps existing casing to avoid destructive conversion edge cases
    """

    token = unicodedata.normalize("NFKC", raw_token or "").strip()
    if not token:
        return ""

    token = token.strip(_NOISE_CHARS)
    token = re.sub(r"\s+", " ", token)
    token = re.sub(r"[\-_]+", "-", token)
    token = re.sub(r"['’]+", "'", token)

    # Keep apostrophes/hyphens only when surrounded by letters.
    token = re.sub(r"(?<![A-Za-z])[\-']+", "", token)
    token = re.sub(r"[\-']+(?![A-Za-z])", "", token)
    token = re.sub(r"[^A-Za-z\-']", "", token)

    token = re.sub(r"-{2,}", "-", token)
    token = re.sub(r"'{2,}", "'", token)

    return token.strip("-'")


def is_header_token(token: str) -> bool:
    """Return True for obvious CSV header-like values."""

    normalized = token.strip().lower().replace("-", "_")
    return normalized in _HEADER_STOPLIST


def is_valid_name_token(token: str, *, min_len: int = 2, max_len: int = 40) -> bool:
    """Apply generic quality filters to normalized name tokens."""

    if not token:
        return False
    if is_header_token(token):
        return False
    if len(token) < min_len or len(token) > max_len:
        return False
    if any(ch.isdigit() for ch in token):
        return False

    letter_count = sum(ch.isalpha() for ch in token)
    if letter_count < min_len:
        return False
    if letter_count / len(token) < 0.7:
        return False

    return True
