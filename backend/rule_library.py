"""Local persisted rule library for always/never redaction terms.

This module is intentionally offline-first and file-backed so the tool can run
as a standalone local application.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import threading
import uuid

MODE_ALLOW = "ALLOW"
MODE_FORCE = "FORCE"
VALID_MODES = {MODE_ALLOW, MODE_FORCE}


@dataclass
class RuleEntry:
    id: str
    term: str
    mode: str
    enabled: bool
    created_at: str
    updated_at: str


_LOCK = threading.RLock()
_RULES: list[RuleEntry] = []
_RULES_FILE: Path | None = None
_ALLOW_TXT_FILE: Path | None = None
_FORCE_TXT_FILE: Path | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_term(term: str) -> str:
    return " ".join((term or "").strip().split())


def _normalized_key(term: str) -> str:
    return normalize_term(term).casefold()


def _serialize_rules() -> dict:
    return {"rules": [asdict(rule) for rule in _RULES]}


def _write_json_file(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _load_txt_terms(path: Path) -> set[str]:
    if not path.exists():
        return set()
    terms: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            value = normalize_term(line)
            if value and not value.startswith("#"):
                terms.add(value)
    return terms


def _sync_txt_files():
    if _ALLOW_TXT_FILE is not None:
        allow_terms = sorted({rule.term for rule in _RULES if rule.mode == MODE_ALLOW and rule.enabled})
        _ALLOW_TXT_FILE.write_text("\n".join(allow_terms) + ("\n" if allow_terms else ""), encoding="utf-8")
    if _FORCE_TXT_FILE is not None:
        force_terms = sorted({rule.term for rule in _RULES if rule.mode == MODE_FORCE and rule.enabled})
        _FORCE_TXT_FILE.write_text("\n".join(force_terms) + ("\n" if force_terms else ""), encoding="utf-8")


def _persist_locked():
    if _RULES_FILE is None:
        return
    _write_json_file(_RULES_FILE, _serialize_rules())
    _sync_txt_files()


def initialize(base_dir: Path | str):
    """Initialize library from JSON store; bootstrap from legacy txt files once."""
    global _RULES_FILE, _ALLOW_TXT_FILE, _FORCE_TXT_FILE, _RULES

    root = Path(base_dir)
    rules_path = root / "rules_library.json"
    allow_path = root / "user_allow_list.txt"
    force_path = root / "user_redact_list.txt"

    with _LOCK:
        _RULES_FILE = rules_path
        _ALLOW_TXT_FILE = allow_path
        _FORCE_TXT_FILE = force_path

        loaded: list[RuleEntry] = []
        if rules_path.exists():
            try:
                payload = json.loads(rules_path.read_text(encoding="utf-8"))
                for item in payload.get("rules", []):
                    mode = str(item.get("mode", "")).upper()
                    term = normalize_term(str(item.get("term", "")))
                    if not term or mode not in VALID_MODES:
                        continue
                    loaded.append(
                        RuleEntry(
                            id=str(item.get("id") or uuid.uuid4().hex),
                            term=term,
                            mode=mode,
                            enabled=bool(item.get("enabled", True)),
                            created_at=str(item.get("created_at") or _now_iso()),
                            updated_at=str(item.get("updated_at") or _now_iso()),
                        )
                    )
            except Exception:
                loaded = []

        if not loaded:
            now = _now_iso()
            allow_terms = _load_txt_terms(allow_path)
            force_terms = _load_txt_terms(force_path)
            merged: list[RuleEntry] = []
            for term in sorted(allow_terms):
                merged.append(RuleEntry(id=uuid.uuid4().hex, term=term, mode=MODE_ALLOW, enabled=True, created_at=now, updated_at=now))
            for term in sorted(force_terms):
                merged.append(RuleEntry(id=uuid.uuid4().hex, term=term, mode=MODE_FORCE, enabled=True, created_at=now, updated_at=now))
            loaded = merged

        _RULES = loaded
        _persist_locked()


def list_rules() -> list[dict]:
    with _LOCK:
        return [asdict(rule) for rule in _RULES]


def _find_rule_index(rule_id: str) -> int:
    for idx, rule in enumerate(_RULES):
        if rule.id == rule_id:
            return idx
    return -1


def create_rule(term: str, mode: str, enabled: bool = True) -> dict:
    clean_term = normalize_term(term)
    clean_mode = (mode or "").upper().strip()
    if not clean_term:
        raise ValueError("term must be a non-empty string")
    if clean_mode not in VALID_MODES:
        raise ValueError("mode must be one of: ALLOW, FORCE")

    with _LOCK:
        key = _normalized_key(clean_term)
        for existing in _RULES:
            if _normalized_key(existing.term) == key and existing.mode == clean_mode:
                raise ValueError("rule already exists for this term and mode")

        now = _now_iso()
        entry = RuleEntry(
            id=uuid.uuid4().hex,
            term=clean_term,
            mode=clean_mode,
            enabled=bool(enabled),
            created_at=now,
            updated_at=now,
        )
        _RULES.append(entry)
        _persist_locked()
        return asdict(entry)


def update_rule(rule_id: str, term: str | None = None, mode: str | None = None, enabled: bool | None = None) -> dict:
    with _LOCK:
        idx = _find_rule_index(rule_id)
        if idx < 0:
            raise KeyError("rule not found")

        current = _RULES[idx]
        new_term = normalize_term(term) if term is not None else current.term
        new_mode = (mode or current.mode).upper().strip() if mode is not None else current.mode
        new_enabled = bool(enabled) if enabled is not None else current.enabled

        if not new_term:
            raise ValueError("term must be a non-empty string")
        if new_mode not in VALID_MODES:
            raise ValueError("mode must be one of: ALLOW, FORCE")

        key = _normalized_key(new_term)
        for existing in _RULES:
            if existing.id == rule_id:
                continue
            if _normalized_key(existing.term) == key and existing.mode == new_mode:
                raise ValueError("rule already exists for this term and mode")

        updated = RuleEntry(
            id=current.id,
            term=new_term,
            mode=new_mode,
            enabled=new_enabled,
            created_at=current.created_at,
            updated_at=_now_iso(),
        )
        _RULES[idx] = updated
        _persist_locked()
        return asdict(updated)


def delete_rule(rule_id: str) -> bool:
    with _LOCK:
        idx = _find_rule_index(rule_id)
        if idx < 0:
            return False
        _RULES.pop(idx)
        _persist_locked()
        return True


def get_term_sets() -> tuple[set[str], set[str]]:
    """Return (force_terms, allow_terms) for currently enabled rules.

    When ``initialize()`` has not been called (e.g. in unit tests) the in-memory
    ``_RULES`` list is empty.  As a fallback we read the legacy plain-text files
    so that terms written directly to ``user_allow_list.txt`` /
    ``user_redact_list.txt`` are still honoured.
    """
    with _LOCK:
        force = {rule.term for rule in _RULES if rule.enabled and rule.mode == MODE_FORCE}
        allow = {rule.term for rule in _RULES if rule.enabled and rule.mode == MODE_ALLOW}

        # Fallback: merge terms from legacy txt files when _RULES is empty
        if not _RULES:
            allow_path = _ALLOW_TXT_FILE or Path(__file__).parent / "user_allow_list.txt"
            force_path = _FORCE_TXT_FILE or Path(__file__).parent / "user_redact_list.txt"
            allow |= _load_txt_terms(allow_path)
            force |= _load_txt_terms(force_path)

        return force, allow
