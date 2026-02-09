# RedactAI - Indian PII Redaction Tool

## Architecture
- Frontend: React + Tailwind + Shadcn/UI (dark theme)
- Backend: FastAPI + python-docx + antiword + pii_engine.py (multi-pass)
- Database: MongoDB (template, no PII storage)

## What's Been Implemented

### Phase 1-3: See previous iterations

### Phase 4: GitHub Repo Integration (Feb 8, 2026)
Pulled from rohankgeorge/PII-Redactor. Key changes:
- **RedactionConfig class**: Configurable passes (entities, addresses, IDs, names, locations, contextual cues, consecutive caps)
- **global_pii_data.py**: Expanded global name/location datasets (non-Indian names, US/UK postcodes)
- **generated_indian_names.py**: Auto-generated massive Indian name lists
- **data/stop_phrases.json**: 700+ legal stop phrases to avoid false positives
- **Defined terms detection**: Tracks "Company", "First Party" etc. as defined terms
- **Contextual cue names**: "Party:", "Witness:", "Authorized Signatory:" → name detection
- **Entity alias tracking**: Short names from entity matches tracked as aliases
- **_is_false_positive_name()**: Checks against stop phrases + single-word filters
- **Fixed CONTEXTUAL_CUE_PATTERN**: Was referenced but undefined in repo (bug fixed)

## Backlog
- P1: Entity aliasing across suffixes (NeoSan Private Limited = NeoSan Pvt Ltd → same number)
- P2: Redacted text preview before download
- P2: Custom PII category toggle
