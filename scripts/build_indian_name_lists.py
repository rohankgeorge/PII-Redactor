"""Build clean Indian name artifacts from source CSV datasets.

This script performs source-aware parsing and emits clean, one-name-per-row CSV
artifacts consumed by ``backend/name_data/load_names.py``.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from backend.name_data.name_normalization import is_valid_name_token, normalize_name_token

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data" / "raw_names"
OUTPUT_DIR = REPO_ROOT / "backend" / "name_data"


@dataclass(frozen=True)
class SourceSpec:
    filename: str
    output_filename: str
    fieldnames: tuple[str, ...]


SOURCE_SPECS = (
    SourceSpec("male_names.csv", "indian_male_names.csv", ("name", "first_name", "male_name")),
    SourceSpec("female_names.csv", "indian_female_names.csv", ("name", "first_name", "female_name")),
    SourceSpec("surnames.csv", "indian_surnames.csv", ("surname", "last_name", "family_name", "name")),
)


def _iter_source_tokens(csv_path: Path, fieldnames: tuple[str, ...]) -> Iterable[str]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        sample = handle.read(2048)
        handle.seek(0)

        try:
            dialect = csv.Sniffer().sniff(sample) if sample else csv.excel
        except csv.Error:
            dialect = csv.excel

        has_header = False
        if sample:
            try:
                has_header = csv.Sniffer().has_header(sample)
            except csv.Error:
                has_header = False

        if has_header:
            reader = csv.DictReader(handle, dialect=dialect)
            normalized_keys = {key.lower().strip(): key for key in (reader.fieldnames or [])}
            matching_keys = [normalized_keys[key] for key in fieldnames if key in normalized_keys]
            if not matching_keys:
                matching_keys = [reader.fieldnames[0]] if reader.fieldnames else []
            for row in reader:
                for key in matching_keys:
                    value = row.get(key)
                    if value:
                        yield value
        else:
            reader = csv.reader(handle, dialect=dialect)
            for row in reader:
                if not row:
                    continue
                yield row[0]


def _build_artifact_for_spec(spec: SourceSpec) -> None:
    source_path = RAW_DIR / spec.filename
    output_path = OUTPUT_DIR / spec.output_filename

    if not source_path.exists():
        print(f"[skip] Missing source: {source_path}")
        return

    cleaned_names = {
        token
        for raw in _iter_source_tokens(source_path, spec.fieldnames)
        if is_valid_name_token(token := normalize_name_token(raw))
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        for token in sorted(cleaned_names):
            writer.writerow([token])

    print(f"[ok] Wrote {len(cleaned_names)} names -> {output_path}")


def main() -> None:
    for spec in SOURCE_SPECS:
        _build_artifact_for_spec(spec)


if __name__ == "__main__":
    main()
