"""
Comprehensive PII redaction engine with unique numbering.
Detects: entity names, full addresses, universal person names, and all Indian IDs.
"""
import re
from typing import Dict, List

from indian_pii_data import (
    PII_REGEX_PATTERNS,
    INDIAN_FIRST_NAMES,
    INDIAN_SURNAMES,
    INDIAN_CITIES,
    INDIAN_STATES,
)


# ────────────────────────────────────────────────────────────
# PIITracker – assigns unique numbered placeholders
# ────────────────────────────────────────────────────────────
class PIITracker:
    """Track unique PII values and assign sequential numbers per category."""

    def __init__(self):
        self._registry: Dict[str, Dict[str, int]] = {}
        self.stats: Dict[str, int] = {}
        self.audit_log: list = []

    def placeholder(self, category: str, original: str, context: str = "") -> str:
        key = original.strip().lower()
        if not key:
            return original

        if category not in self._registry:
            self._registry[category] = {}

        reg = self._registry[category]
        if key not in reg:
            reg[key] = len(reg) + 1

        num = reg[key]
        self.stats[category] = self.stats.get(category, 0) + 1
        ph = f"[REDACTED_{category}{num}]"
        self.audit_log.append({
            "category": category,
            "placeholder": ph,
            "location": context,
        })
        return ph

    @property
    def total(self) -> int:
        return len(self.audit_log)


# ────────────────────────────────────────────────────────────
# Compiled patterns
# ────────────────────────────────────────────────────────────

# Entity suffixes
_ENTITY_SUFFIX = (
    r"(?:Private\s+Limited|Pvt\.?\s*Ltd\.?|Limited|Ltd\.?|LLP|LLC|"
    r"Inc\.?|Corporation|Corp\.?|Co\.?|Foundation|Trust|Associates|"
    r"Enterprises|Industries|Services|Holdings|Group|Partners|Bank)"
)
ENTITY_PATTERN = re.compile(
    r"\b(?!(?:Mr|Mrs|Ms|Dr|Prof|Shri|Smt|Sri)\.?\s)"   # Exclude titles
    r"([A-Z][\w]+(?:[\s&]+[A-Z][\w]+){0,6})\s+"
    + _ENTITY_SUFFIX + r"\.?\b",
    re.IGNORECASE,
)

def _entity_category(suffix: str) -> str:
    s = suffix.lower().replace(".", "").replace(" ", "")
    if "privatelimited" in s or "pvtltd" in s:
        return "PRIVATE_LIMITED"
    if "limited" in s or "ltd" in s:
        return "LIMITED"
    if "llp" in s:
        return "LLP"
    return "ENTITY"


# Full address: number → PIN code (6-digit), optionally followed by India
_ADDR_START = (
    r"(?:No\.?\s*|#\s*|Flat\s+(?:No\.?\s*)?|House\s+(?:No\.?\s*)?|"
    r"Plot\s+(?:No\.?\s*)?|Sy\.?\s*No\.?\s*|S\.?\s*No\.?\s*)?"
)
FULL_ADDRESS_PATTERN = re.compile(
    _ADDR_START
    + r"[A-Za-z]?\d[\w/.\-]*"           # Starting identifier (36, No.97, E123)
    + r"\s*"                              # Optional space after number
    + r"(?=[\w\s,./\-\'()\&\d:;]*,)"     # Lookahead: must contain comma (address is multi-part)
    + r"[\w\s,./\-\'()\&\d:;]+?"         # Address body (lazy)
    + r"[\s,\-–]*[1-9]\d{5}"             # PIN code
    + r"(?:\s*,?\s*India)?",              # Optional country
)

# Road-starting address (Magadi Main Road ... PIN)
ROAD_ADDRESS_PATTERN = re.compile(
    r"[A-Z][a-z]+(?:\s+[A-Za-z]+)*?\s+(?:Road|Main\s+Road|Street|Marg|Highway)"
    r"[\s,]+[\w][\w\s,./\-\'()\&\d:;]+?"
    r"[\s,\-–]*[1-9]\d{5}"
    r"(?:\s*,?\s*India)?",
)

# Location-based address (named place, ... PIN)
PLACE_ADDRESS_PATTERN = re.compile(
    r"[A-Z][a-z]+(?:\s+[A-Za-z][a-z]+)*,"    # Place name followed by comma
    r"[\w\s,./\-\'()\&\d:;]+?"                # Address body
    r"[\s,\-–]*[1-9]\d{5}"                     # PIN code
    r"(?:\s*,?\s*India)?",
)

