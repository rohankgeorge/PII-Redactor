# Raw Indian name source data (canonical)

These files are the canonical, committed raw inputs used by
`backend/name_data/build_name_corpus.py`.

Policy:
- Keep raw upstream files in this directory under version control.
- Do not fetch network resources during corpus builds.
- If upstream data changes, refresh these raw files in a separate update commit
  and then regenerate derived artifacts.

## Provenance

- `mbejda_indian_male_names.csv`
  - Source: https://gist.github.com/mbejda/7f86ca901fe41bc14a63
- `merishna_indian_caste_data.csv`
  - Source: https://github.com/merishnaSuwal/indian_surnames_data
- `mastrex/*.txt`
  - Source: https://github.com/MASTREX/List-of-Indian-Names
