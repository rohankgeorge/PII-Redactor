from __future__ import annotations

from name_data.load_names import merge_with_existing
from name_data.name_normalization import is_valid_name_token, normalize_name_token


def test_normalize_name_token_preserves_valid_punctuation() -> None:
    assert normalize_name_token("  \"D'Souza\" ") == "D'Souza"
    assert normalize_name_token("Anne-Marie") == "Anne-Marie"


def test_normalize_name_token_drops_noise() -> None:
    assert normalize_name_token("***first_name***") == "first-name"
    assert normalize_name_token("12R@hul!!") == "Rhul"


def test_is_valid_name_token_filters_headers_and_bad_lengths() -> None:
    assert not is_valid_name_token("name")
    assert not is_valid_name_token("n")
    assert not is_valid_name_token("a" * 50)
    assert is_valid_name_token("Rahul")


def test_merge_with_existing_keeps_legacy_sets() -> None:
    merged_firsts, merged_surnames = merge_with_existing({"Aarush"}, {"Kulkarni"})
    assert "Aarush" in merged_firsts
    assert "Kulkarni" in merged_surnames