# Title-based person name
TITLE_NAME_PATTERN = re.compile(
    r"(?:Mr\.?\s*|Mrs\.?\s*|Ms\.?\s*|Dr\.?\s*|Prof\.?\s*|"
    r"Shri\.?\s*|Smt\.?\s*|Sri\.?\s*)"
    r"([A-Z][a-z']+(?:\s+[A-Z][a-z']+|\s+[A-Z]\.)*"
    r"(?:\s+[dDlL]\'?\s*[A-Z][a-z']+)?)",       # Handle D'Rozario etc.
)

# Name from context ("Name:" or "Name & Title:")
CONTEXT_NAME_PATTERN = re.compile(
    r"(?:Name(?:\s*&\s*Title)?(?:\s+of\s+\w+(?:'s)?\s+Representative)?)\s*"
    r"[:\-–]\s*"
    r"([A-Z][a-z']+(?:\s+[A-Z]\.|\s+[A-Z][a-z']+|\s+[dDlL]\'?\s*[A-Z][a-z']+)*)",
)

# Build massive name set and pattern
_ALL_NAMES = sorted(INDIAN_FIRST_NAMES | INDIAN_SURNAMES, key=len, reverse=True)
_NAME_ALTERNATION = "|".join(re.escape(n) for n in _ALL_NAMES) if _ALL_NAMES else None
NAME_DICT_PATTERN = re.compile(
    r"\b(" + _NAME_ALTERNATION + r")\b"
) if _NAME_ALTERNATION else None

# Location pattern
_ALL_LOCS = sorted(INDIAN_CITIES | INDIAN_STATES, key=len, reverse=True)
_LOC_ALTERNATION = "|".join(re.escape(loc) for loc in _ALL_LOCS) if _ALL_LOCS else None
LOCATION_DICT_PATTERN = re.compile(
    r"\b(" + _LOC_ALTERNATION + r")\b", re.IGNORECASE
) if _LOC_ALTERNATION else None

# Consecutive capitalized words (2+ words, potential names)
CONSEC_CAP_PATTERN = re.compile(
    r"\b([A-Z][a-z']{1,20}(?:\s+[A-Z]\.)*"
    r"(?:\s+[A-Z][a-z']{1,20}){1,5}"
    r"(?:\s+[dDlL]\'?[A-Z][a-z']+)?)\b"
)

# Stop words that look like capitalized phrases but aren't names
_STOP_PHRASES = {
    "first part", "second part", "third part", "fourth part",
    "effective date", "closing date", "long stop date", "long-stop date",
    "share transfer agreement", "share purchase price", "revenue share payment",
    "non compete", "non disclosure", "non solicitation", "non disparagement",
    "master settlement agreement", "technology transfer", "ip assignment",
    "intellectual property", "first information report", "look out circular",
    "legacy agreements", "settlement documents", "closing actions",
    "material breach", "confidential information", "assigned ip",
    "completion meeting", "conditions precedent", "mutual releases",
    "governing law", "interim relief", "extended non compete",
    "full and final", "covenant not to sue", "cross default",
    "signing pack", "simultaneous exchange", "ancillary documents",
    "share transfer forms", "resignation letters", "proof of release",
    "joint other actions", "compliance checks", "quality assurance",
}

# ────────────────────────────────────────────────────────────
# Redaction functions – ordered by priority
# ────────────────────────────────────────────────────────────

def _already_redacted(text: str, start: int, end: int) -> bool:
    """Check if position overlaps with an existing placeholder."""
    snippet = text[max(0, start - 1):end + 1]
    return "[REDACTED_" in snippet


def _redact_addresses(text: str, tracker: PIITracker, ctx: str) -> str:
    """Pass 1: Detect and redact full address blocks (number → PIN → India)."""
    for pattern in [FULL_ADDRESS_PATTERN, ROAD_ADDRESS_PATTERN]:
        def _repl(m):
            if "[REDACTED_" in m.group():
                return m.group()
            return tracker.placeholder("ADDRESS", m.group(), ctx)
        text = pattern.sub(_repl, text)
    return text


