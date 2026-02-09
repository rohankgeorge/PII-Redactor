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
        self._alias_registry: Dict[str, Dict[str, int]] = {}
        self._alias_terms: Dict[str, str] = {}
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

    def register_alias(self, category: str, original: str, alias: str, context: str = "") -> str:
        label_type = _label_type_for_category(category)
        original_key = original.strip().lower()
        alias_key = alias.strip().lower()
        if not original_key or not alias_key:
            return alias
        if alias_key in self._alias_terms:
            return self._alias_terms[alias_key]

        if label_type not in self._alias_registry:
            self._alias_registry[label_type] = {}

        label_registry = self._alias_registry[label_type]
        if original_key not in label_registry:
            label_registry[original_key] = len(label_registry) + 1

        label_num = label_registry[original_key]
        label = f"{label_type} {label_num}"
        self._alias_terms[alias_key] = label
        self.audit_log.append({
            "category": f"{label_type.upper()}_ALIAS",
            "placeholder": label,
            "location": context,
        })
        return label

    def alias_label(self, term: str) -> str:
        return self._alias_terms.get(term.strip().lower(), "")

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
    + r"(?i:" + _ENTITY_SUFFIX + r")" + r"\.?\b",       # Case-insensitive suffix only
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
    r"(?:^|(?<=\s)|(?<=:)|(?<=\n))"          # Must start at boundary
    + _ADDR_START
    + r"(?!(?:19|20)\d{2}\b)"                 # Exclude years (1900-2099)
    + r"[A-Za-z]?\d[\w/.\-]*"                 # Starting identifier
    + r"\s*"
    + r"(?=[\w\s,./\-\'()\&\d:;]*,)"
    + r"[\w\s,./\-\'()\&\d:;]+?"
    + r"[\s,\-–]*[1-9]\d{5}"
    + r"(?:\s*,?\s*India)?",
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
    r"([A-Z][a-z]+(?:"
    r"\s+[A-Z]'[A-Z][a-z]+"       # D'Rozario
    r"|\s+[A-Z]\s+[A-Z][a-z]+"    # D Rozario (initial + space + name)
    r"|\s+[A-Z][a-z]+"            # Regular word (Sean, Sharma)
    r"|\s+[A-Z]\."                # Initial with dot (N.)
    r")*)",
)

# Name from context ("Name:" or "Name & Title:")
CONTEXT_NAME_PATTERN = re.compile(
    r"(?:Name(?:\s*&\s*Title)?(?:\s+of\s+\w+(?:'s)?\s+Representative)?)\s*"
    r"[:\-–]\s*"
    r"([A-Z][a-z]+(?:"
    r"\s+[A-Z]'[A-Z][a-z]+"
    r"|\s+[A-Z]\s+[A-Z][a-z]+"
    r"|\s+[A-Z][a-z]+"
    r"|\s+[A-Z]\."
    r")*)",
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
    r"\b([A-Z][a-z]{1,20}(?:"
    r"\s+[A-Z]'[A-Z][a-z]+"        # D'Rozario
    r"|\s+[A-Z]\s+[A-Z][a-z]+"     # D Rozario
    r"|\s+[A-Z][a-z]{1,20}"        # Regular name word
    r"|\s+[A-Z]\."                  # Initial with dot
    r"){1,5})\b"
)

