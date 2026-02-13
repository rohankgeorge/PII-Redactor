"""Build deterministic local Indian name artifacts from committed raw datasets."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Iterable

DATA_DIR = Path(__file__).resolve().parent
RAW_DATA_DIR = DATA_DIR.parent.parent / "data" / "raw_names"
MASTREX_DIR = RAW_DATA_DIR / "mastrex"

NOISE_TOKENS = {
    "",
    "na",
    "n/a",
    "none",
    "null",
    "nan",
    "unknown",
    "name",
    "names",
    "first",
    "last",
    "middle",
    "optional",
    "prefix",
    "prefixs",
}

WHITESPACE_RE = re.compile(r"\s+")
VALID_CHARS_RE = re.compile(r"^[A-Za-z .\-'`]+$")
HAS_DIGIT_RE = re.compile(r"\d")
def normalize_candidate(raw_value: str) -> str | None:
    value = WHITESPACE_RE.sub(" ", raw_value.strip())
    if not value:
        return None
    if HAS_DIGIT_RE.search(value):
        return None
    if not VALID_CHARS_RE.match(value):
        return None

    tokens = [token.strip(" .,-").lower() for token in value.split(" ")]
    if not tokens or any(token in NOISE_TOKENS for token in tokens):
        return None

    cleaned = " ".join(part for part in value.split(" ") if part)
    if len(cleaned) < 2:
        return None
    return cleaned.title()


def parse_mbejda_gist() -> tuple[set[str], set[str], set[str]]:
    content = (RAW_DATA_DIR / "mbejda_indian_male_names.csv").read_text(encoding="utf-8")

    first_names: set[str] = set()
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        candidate = normalize_candidate(row.get("name", ""))
        if candidate:
            first_names.add(candidate)
    return first_names, set(), set()


def parse_indian_surnames_repo() -> tuple[set[str], set[str], set[str]]:
    content = (RAW_DATA_DIR / "merishna_indian_caste_data.csv").read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(content))

    surnames: set[str] = set()
    for row in reader:
        candidate = normalize_candidate(row.get("caste", ""))
        if candidate:
            surnames.add(candidate)
    return set(), surnames, set()


def parse_mastrex_names_repo() -> tuple[set[str], set[str], set[str]]:
    first_names: set[str] = set()
    surnames: set[str] = set()
    neutral: set[str] = set()

    for file_path in sorted(MASTREX_DIR.glob("*.txt")):
        file_name = file_path.name
        file_text = file_path.read_text(encoding="utf-8")
        lines = file_text.splitlines()

        target: set[str] | None = None
        lowered = file_name.lower()
        if "first" in lowered:
            target = first_names
        elif "last" in lowered:
            target = surnames
        elif "middle" in lowered:
            target = neutral
        elif "prefix" in lowered:
            target = neutral

        if target is None:
            continue

        for line in lines:
            candidate = normalize_candidate(line)
            if candidate:
                target.add(candidate)

    return first_names, surnames, neutral


def write_csv(path: Path, rows: Iterable[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        for value in sorted(set(rows)):
            writer.writerow([value])


def main() -> None:
    source_parsers = {
        "mbejda_gist": parse_mbejda_gist,
        "merishna_surnames": parse_indian_surnames_repo,
        "mastrex_names": parse_mastrex_names_repo,
    }

    merged_first: set[str] = set()
    merged_surnames: set[str] = set()
    merged_neutral: set[str] = set()

    print(f"Building Indian name corpus from committed raw sources in {RAW_DATA_DIR}...\n")
    for source_name, parser in source_parsers.items():
        first, surnames, neutral = parser()
        merged_first |= first
        merged_surnames |= surnames
        merged_neutral |= neutral
        print(
            f"{source_name}: first={len(first)} surname={len(surnames)} neutral={len(neutral)}"
        )

    write_csv(DATA_DIR / "indian_first_names_merged.csv", merged_first)
    write_csv(DATA_DIR / "indian_surnames_merged.csv", merged_surnames)
    write_csv(DATA_DIR / "indian_neutral_names.csv", merged_neutral)

    print("\nFinal unique counts:")
    print(f"first={len(merged_first)}")
    print(f"surname={len(merged_surnames)}")
    print(f"neutral={len(merged_neutral)}")


if __name__ == "__main__":
    main()
