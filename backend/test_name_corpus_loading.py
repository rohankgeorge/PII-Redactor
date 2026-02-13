"""Tests for merged name-corpus loading and ruler pattern population."""

from pathlib import Path

import pytest

from name_data import load_names


def _write_csv(path: Path, values: list[str]) -> None:
    path.write_text("\n".join(values) + "\n", encoding="utf-8")


def test_load_all_indian_names_prefers_merged_files_when_present(tmp_path, monkeypatch):
    _write_csv(tmp_path / "indian_first_names_merged.csv", ["Mergedfirst"])
    _write_csv(tmp_path / "indian_surnames_merged.csv", ["Mergedsurname"])
    _write_csv(tmp_path / "indian_neutral_names.csv", ["Neutralname"])

    # Legacy files are intentionally populated but should not affect merged loading.
    _write_csv(tmp_path / "indian_male_names.csv", ["Legacyfirst"])
    _write_csv(tmp_path / "indian_surnames.csv", ["Legacysurname"])

    monkeypatch.setattr(load_names, "DATA_DIR", tmp_path)

    first_names, surnames = load_names.load_all_indian_names()

    assert "Mergedfirst" in first_names
    assert "Neutralname" in first_names
    assert "Legacyfirst" not in first_names
    assert "Mergedsurname" in surnames
    assert "Legacysurname" not in surnames


def test_load_nlp_pipeline_adds_person_patterns_from_merged_data(tmp_path, monkeypatch):
    spacy = pytest.importorskip("spacy")
    import nlp_engine

    _write_csv(tmp_path / "indian_first_names_merged.csv", ["Sentinelfirst"])
    _write_csv(tmp_path / "indian_surnames_merged.csv", ["Sentinelsurname"])
    _write_csv(tmp_path / "indian_neutral_names.csv", ["Sentinelneutral"])

    monkeypatch.setattr(load_names, "DATA_DIR", tmp_path)

    def _mock_spacy_load(_model_name: str):
        nlp = spacy.blank("en")
        nlp.add_pipe("ner")
        return nlp

    monkeypatch.setattr(nlp_engine.spacy, "load", _mock_spacy_load)
    nlp_engine.NLP = None

    nlp = nlp_engine.load_nlp_pipeline()

    ruler_name = "span_ruler" if "span_ruler" in nlp.pipe_names else "entity_ruler"
    ruler = nlp.get_pipe(ruler_name)
    person_patterns = [p for p in ruler.patterns if p.get("label") == "PERSON"]

    assert len(person_patterns) > 0
    assert any(p.get("pattern") == "Sentinelfirst" for p in person_patterns)
    assert any(p.get("pattern") == "Sentinelsurname" for p in person_patterns)
