# Address Fallback False-Positive Mitigation Plan

## Decision
Do **not** roll back the entire India-area expansion yet. Instead, ship a targeted mitigation pass that preserves recall gains while removing the high-confidence false-positive paths reported in review.

## Why this path
- Full rollback would lose support for fragmented, non-PIN Indian addresses that motivated this PR.
- Current regressions are concentrated in a few overly-broad cues (`phase|sector` structure matching and possessive-token artifacts), so precision can be recovered with narrow changes.

## Plan
1. **Narrow structural cue regexes**
   - Restrict `sector|phase` boosts to address-like suffixes only:
     - numeric/alpha-number forms (`Sector-5`, `Phase 2A`)
     - Roman numerals (`Phase II`)
   - Exclude free-form prose continuations (for example `phase wise`, `phase rollout`).

2. **Remove possessive leakage from house-token scoring**
   - Remove single-letter `s` from `_ADDRESS_HOUSE_TOKENS`.
   - Keep explicit house markers (`no`, `flat`, `house`, `plot`, etc.) unchanged.

3. **Add precision-focused regression tests**
   - Narrative sentence with possessive + city should not redact.
   - `phase wise` operational text should not redact.
   - Keep at least one positive case each for `Sector-5` and `Phase II` still redacting when other address cues exist.

4. **Guardrail scoring follow-up (if needed)**
   - If false positives persist, require either:
     - one *hard* address cue (`PIN`, house token, ordinal + street suffix), or
     - two *independent* structural cues before crossing threshold.

5. **Measure before/after impact**
   - Compare:
     - fallback-address precision on a curated non-address narrative set
     - recall on fragmented Indian address fixtures
   - Ship only if precision recovers without materially hurting recall.

## Rollback criteria
Roll back the area-token expansion only if the targeted fixes above cannot bring precision to acceptable levels after one iteration. This keeps rollback as a contingency, not the default response.
