"""
Comprehensive PII redaction engine with unique numbering.
Detects: entity names, full addresses, universal person names, and all Indian IDs.
"""
from dataclasses import dataclass
import json
import os
import re
from typing import Dict, List, Set, Tuple

from indian_pii_data import (
    PII_REGEX_PATTERNS,
    INDIAN_FIRST_NAMES,
    INDIAN_SURNAMES,
    INDIAN_CITIES,
    INDIAN_STATES,
)
from global_pii_data import (
    GLOBAL_POSTAL_CODE_PATTERNS,
    US_ZIP_PATTERN,
    UK_POSTCODE_PATTERN,
)

import nlp_engine
import rule_library
from placeholder_utils import is_inside_placeholder as _is_inside_placeholder, is_placeholder_internal_text


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
        self.qa_signals: list = []

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
            "original_text": original,
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
            "original_text": alias,
        })
        return label

    def alias_label(self, term: str) -> str:
        return self._alias_terms.get(term.strip().lower(), "")

    @property
    def total(self) -> int:
        return sum(1 for row in self.audit_log if row.get("category") != "POTENTIAL_LEAK")


# ────────────────────────────────────────────────────────────
# Compiled patterns
# ────────────────────────────────────────────────────────────

# Entity suffixes are configurable via this lexicon. Keep backward-compatible
# corporate forms while adding legal-domain variants.
ENTITY_SUFFIX_LEXICON = [
    "Private Limited",
    "Pvt Ltd",
    "Pvt. Ltd.",
    "Limited",
    "Ltd",
    "Ltd.",
    "LLP",
    "LLC",
    "Inc",
    "Inc.",
    "Corporation",
    "Corp",
    "Corp.",
    "Co",
    "Co.",
    "Foundation",
    "Trust",
    "Associates",
    "Enterprises",
    "Industries",
    "Services",
    "Holdings",
    "Group",
    "Partners",
    "Bank",
    "Association",
    "Associations",
    "Owners Association",
    "Owner's Association",
    "Society",
    "Federation",
    "Chamber",
    "Firm",
    "Audit Firm",
]


def _build_entity_suffix_pattern(entries: List[str]) -> str:
    escaped_entries = []
    for entry in entries:
        escaped = re.escape(entry.strip())
        escaped_entries.append(escaped.replace(r"\ ", r"\s+"))
    escaped_entries.sort(key=len, reverse=True)
    return r"(?:" + "|".join(escaped_entries) + r")"