def _redact_entities(text: str, tracker: PIITracker, ctx: str) -> str:
    """Pass 2: Detect entity names with corporate suffixes."""
    seen_short_names = []

    def _repl(m):
        full = m.group().strip().rstrip(".")
        if "[REDACTED_" in full:
            return m.group()
        name_part = m.group(1).strip()
        # Determine category from suffix (everything after the name part)
        suffix_part = full[len(name_part):].strip()
        cat = _entity_category(suffix_part)
        seen_short_names.append(name_part)
        return tracker.placeholder(cat, full, ctx)

    text = ENTITY_PATTERN.sub(_repl, text)

    # Also catch standalone references to detected entity short names
    for sn in seen_short_names:
        if len(sn) >= 3:
            safe = re.escape(sn)
            def _sn_repl(m, _sn=sn):
                if "[REDACTED_" in text[max(0, m.start() - 10):m.start()]:
                    return m.group()
                return tracker.placeholder("ENTITY", _sn, ctx)
            text = re.sub(r"\b" + safe + r"\b", _sn_repl, text)

    return text


def _redact_ids(text: str, tracker: PIITracker, ctx: str) -> str:
    """Pass 3: Detect specific ID patterns (Aadhaar, PAN, etc.)."""
    for category, pattern in PII_REGEX_PATTERNS:
        def _repl(m, cat=category):
            if "[REDACTED_" in m.group():
                return m.group()
            return tracker.placeholder(cat, m.group(), ctx)
        text = pattern.sub(_repl, text)
    return text


def _redact_names(text: str, tracker: PIITracker, ctx: str) -> str:
    """Pass 4: Detect person names (titles, context, dictionary, heuristic)."""

    # 4a: Title-based names (Mr./Mrs./Dr. + following name)
    def _title_repl(m):
        if "[REDACTED_" in m.group():
            return m.group()
        return tracker.placeholder("INDIVIDUAL", m.group().strip(), ctx)
    text = TITLE_NAME_PATTERN.sub(_title_repl, text)

    # 4b: Context-based names ("Name:" patterns)
    def _ctx_repl(m):
        name = m.group(1).strip()
        if "[REDACTED_" in name or len(name) < 3:
            return m.group()
        prefix = m.group()[:m.group().index(name)]
        return prefix + tracker.placeholder("INDIVIDUAL", name, ctx)
    text = CONTEXT_NAME_PATTERN.sub(_ctx_repl, text)

    # 4c: Dictionary-based Indian names (single words)
    if NAME_DICT_PATTERN:
        def _dict_repl(m):
            if "[REDACTED_" in text[max(0, m.start() - 12):m.start()]:
                return m.group()
            return tracker.placeholder("INDIVIDUAL", m.group(), ctx)
        text = NAME_DICT_PATTERN.sub(_dict_repl, text)

    # 4d: Consecutive capitalized words heuristic
    def _consec_repl(m):
        phrase = m.group().strip()
        if "[REDACTED_" in phrase:
            return m.group()
        if phrase.lower() in _STOP_PHRASES:
            return m.group()
        # Check if at least one word is a known name
        words = phrase.split()
        has_known = any(w in INDIAN_FIRST_NAMES or w in INDIAN_SURNAMES for w in words)
        if has_known and len(words) >= 2:
            return tracker.placeholder("INDIVIDUAL", phrase, ctx)
        return m.group()
    text = CONSEC_CAP_PATTERN.sub(_consec_repl, text)

    return text


def _redact_locations(text: str, tracker: PIITracker, ctx: str) -> str:
    """Pass 5: Detect remaining location names (cities/states)."""
    if not LOCATION_DICT_PATTERN:
        return text

    def _repl(m):
        if "[REDACTED_" in text[max(0, m.start() - 12):m.start()]:
            return m.group()
        return tracker.placeholder("LOCATION", m.group(), ctx)
    return LOCATION_DICT_PATTERN.sub(_repl, text)


# ────────────────────────────────────────────────────────────
# Main entry point
# ────────────────────────────────────────────────────────────

def redact_text(text: str, tracker: PIITracker, context: str = "") -> str:
    """Apply all redaction passes in priority order."""
    if not text or not text.strip():
        return text

    text = _redact_addresses(text, tracker, context)
    text = _redact_entities(text, tracker, context)
    text = _redact_ids(text, tracker, context)
    text = _redact_names(text, tracker, context)
    text = _redact_locations(text, tracker, context)

    return text
