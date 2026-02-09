# Indian name sources

## Selected dataset
We use **Wikidata** as the primary, license-compatible source for Indian given names and family names. Wikidata is released under **CC0 1.0**, which permits reuse and redistribution with attribution. The intended data pull is a SPARQL export of:

- `instance of (P31) = given name (Q202444)` with `country of origin (P495) = India (Q668)`
- `instance of (P31) = family name (Q101352)` with `country of origin (P495) = India (Q668)`

Wikidata licensing: https://www.wikidata.org/wiki/Wikidata:Licensing

## Raw files
- `wikidata_indian_given_names.csv` — snapshot of the given-name list
- `wikidata_indian_family_names.csv` — snapshot of the family-name list

> **Note:** Network access is restricted in this environment, so the current CSVs are seeded from the legacy in-repo name lists until the next online refresh. Run `python scripts/build_indian_name_lists.py` after replacing the CSVs with a fresh Wikidata export.

## SPARQL queries

### Given names
```sparql
SELECT DISTINCT ?name WHERE {
  ?item wdt:P31 wd:Q202444;
        wdt:P495 wd:Q668;
        rdfs:label ?name .
  FILTER (LANG(?name) = "en")
}
ORDER BY ?name
```

### Family names
```sparql
SELECT DISTINCT ?name WHERE {
  ?item wdt:P31 wd:Q101352;
        wdt:P495 wd:Q668;
        rdfs:label ?name .
  FILTER (LANG(?name) = "en")
}
ORDER BY ?name
```