_ENTITY_SUFFIX = _build_entity_suffix_pattern(ENTITY_SUFFIX_LEXICON)
ENTITY_PATTERN = re.compile(
    r"\b(?!(?:Mr|Mrs|Ms|Dr|Prof|Shri|Smt|Sri)\.?\s)"   # Exclude titles
    r"([A-Z][\w]+(?:[\s&]+[A-Z][\w]+){0,6})\s+"
    + r"(?i:" + _ENTITY_SUFFIX + r")" + r"\b",       # Case-insensitive suffix only
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
_STREET_SUFFIX = (
    r"(?:Street|St\.?|Road|Rd\.?|Avenue|Ave\.?|Boulevard|Blvd\.?|Lane|Ln\.?|"
    r"Drive|Dr\.?|Court|Ct\.?|Way|Parkway|Pkwy\.?|Place|Pl\.?|Terrace|Ter\.?|"
    r"Salai|Sarai|Bazaar|Nagar|Marg|Highway|Expressway|Bypass|Cross|Layout|Colony)"
)
_GLOBAL_POSTAL_PATTERN = rf"(?:{US_ZIP_PATTERN}|{UK_POSTCODE_PATTERN})"
_PIN_PATTERN = r"[1-9]\d{2}\s?\d{3}"
_PIN_OR_MASKED_PATTERN = rf"(?:{_PIN_PATTERN}|[1-9][xX*]{{5}})"
FULL_ADDRESS_PATTERN = re.compile(
    r"(?:^|(?<=\s)|(?<=:)|(?<=\n))"          # Must start at boundary
    + _ADDR_START
    + r"(?!(?:19|20)\d{2}\b)"                 # Exclude years (1900-2099)
    + r"[A-Za-z]?\d[\w/.\-]*"                 # Starting identifier
    + r"\s*"
    + r"(?=[\w\s,./\-\'()\&\d:;]*,)"
    + r"[\w\s,./\-\'()\&\d:;]+?"
    + r"[\s,\-–]*" + _PIN_PATTERN
    + r"(?:\s*,?\s*India)?",
)

# General address: street + city + state + international postal code
GENERAL_ADDRESS_PATTERN = re.compile(
    r"(?:^|(?<=\s)|(?<=:)|(?<=\n))"
    + _ADDR_START
    + r"(?!(?:19|20)\d{2}\b)"
    + r"[A-Za-z]?\d[\w/.\-]*"
    + r"\s+"
    + r"[\w\s.\-']+?\s+"
    + _STREET_SUFFIX
    + r"\s*,\s*"
    + r"[A-Za-z][A-Za-z\s.'-]+"
    + r"\s*,\s*"
    + r"(?:[A-Z]{2}|[A-Za-z][A-Za-z\s.'-]+)"
    + r"\s+"
    + _GLOBAL_POSTAL_PATTERN
    + r"(?:\s*,?\s*[A-Za-z][A-Za-z\s.'-]+)?",
    re.IGNORECASE,
)

# Road-starting address (Magadi Main Road ... PIN)
ROAD_ADDRESS_PATTERN = re.compile(
    r"(?:^|(?<=\s)|(?<=:)|(?<=\n))"
    r"(?:[A-Z][\w&().,'/\-]*(?:\s+[A-Z0-9][\w&().,'/\-]*){0,5}\s*,\s*)?"
    + _ADDR_START
    + r"(?:\d+[A-Za-z]?(?:\s*(?:&|/|-)\s*\d+[A-Za-z]?)*\s+)?"
    + r"[A-Za-z0-9][\w.'\-/]*(?:\s+[A-Za-z0-9][\w.'\-/]*){0,6}\s+"
    + _STREET_SUFFIX
    + r"[\s,]+[\w][\w\s,./\-\'()\&:;]*?"
    + r"[\s,\-–]*"
    + _PIN_OR_MASKED_PATTERN
    + r"(?:\s*,?\s*India)?",
    re.IGNORECASE,
)

# Standalone road/street line guarded by address cues or list markers
ROAD_ONLY_CONTEXT_PATTERN = re.compile(
    r"(?im)"
    r"(?P<prefix>(?:^|\n)\s*(?:(?:[A-Z]|[0-9])\.\s*)?"
    r"(?:(?:residing\s+at|address|residence|located\s+at)\s*[:\-–]\s*)?)"
    r"(?P<road>[A-Za-z0-9][\w.'-]*(?:\s+[A-Za-z0-9][\w.'-]*)*\s+"
    + _STREET_SUFFIX
    + r")"
    r"(?=\s*(?:$|\n|[,;]|[-–]|\d|[A-Za-z]))"
)

# Location-based address (named place, ... PIN)
PLACE_ADDRESS_PATTERN = re.compile(
    r"[A-Z][a-z]+(?:\s+[A-Za-z][a-z]+)*,"    # Place name followed by comma
    r"[\w\s,./\-\'()\&\d:;]+?"                # Address body
    r"[\s,\-–]*" + _PIN_PATTERN                # PIN code
    + r"(?:\s*,?\s*India)?",
)

# Multi-line address (building line + street line + city/PIN line)
MULTILINE_ADDRESS_PATTERN = re.compile(
    r"(?:^|(?<=\n)|(?<=:)|(?<=\s))"
    r"[A-Z][\w&().,'/\-]*(?:\s+[A-Z0-9][\w&().,'/\-]*)*"
    r"\s*\n"
    + _ADDR_START
    + r"[A-Za-z]?\d[\w/.\-]*"
    + r"[^\n]*?\s+"
    + _STREET_SUFFIX
    + r"[^\n]*"
    + r"\s*\n"
    r"(?:[A-Za-z][A-Za-z\s.'-]+)?"
    r"\s*[-–,]?\s*"
    + _PIN_OR_MASKED_PATTERN
    + r"(?:\s*,?\s*India)?",
    re.IGNORECASE,
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

@dataclass(frozen=True)
class NameDetectionConfig:
    use_title: bool = True
    use_context_label: bool = True
    use_contextual_cues: bool = True
    use_consecutive_caps: bool = True
    use_dictionary: bool = True
    norp_category: str = "ENTITY"


_DEFAULT_STOP_PHRASES = {
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

_NLP_LABEL_CATEGORY_MAP = {
    "PERSON": "INDIVIDUAL",
    "GPE": "LOCATION",
    "LOC": "LOCATION",
    "ORG": "ENTITY",
}

_DEFAULT_FALSE_POSITIVE_WORDS = {
    "agreement", "annexure", "appendix", "article", "act", "schedule",
    "section", "clause", "exhibit", "recital", "party",
}


def _load_name_detection_data() -> Tuple[Set[str], Set[str], NameDetectionConfig]:
    stop_phrases = {phrase.lower() for phrase in _DEFAULT_STOP_PHRASES}
    false_positive_words = {word.lower() for word in _DEFAULT_FALSE_POSITIVE_WORDS}
    config = NameDetectionConfig()
    data_path = os.path.join(os.path.dirname(__file__), "data", "stop_phrases.json")
    try:
        with open(data_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return stop_phrases, false_positive_words, config
    except json.JSONDecodeError:
        return stop_phrases, false_positive_words, config

    for phrase in data.get("stop_phrases", []):
        if isinstance(phrase, str):
            stop_phrases.add(phrase.lower().strip())
    for word in data.get("false_positive_name_words", []):
        if isinstance(word, str):
            false_positive_words.add(word.lower().strip())
    config_data = data.get("name_detection", {})
    if isinstance(config_data, dict):
        norp_category = config_data.get("norp_category", config.norp_category)
        if norp_category not in {"ENTITY", "LOCATION"}:
            norp_category = config.norp_category
        config = NameDetectionConfig(
            use_title=config_data.get("use_title", config.use_title),
            use_context_label=config_data.get("use_context_label", config.use_context_label),
            use_contextual_cues=config_data.get("use_contextual_cues", config.use_contextual_cues),
            use_consecutive_caps=config_data.get("use_consecutive_caps", config.use_consecutive_caps),
            use_dictionary=config_data.get("use_dictionary", config.use_dictionary),
            norp_category=norp_category,
        )
    return stop_phrases, false_positive_words, config


_STOP_PHRASES, _FALSE_POSITIVE_NAME_WORDS, _NAME_DETECTION_CONFIG = _load_name_detection_data()

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

_NAME_SEQUENCE_PATTERN = (
    r"([A-Z][a-z]{1,20}(?:"
    r"\s+[A-Z]'[A-Z][a-z]+"        # D'Rozario
    r"|\s+[A-Z]\s+[A-Z][a-z]+"     # D Rozario
    r"|\s+[A-Z][a-z]{1,20}"        # Regular name word
    r"|\s+[A-Z]\."                  # Initial with dot
    r"){1,5})"
)

# Consecutive capitalized words (2+ words, potential names)
CONSEC_CAP_PATTERN = re.compile(r"\b" + _NAME_SEQUENCE_PATTERN + r"\b")

# Contextual cue pattern - names after labels like "Party:", "Authorized Signatory:", "Witness:"
_CONTEXTUAL_CUES = (
    r"(?:Party|Authorized\s+Signatory|Signatory|Witness|Director|"
    r"Representative|Guarantor|Nominee|Beneficiary|Executor|"
    r"Trustee|Partner|Promoter|Shareholder|Assignee|Assignor|"
    r"Licensee|Licensor|Lessee|Lessor|Tenant|Landlord|Seller|Buyer|"
    r"Vendor|Purchaser|Borrower|Lender|Debtor|Creditor|"
    r"Complainant|Respondent|Petitioner|Appellant|Plaintiff|Defendant)"
)
CONTEXTUAL_CUE_PATTERN = re.compile(
    _CONTEXTUAL_CUES + r"\s*[:\-–]\s*" + _NAME_SEQUENCE_PATTERN,
)

DEFINED_TERM_LEAD_IN = (
    r"(?:(?i:(?:hereinafter|defined\s+as|referred\s+to\s+as|called)\s+)+)?"
    r"(?:(?i:the)\s+)?"
)
DEFINED_TERM_QUOTED_PATTERN = re.compile(
    r"(?:\(|,|–|-)\s*"
    + DEFINED_TERM_LEAD_IN
    + r"[\"'“‘](?P<term>[A-Z][\w&\-]{1,40})[\"'”’]"
)
DEFINED_TERM_PLAIN_PATTERN = re.compile(
    r"(?:\(|,|–|-)\s*"
    + DEFINED_TERM_LEAD_IN
    + r"(?P<term>[A-Z][A-Za-z0-9&\-]{2,40})\b"
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

_ADDRESS_HOUSE_TOKENS = {
    "no", "flat", "door", "house", "plot", "block", "sy", "s", "survey",
}
_ADDRESS_STREET_SUFFIXES = {
    "street", "st", "road", "rd", "avenue", "ave", "boulevard", "blvd", "lane", "ln",
    "drive", "dr", "court", "ct", "way", "parkway", "pkwy", "place", "pl", "terrace", "ter",
    "salai", "sarai", "bazaar", "nagar", "marg", "highway", "expressway", "bypass", "cross",
    "layout", "colony",
}
_ADDRESS_AREA_TOKENS = {
    # Indian locality / area naming conventions
    "area", "locality", "village", "post", "po", "district", "dist", "tehsil", "taluk",
    "hobli", "mandal", "mohalla", "peth", "wadi", "gaon", "gram", "phase", "sector",
    "extension", "extn", "main", "cross", "crossroad", "crossroads", "circle", "chowk",
    "gali", "society", "enclave", "camp", "gate", "bazar", "bazaar", "nagaram", "cheri",
    "puram", "pura", "khera", "khurd", "kalan", "thana", "pincode", "pin",
}
_ADDRESS_LEGAL_CLAUSE_TERMS = {
    "whereas", "agreement", "clause", "section", "article", "hereby", "thereof", "thereunder",
    "petitioner", "respondent", "plaintiff", "defendant", "appellant", "affidavit", "writ",
    "application", "court", "tribunal", "proceeding",
}

# ────────────────────────────────────────────────────────────
# Redaction functions – ordered by priority
# ────────────────────────────────────────────────────────────

POSTAL_CODE_CATEGORIES = {"PIN_CODE", "US_ZIP_CODE", "UK_POSTCODE"}
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


def _looks_like_non_address_legal_clause(candidate: str) -> bool:
    lowered = candidate.lower()
    legal_hits = sum(1 for term in _ADDRESS_LEGAL_CLAUSE_TERMS if term in lowered)
    cue_hits = 0
    if re.search(r"\b(?:no\.?|flat|door|house|plot|block)\b", lowered):
        cue_hits += 1
    if re.search(r"\b\d+(?:st|nd|rd|th)\b", lowered):
        cue_hits += 1
    if re.search(r"\b(?:" + "|".join(_ADDRESS_STREET_SUFFIXES) + r")\b", lowered):
        cue_hits += 1
    if re.search(_PIN_OR_MASKED_PATTERN, candidate):
        cue_hits += 1
    return legal_hits >= 2 and cue_hits <= 1


def _score_address_candidate(candidate: str) -> int:
    score = 0
    lowered = candidate.lower()
    tokens = re.findall(r"[a-z0-9./#-]+", lowered)
    token_set = set(t.rstrip(".,;:") for t in tokens)

    if any(t in _ADDRESS_HOUSE_TOKENS for t in token_set):
        score += 3
    if re.search(r"\b\d+(?:st|nd|rd|th)\b", lowered):
        score += 2

    area_hits = sum(1 for token in token_set if token in _ADDRESS_AREA_TOKENS)
    score += min(area_hits, 2) * 2
    if re.search(r"\b(?:sector|phase)\s*[-:]?\s*[a-z0-9]+\b", lowered):
        score += 2
    if re.search(r"\b(?:village|dist(?:rict)?|taluk|tehsil|mandal)\b", lowered):
        score += 2

    street_hits = sum(1 for sfx in _ADDRESS_STREET_SUFFIXES if re.search(rf"\b{re.escape(sfx)}\b", lowered))
    score += min(street_hits, 2) * 3

    city_hits = sum(1 for city in INDIAN_CITIES if re.search(rf"\b{re.escape(city.lower())}\b", lowered))
    state_hits = sum(1 for state in INDIAN_STATES if re.search(rf"\b{re.escape(state.lower())}\b", lowered))
    score += min(city_hits, 1) * 2
    score += min(state_hits, 1) * 2

    if re.search(_PIN_OR_MASKED_PATTERN, candidate):
        score += 3
    elif re.search(r"\b\d{5,6}\b", candidate):
        score += 2

    if candidate.count(",") >= 1:
        score += 1
    if candidate.count("\n") >= 1:
        score += 1

    return score


def _redact_address_fallback_candidates(text: str, tracker: PIITracker, ctx: str) -> str:
    lines = text.splitlines(keepends=True)
    if not lines:
        return text

    line_starts: List[int] = []
    cursor = 0
    for line in lines:
        line_starts.append(cursor)
        cursor += len(line)
    line_starts.append(cursor)

    threshold = 6
    candidates: List[Tuple[int, int, int]] = []
    for i in range(len(lines)):
        for window in (1, 2, 3):
            j = i + window
            if j > len(lines):
                break
            start = line_starts[i]
            end = line_starts[j]
            snippet = text[start:end]
            trimmed = snippet.strip()
            if len(trimmed) < 12 or "[REDACTED_" in snippet:
                continue
            left_trim = len(snippet) - len(snippet.lstrip())
            right_trim = len(snippet) - len(snippet.rstrip())
            span_start = start + left_trim
            span_end = end - right_trim
            if span_end <= span_start:
                continue
            if _is_inside_placeholder(text, span_start) or _looks_like_non_address_legal_clause(trimmed):
                continue
            score = _score_address_candidate(trimmed)
            if score >= threshold:
                candidates.append((span_start, span_end, score))

    if not candidates:
        return text

    candidates.sort(key=lambda item: (item[0], -(item[1] - item[0]), -item[2]))
    selected: List[Tuple[int, int]] = []
    last_end = -1
    for start, end, _ in candidates:
        if start < last_end:
            continue
        selected.append((start, end))
        last_end = end

    if not selected:
        return text

    out = text
    for start, end in reversed(selected):
        original = out[start:end]
        if "[REDACTED_" in original:
            continue
        out = out[:start] + tracker.placeholder("ADDRESS", original, ctx) + out[end:]
    return out


def _redact_addresses(text: str, tracker: PIITracker, ctx: str) -> str:
    """Pass 1: Detect and redact full address blocks (number → PIN → India)."""
    def _road_only_repl(m):
        road = m.group("road")
        if "[REDACTED_" in road or _is_inside_placeholder(text, m.start("road")):
            return m.group()
        return f"{m.group('prefix')}{tracker.placeholder('ADDRESS', road, ctx)}"

    text = ROAD_ONLY_CONTEXT_PATTERN.sub(_road_only_repl, text)
    for pattern in [
        MULTILINE_ADDRESS_PATTERN,
        FULL_ADDRESS_PATTERN,
        ROAD_ADDRESS_PATTERN,
        PLACE_ADDRESS_PATTERN,
        GENERAL_ADDRESS_PATTERN,
    ]:
        def _repl(m):
            if "[REDACTED_" in m.group():
                return m.group()
            return tracker.placeholder("ADDRESS", m.group(), ctx)
        text = pattern.sub(_repl, text)
    text = _redact_address_fallback_candidates(text, tracker, ctx)
    return text


def _redact_entities(text: str, tracker: PIITracker, ctx: str) -> str:
    """Pass 2: Detect entity names with corporate suffixes."""
    seen_short_names = []

    def _capture_defined_terms(match):
        full = match.group().strip().rstrip(".")
        cat = _entity_category(full)
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
        cat = _entity_category(full)
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
        if category in POSTAL_CODE_CATEGORIES:
            continue  # PIN codes handled after addresses
        def _repl(m, cat=category):
            if _is_inside_placeholder(text, m.start()):
                return m.group()
            return tracker.placeholder(cat, m.group(), ctx)
        text = pattern.sub(_repl, text)
    return text


def _redact_post_address_ids(text: str, tracker: PIITracker, ctx: str) -> str:
    """Pass 4: Detect standalone PIN codes (those not already captured in addresses)."""
    for category, pattern in PII_REGEX_PATTERNS + GLOBAL_POSTAL_CODE_PATTERNS:
        if category not in POSTAL_CODE_CATEGORIES:
            continue
        def _repl(m, cat=category):
            if _is_inside_placeholder(text, m.start()):
                return m.group()
            return tracker.placeholder(cat, m.group(), ctx)
        text = pattern.sub(_repl, text)
    return text


def _is_false_positive_name(phrase: str) -> bool:
    lowered = phrase.lower().strip()
    if lowered in _STOP_PHRASES:
        return True
    for word in re.findall(r"[a-z']+", lowered):
        if word in _FALSE_POSITIVE_NAME_WORDS:
            return True
    return False


def _redact_names(
    text: str,
    tracker: PIITracker,
    ctx: str,
    config: NameDetectionConfig = _NAME_DETECTION_CONFIG,
) -> str:
    """Pass 4: Detect person names and locations with spaCy + EntityRuler."""
    nlp = nlp_engine.load_nlp_pipeline()
    entities = nlp_engine.detect_names_and_locations(text, nlp)

    for ent in sorted(entities, key=lambda item: item["start"], reverse=True):
        if _is_inside_placeholder(text, ent["start"]):
            continue
        category = _NLP_LABEL_CATEGORY_MAP.get(ent["label"])
        if ent["label"] == "NORP":
            category = config.norp_category
        if not category:
            continue
        placeholder = tracker.placeholder(category, ent["text"], ctx)
        text = text[: ent["start"]] + placeholder + text[ent["end"] :]

    return text


def _redact_locations(text: str, tracker: PIITracker, ctx: str) -> str:
    """No-op. Locations are handled in _redact_names via NLP."""
    _ = tracker
    _ = ctx
    return text


QA_AUTO_REDACT_THRESHOLD = 0.8
QA_REVIEW_HIGHLIGHT_COLOR = "RED"
_STREET_CUE = (
    r"(?:Street|St\.?|Road|Rd\.?|Avenue|Ave\.?|Boulevard|Blvd\.?|Lane|Ln\.?|"
    r"Drive|Dr\.?|Court|Ct\.?|Way|Place|Terrace|Nagar|Marg|Layout|Colony|Salai)"
)
QA_ADDRESS_WITH_POSTAL_PATTERN = re.compile(
    r"\b[\w][\w\s,./\-'()&:;]{4,120}\b"
    + _STREET_CUE
    + r"\b[\w\s,./\-'()&:;]{0,40}\b(?:[1-9]\d{2}\s?\d{3}|[1-9][xX*]{5})\b",
    re.IGNORECASE,
)
QA_ADDRESS_CUE_PATTERN = re.compile(
    r"\b(?:No\.?\s*\d+[\w/\-]*,\s*)?[A-Za-z0-9][\w\s,./\-'()&:;]{2,80}\b"
    + _STREET_CUE
    + r"\b",
    re.IGNORECASE,
)
QA_ENTITY_CUE_PATTERN = re.compile(
    r"\b([A-Z][\w&.-]*(?:\s+[A-Z][\w&.-]*){0,6}\s+(?:Private\s+Limited|Pvt\.?\s*Ltd\.?|"
    r"Limited|Ltd\.?|LLP|LLC|Inc\.?|Corporation|Corp\.?|Trust|Foundation|Associates|Group|Bank))\b",
)
QA_INDIVIDUAL_CUE_PATTERN = re.compile(
    r"\b(?:Mr|Mrs|Ms|Dr|Prof|Shri|Smt|Sri)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b",
)


def _run_final_qa(text: str, tracker: PIITracker, context: str) -> str:
    """Final QA pass to detect suspicious residual PII after redaction transforms."""
    detections: list[dict] = []
    nlp = nlp_engine.load_nlp_pipeline()

    for ent in nlp_engine.detect_names_and_locations(text, nlp):
        label = ent["label"]
        if label == "PERSON":
            signal_type = "INDIVIDUAL"
            confidence = 0.74
        elif label == "ORG":
            signal_type = "ENTITY"
            confidence = 0.72
        elif label in {"GPE", "LOC"}:
            signal_type = "ADDRESS"
            confidence = 0.6
        else:
            continue
        detections.append(
            {
                "start": ent["start"],
                "end": ent["end"],
                "span": ent["text"],
                "type": signal_type,
                "confidence": confidence,
                "source": "NER",
            }
        )

    for m in QA_ADDRESS_WITH_POSTAL_PATTERN.finditer(text):
        detections.append(
            {
                "start": m.start(),
                "end": m.end(),
                "span": m.group().strip(),
                "type": "ADDRESS",
                "confidence": 0.9,
                "source": "FUZZY_ADDRESS",
            }
        )
    for m in QA_ADDRESS_CUE_PATTERN.finditer(text):
        detections.append(
            {
                "start": m.start(),
                "end": m.end(),
                "span": m.group().strip(),
                "type": "ADDRESS",
                "confidence": 0.67,
                "source": "FUZZY_ADDRESS",
            }
        )
    for m in QA_ENTITY_CUE_PATTERN.finditer(text):
        detections.append(
            {
                "start": m.start(1),
                "end": m.end(1),
                "span": m.group(1).strip(),
                "type": "ENTITY",
                "confidence": 0.9,
                "source": "FUZZY_ENTITY",
            }
        )
    for m in QA_INDIVIDUAL_CUE_PATTERN.finditer(text):
        detections.append(
            {
                "start": m.start(1),
                "end": m.end(1),
                "span": m.group(1).strip(),
                "type": "INDIVIDUAL",
                "confidence": 0.82,
                "source": "FUZZY_INDIVIDUAL",
            }
        )

    filtered: list[dict] = []
    for det in sorted(detections, key=lambda item: (-item["confidence"], item["start"], -(item["end"] - item["start"]))):
        span = det["span"].strip()
        if (
            not span
            or "[REDACTED_" in span
            or is_placeholder_internal_text(span)
            or _is_inside_placeholder(text, det["start"])
        ):
            continue
        if len(span) <= 2:
            continue
        if any(not (det["end"] <= existing["start"] or det["start"] >= existing["end"]) for existing in filtered):
            continue
        filtered.append(det)

    for det in sorted(filtered, key=lambda item: item["start"], reverse=True):
        confidence = round(det["confidence"], 2)
        signal = {
            "type": det["type"],
            "span": det["span"],
            "confidence": confidence,
            "source": det["source"],
            "location": context,
            "severity": "HIGH" if det["confidence"] >= QA_AUTO_REDACT_THRESHOLD else "REVIEW",
            "highlight": QA_REVIEW_HIGHLIGHT_COLOR,
        }
        if det["confidence"] >= QA_AUTO_REDACT_THRESHOLD:
            placeholder = tracker.placeholder(det["type"], det["span"], context)
            text = text[: det["start"]] + placeholder + text[det["end"] :]
            signal["action"] = "AUTO_REDACTED"
            signal["placeholder"] = placeholder
        else:
            signal["action"] = "MANUAL_REVIEW"
            tracker.audit_log.append(
                {
                    "category": "POTENTIAL_LEAK",
                    "placeholder": f"{det['type']} ({signal['confidence']}) {det['span']}",
                    "location": context,
                    "original_text": det["span"],
                    "severity": "REVIEW",
                    "highlight": QA_REVIEW_HIGHLIGHT_COLOR,
                }
            )
        tracker.qa_signals.append(signal)

    return text


# ────────────────────────────────────────────────────────────
# Main entry point
# ────────────────────────────────────────────────────────────

def redact_text(
    text: str,
    tracker: PIITracker,
    context: str = "",
    name_config: NameDetectionConfig = _NAME_DETECTION_CONFIG,
) -> str:
    """Apply all redaction passes in priority order."""
    if not text or not text.strip():
        return text

    always_redact, never_redact = rule_library.get_term_sets()

    text, protection_map = nlp_engine.protect_never_redact_terms(text, never_redact)
    text = _redact_pre_address_ids(text, tracker, context)
    text = _redact_addresses(text, tracker, context)
    text = _redact_entities(text, tracker, context)
    text = _redact_defined_terms(text, tracker, context)
    text = _redact_post_address_ids(text, tracker, context)
    text = _redact_names(text, tracker, context, name_config)
    text = nlp_engine.run_second_pass(text, tracker, nlp_engine.LEGAL_NLP, nlp_engine.INDIC_PIPELINE, context)
    text = nlp_engine.apply_user_always_redact(text, always_redact, tracker, context)
    text = _run_final_qa(text, tracker, context)
    text = nlp_engine.unprotect_never_redact_terms(text, protection_map)

    return text
