"""Load and merge external Indian name datasets."""

from __future__ import annotations

from pathlib import Path
import csv

from indian_pii_data import INDIAN_FIRST_NAMES, INDIAN_SURNAMES

DATA_DIR = Path(__file__).parent

STOPLIST = {
    "The", "And", "For", "New", "Old", "East", "West", "North", "South", "Center",
    "City", "State", "Name", "India", "Other", "Unknown", "Test",
}


def _read_name_column(csv_path: Path) -> set[str]:
    names: set[str] = set()
    if not csv_path.exists():
        return names

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue
            raw = row[0].strip().strip('"').strip("'")
            if not raw:
                continue
            name = raw.title()
            if len(name) < 3:
                continue
            if name in STOPLIST:
                continue
            names.add(name)
    return names


def load_all_indian_names() -> tuple[set[str], set[str]]:
    # Neutral names are included in first-name patterns to reduce missed detections
    # for names that are commonly used across genders.
    first_names_merged = _read_name_column(DATA_DIR / "indian_first_names_merged.csv")
    neutral = _read_name_column(DATA_DIR / "indian_neutral_names.csv")
    surnames = _read_name_column(DATA_DIR / "indian_surnames_merged.csv")
    first_names = first_names_merged | neutral
    return first_names, surnames


def merge_with_existing(new_firsts: set[str], new_surnames: set[str]) -> tuple[set[str], set[str]]:
    return set(INDIAN_FIRST_NAMES) | set(new_firsts), set(INDIAN_SURNAMES) | set(new_surnames)
