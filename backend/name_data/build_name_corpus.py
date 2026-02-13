"""Build deterministic local Indian name artifacts from upstream public datasets."""

from __future__ import annotations

import csv
import io
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable

DATA_DIR = Path(__file__).resolve().parent

GIST_URL = "https://api.github.com/gists/7f86ca901fe41bc14a63"
SURNAMES_REPO_CSV_URL = (
    "https://raw.githubusercontent.com/merishnaSuwal/indian_surnames_data/master/"
    "indian_caste_data.csv"
)
NAMES_REPO_CONTENTS_URL = "https://api.github.com/repos/MASTREX/List-of-Indian-Names/contents"

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

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1  # seconds
MAX_RETRY_DELAY = 60  # seconds


def fetch_text(url: str) -> str:
    """Fetch text from URL with retry logic for network failures and rate limits."""
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return response.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            last_error = e
            # Handle rate limiting (HTTP 429) and server errors (5xx)
            if e.code == 429:
                # Rate limited - use retry-after header if available
                retry_after = e.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = int(retry_after)
                    except ValueError:
                        delay = INITIAL_RETRY_DELAY * (2 ** attempt)
                else:
                    delay = INITIAL_RETRY_DELAY * (2 ** attempt)
                delay = min(delay, MAX_RETRY_DELAY)
                print(f"Rate limited (attempt {attempt + 1}/{MAX_RETRIES}). "
                      f"Retrying in {delay}s...")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(delay)
            elif 500 <= e.code < 600:
                # Server error - retry with exponential backoff
                delay = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                print(f"Server error {e.code} (attempt {attempt + 1}/{MAX_RETRIES}). "
                      f"Retrying in {delay}s...")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(delay)
            else:
                # Client error (4xx) - don't retry
                raise RuntimeError(f"HTTP error {e.code} fetching {url}: {e.reason}") from e
        except urllib.error.URLError as e:
            last_error = e
            # Network error - retry with exponential backoff
            delay = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
            print(f"Network error (attempt {attempt + 1}/{MAX_RETRIES}): {e.reason}. "
                  f"Retrying in {delay}s...")
            if attempt < MAX_RETRIES - 1:
                time.sleep(delay)
    
    # All retries exhausted
    raise RuntimeError(
        f"Failed to fetch {url} after {MAX_RETRIES} attempts: {last_error}"
    ) from last_error


def fetch_json(url: str) -> dict:
    """Fetch and parse JSON from URL with error handling."""
    try:
        text = fetch_text(url)
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON response from {url}: {e}") from e


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
    if " " not in cleaned and len(cleaned) <= 1:
        return None
    return cleaned.title()


def parse_mbejda_gist() -> tuple[set[str], set[str], set[str]]:
    payload = fetch_json(GIST_URL)
    raw_url = payload["files"]["Indian-Male-Names.csv"]["raw_url"]
    content = fetch_text(raw_url)

    first_names: set[str] = set()
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        candidate = normalize_candidate(row.get("name", ""))
        if candidate:
            first_names.add(candidate)
    return first_names, set(), set()


def parse_indian_surnames_repo() -> tuple[set[str], set[str], set[str]]:
    content = fetch_text(SURNAMES_REPO_CSV_URL)
    reader = csv.DictReader(io.StringIO(content))

    surnames: set[str] = set()
    for row in reader:
        candidate = normalize_candidate(row.get("caste", ""))
        if candidate:
            surnames.add(candidate)
    return set(), surnames, set()


def parse_mastrex_names_repo() -> tuple[set[str], set[str], set[str]]:
    contents = fetch_json(NAMES_REPO_CONTENTS_URL)

    first_names: set[str] = set()
    surnames: set[str] = set()
    neutral: set[str] = set()

    for item in contents:
        if item.get("type") != "file" or not item.get("name", "").lower().endswith(".txt"):
            continue

        file_name = item["name"]
        file_text = fetch_text(item["download_url"])
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

    print("Building Indian name corpus from upstream sources...\n")
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
