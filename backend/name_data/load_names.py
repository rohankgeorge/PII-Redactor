"""Load and merge already-clean external Indian name artifacts."""

from __future__ import annotations

from pathlib import Path
import csv

from indian_pii_data import INDIAN_FIRST_NAMES, INDIAN_SURNAMES
from name_data.name_normalization import is_valid_name_token, normalize_name_token

DATA_DIR = Path(__file__).parent


def _read_clean_name_artifact(csv_path: Path) -> set[str]:
    names: set[str] = set()
    if not csv_path.exists():
        return names

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue
            # Artifacts are expected to be pre-cleaned single-value rows.
            token = normalize_name_token(row[0])
            if is_valid_name_token(token):
                names.add(token)
    return names


def load_all_indian_names() -> tuple[set[str], set[str]]:
    male = _read_clean_name_artifact(DATA_DIR / "indian_male_names.csv")
    female = _read_clean_name_artifact(DATA_DIR / "indian_female_names.csv")
    surnames = _read_clean_name_artifact(DATA_DIR / "indian_surnames.csv")
    first_names = male | female
    return first_names, surnames


def merge_with_existing(new_firsts: set[str], new_surnames: set[str]) -> tuple[set[str], set[str]]:
    return set(INDIAN_FIRST_NAMES) | set(new_firsts), set(INDIAN_SURNAMES) | set(new_surnames)
