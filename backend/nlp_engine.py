"""NLP utilities for name/location detection and optional second-pass NER models."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Optional

import spacy

from indian_pii_data import (
    INDIAN_CITIES,
    INDIAN_FIRST_NAMES,
    INDIAN_STATES,
    INDIAN_SURNAMES,
)

MODEL_NAME = "en_core_web_sm"
LEGAL_MODEL_WHL = (
    "https://huggingface.co/opennyaiorg/en_legal_ner_trf/resolve/main/"
    "en_legal_ner_trf-any-py3-none-any.whl"
)
_PLACEHOLDER_PATTERN = re.compile(r"\[REDACTED_[A-Z_]+\d+\]")

NLP = None
LEGAL_NLP = None
INDIC_PIPELINE = None


def _is_inside_placeholder(text: str, start: int) -> bool:
    for m in _PLACEHOLDER_PATTERN.finditer(text):
        if m.start() <= start < m.end():
            return True
    return False


def _build_person_patterns(first_names: set[str], surnames: set[str]) -> list[dict]:
    patterns = []
    for name in sorted(first_names | surnames):
        cleaned = name.strip()
        if cleaned:
            patterns.append({"label": "PERSON", "pattern": cleaned})
    return patterns


def _build_location_patterns() -> list[dict]:
    patterns = []
    for loc in sorted(INDIAN_CITIES):
        if loc.strip():
            patterns.append({"label": "GPE", "pattern": loc.strip()})
    for loc in sorted(INDIAN_STATES):
        if loc.strip():
            patterns.append({"label": "LOC", "pattern": loc.strip()})
    return patterns


def load_nlp_pipeline():
    """Load spaCy model and configure a ruler with Indian name/location dictionaries."""
    global NLP
    if NLP is not None:
        return NLP

    nlp = spacy.load(MODEL_NAME)
    major, minor = (int(x) for x in spacy.__version__.split(".")[:2])
    use_span_ruler = (major, minor) >= (3, 3)

    if use_span_ruler and "span_ruler" not in nlp.pipe_names:
        ruler = nlp.add_pipe("span_ruler", before="ner")
    elif not use_span_ruler and "entity_ruler" not in nlp.pipe_names:
        ruler = nlp.add_pipe("entity_ruler", before="ner")
    else:
        ruler = nlp.get_pipe("span_ruler" if use_span_ruler else "entity_ruler")

    from name_data.load_names import load_all_indian_names, merge_with_existing

    new_firsts, new_surnames = load_all_indian_names()
    merged_firsts, merged_surnames = merge_with_existing(new_firsts, new_surnames)

    patterns = []
    patterns.extend(_build_person_patterns(merged_firsts, merged_surnames))
    patterns.extend(_build_location_patterns())
    ruler.add_patterns(patterns)

    print(
        f"EntityRuler loaded with {len(merged_firsts)} first name patterns "
        f"and {len(merged_surnames)} surname patterns."
    )

    NLP = nlp
    return NLP


def load_legal_ner():
    """Load optional OpenNyAI legal NER model."""
    global LEGAL_NLP
    if LEGAL_NLP is not None:
        return LEGAL_NLP

    try:
        LEGAL_NLP = spacy.load("en_legal_ner_trf")
    except Exception:
        print(
            "OpenNyAI Legal NER not installed — skipping. "
            f"Install with: pip install {LEGAL_MODEL_WHL}"
        )
        LEGAL_NLP = None
    return LEGAL_NLP


def load_indic_ner() -> Optional[Any]:
    """Load optional IndicNER transformer pipeline."""
    global INDIC_PIPELINE
    if INDIC_PIPELINE is not None:
        return INDIC_PIPELINE

    try:
        from transformers import pipeline

        INDIC_PIPELINE = pipeline("ner", model="ai4bharat/IndicNER")
    except Exception:
        print(
            "IndicNER not installed — skipping. Install with: "
            "pip install transformers torch"
        )
        INDIC_PIPELINE = None
    return INDIC_PIPELINE


def initialize_models():
    """Load all NLP models once at startup."""
    load_nlp_pipeline()
    load_legal_ner()
    load_indic_ner()


def detect_names_and_locations(text: str, nlp) -> list[dict]:
    doc = nlp(text)
    allowed = {"PERSON", "ORG", "GPE", "LOC", "NORP"}
    entities = []
    for ent in doc.ents:
        if ent.label_ in allowed:
            entities.append(
                {"start": ent.start_char, "end": ent.end_char, "text": ent.text, "label": ent.label_}
            )
    return entities


def load_user_list(filepath: str) -> set[str]:
    items: set[str] = set()
    path = Path(filepath)
    if not path.exists():
        return items

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            value = line.strip()
            if value and not value.startswith("#"):
                items.add(value)
    return items


def apply_user_always_redact(text: str, always_redact: set[str], tracker, context: str) -> str:
    for term in sorted(always_redact, key=len, reverse=True):
        if not term.strip():
            continue
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        matches = [m for m in pattern.finditer(text) if not _is_inside_placeholder(text, m.start())]
        for m in reversed(matches):
            placeholder = tracker.placeholder("INDIVIDUAL", m.group(), context)
            text = text[: m.start()] + placeholder + text[m.end() :]
    return text


def protect_never_redact_terms(text: str, never_redact: set[str]) -> tuple[str, dict]:
    protection_map: dict[str, str] = {}
    marker_index = 0
    for term in sorted(never_redact, key=len, reverse=True):
        if not term.strip():
            continue
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        matches = [m for m in pattern.finditer(text) if not _is_inside_placeholder(text, m.start())]
        for m in reversed(matches):
            marker = f"__PROTECTED_TERM_{marker_index}__"
            marker_index += 1
            protection_map[marker] = m.group()
            text = text[: m.start()] + marker + text[m.end() :]
    return text, protection_map


def unprotect_never_redact_terms(text: str, protection_map: dict) -> str:
    for marker, original in protection_map.items():
        text = text.replace(marker, original)
    return text


def apply_user_never_redact(text: str, never_redact: set[str]) -> str:
    protected_text, protection_map = protect_never_redact_terms(text, never_redact)
    return unprotect_never_redact_terms(protected_text, protection_map)


def detect_with_legal_ner(text: str, legal_nlp) -> list[dict]:
    if legal_nlp is None:
        return []

    mapping = {
        "PETITIONER": "INDIVIDUAL",
        "RESPONDENT": "INDIVIDUAL",
        "JUDGE": "INDIVIDUAL",
        "LAWYER": "INDIVIDUAL",
        "WITNESS": "INDIVIDUAL",
        "OTHER_PERSON": "INDIVIDUAL",
        "COURT": "ENTITY",
        "GPE": "LOCATION",
    }
    entities = []
    doc = legal_nlp(text)
    for ent in doc.ents:
        category = mapping.get(ent.label_)
        if category:
            entities.append(
                {
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "text": ent.text,
                    "label": ent.label_,
                    "category": category,
                }
            )
    return entities


def detect_with_indic_ner(text: str, indic_pipeline) -> list[dict]:
    if indic_pipeline is None:
        return []

    mapping = {"PER": "INDIVIDUAL", "LOC": "LOCATION", "ORG": "ENTITY"}
    entities = []
    raw = indic_pipeline(text)
    for ent in raw:
        label = ent.get("entity_group") or ent.get("entity", "")
        label = label.replace("B-", "").replace("I-", "")
        category = mapping.get(label)
        if not category:
            continue
        start = int(ent.get("start", 0))
        end = int(ent.get("end", start))
        entities.append(
            {
                "start": start,
                "end": end,
                "text": text[start:end],
                "label": label,
                "category": category,
            }
        )
    return entities


def run_second_pass(text: str, tracker, legal_nlp, indic_pipeline, context: str) -> str:
    detections = []
    detections.extend(detect_with_legal_ner(text, legal_nlp))
    detections.extend(detect_with_indic_ner(text, indic_pipeline))

    for ent in sorted(detections, key=lambda item: item["start"], reverse=True):
        if _is_inside_placeholder(text, ent["start"]):
            continue
        placeholder = tracker.placeholder(ent["category"], ent["text"], context)
        text = text[: ent["start"]] + placeholder + text[ent["end"] :]
    return text