DEFINED_TERM_QUOTED_PATTERN = re.compile(
    r"(?:\(|,|–|-)\s*(?:the\s+)?[\"'“‘](?P<term>[A-Z][\w&\-]{1,40})[\"'”’]"
)
DEFINED_TERM_PLAIN_PATTERN = re.compile(
    r"(?:\(|,|–|-)\s*(?:the\s+)?(?P<term>[A-Z][A-Za-z0-9&\-]{2,40})\b"
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

def _label_type_for_category(category: str) -> str:
    if category in {"PRIVATE_LIMITED", "LIMITED", "LLP", "ENTITY"}:
        return "Entity"
    return "Individual"


def _is_inside_placeholder(text: str, pos: int) -> bool:
    """Check if a position is inside an existing [REDACTED_...] tag."""
    before = text[:pos]
    last_open = before.rfind("[REDACTED_")
    if last_open < 0:
        return False
    last_close = before.rfind("]", last_open)
    return last_close < last_open  # Open bracket found with no matching close


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

    def _capture_defined_terms(match):
        full = match.group().strip().rstrip(".")
        fl = full.lower().replace(".", "").replace(" ", "")
        if "privatelimited" in fl or "pvtltd" in fl:
            cat = "PRIVATE_LIMITED"
        elif "llp" in fl:
            cat = "LLP"
        elif "limited" in fl or "ltd" in fl:
            cat = "LIMITED"
        else:
            cat = "ENTITY"
        tail = text[match.end():match.end() + 140]
        for pattern in (DEFINED_TERM_QUOTED_PATTERN, DEFINED_TERM_PLAIN_PATTERN):
            alias_match = pattern.search(tail)
            if not alias_match:
                continue
            alias = alias_match.group("term")
            tracker.register_alias(cat, full, alias, ctx)
            break

    for match in ENTITY_PATTERN.finditer(text):
        if _is_inside_placeholder(text, match.start()):
            continue
        _capture_defined_terms(match)

    def _repl(m):
        full = m.group().strip().rstrip(".")
        if _is_inside_placeholder(text, m.start()):
            return m.group()
        name_part = m.group(1).strip()
        # Determine category from full matched text
        fl = full.lower().replace(".", "").replace(" ", "")
        if "privatelimited" in fl or "pvtltd" in fl:
            cat = "PRIVATE_LIMITED"
        elif "llp" in fl:
            cat = "LLP"
        elif "limited" in fl or "ltd" in fl:
            cat = "LIMITED"
        else:
            cat = "ENTITY"
        seen_short_names.append(name_part.split()[0])  # First word for standalone detection
        return tracker.placeholder(cat, full, ctx)

    text = ENTITY_PATTERN.sub(_repl, text)

    # Also catch standalone references to detected entity short names
    for sn in seen_short_names:
        if len(sn) >= 3:
            safe = re.escape(sn)
            def _sn_repl(m, _sn=sn):
                if _is_inside_placeholder(text, m.start()):
                    return m.group()
                return tracker.placeholder("ENTITY", _sn, ctx)
            text = re.sub(r"\b" + safe + r"\b", _sn_repl, text)

    return text


def _redact_defined_terms(text: str, tracker: PIITracker, ctx: str) -> str:
    """Replace defined-term aliases with anonymized labels."""
    for alias_key, label in tracker._alias_terms.items():
        safe = re.escape(alias_key)
        pattern = re.compile(r"\b" + safe + r"\b", re.IGNORECASE)
        def _alias_repl(m, _label=label):
            if _is_inside_placeholder(text, m.start()):
                return m.group()
            return _label
        text = pattern.sub(_alias_repl, text)
    return text


def _redact_pre_address_ids(text: str, tracker: PIITracker, ctx: str) -> str:
    """Pass 2: Detect specific IDs BEFORE addresses (Aadhaar, PAN, etc. — not PIN codes)."""
    for category, pattern in PII_REGEX_PATTERNS:
        if category == "PIN_CODE":
            continue  # PIN codes handled after addresses
        def _repl(m, cat=category):
            if _is_inside_placeholder(text, m.start()):
                return m.group()
            return tracker.placeholder(cat, m.group(), ctx)
        text = pattern.sub(_repl, text)
    return text


def _redact_post_address_ids(text: str, tracker: PIITracker, ctx: str) -> str:
    """Pass 4: Detect standalone PIN codes (those not already captured in addresses)."""
    for category, pattern in PII_REGEX_PATTERNS:
        if category != "PIN_CODE":
            continue
        def _repl(m, cat=category):
            if _is_inside_placeholder(text, m.start()):
                return m.group()
            return tracker.placeholder(cat, m.group(), ctx)
        text = pattern.sub(_repl, text)
    return text


def _redact_names(text: str, tracker: PIITracker, ctx: str) -> str:
    """Pass 4: Detect person names (titles, context, dictionary, heuristic)."""

    # 4a: Title-based names (Mr./Mrs./Dr. + following name)
    def _title_repl(m):
        if _is_inside_placeholder(text, m.start()):
            return m.group()
        # Track by name-only (group 1) so "Mr. X" and "X" get the same number
        return tracker.placeholder("INDIVIDUAL", m.group(1).strip(), ctx)
    text = TITLE_NAME_PATTERN.sub(_title_repl, text)

    # 4b: Context-based names ("Name:" patterns)
    def _ctx_repl(m):
        name = m.group(1).strip()
        if _is_inside_placeholder(text, m.start()) or len(name) < 3:
            return m.group()
        prefix = m.group()[:m.group().index(name)]
        return prefix + tracker.placeholder("INDIVIDUAL", name, ctx)
    text = CONTEXT_NAME_PATTERN.sub(_ctx_repl, text)

    # 4c: Consecutive capitalized words (catch multi-word names before single words)
    def _consec_repl(m):
        phrase = m.group().strip()
        if _is_inside_placeholder(text, m.start()):
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

    # 4d: Dictionary-based Indian names (single words — catch remaining)
    if NAME_DICT_PATTERN:
        def _dict_repl(m):
            if _is_inside_placeholder(text, m.start()):
                return m.group()
            return tracker.placeholder("INDIVIDUAL", m.group(), ctx)
        text = NAME_DICT_PATTERN.sub(_dict_repl, text)

    return text


def _redact_locations(text: str, tracker: PIITracker, ctx: str) -> str:
    """Pass 5: Detect remaining location names (cities/states)."""
    if not LOCATION_DICT_PATTERN:
        return text

    def _repl(m):
        if _is_inside_placeholder(text, m.start()):
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

    text = _redact_pre_address_ids(text, tracker, context)
    text = _redact_addresses(text, tracker, context)
    text = _redact_entities(text, tracker, context)
    text = _redact_defined_terms(text, tracker, context)
    text = _redact_post_address_ids(text, tracker, context)
    text = _redact_names(text, tracker, context)
    text = _redact_locations(text, tracker, context)

    return text
