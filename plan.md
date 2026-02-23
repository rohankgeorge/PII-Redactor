# PII Redactor — Implementation Plan

## Instructions for Claude

Follow this plan milestone by milestone in strict order. For each milestone:
1. Run `/goal-driven` with the milestone's goal and success criteria to frame the work
2. Run `/explore-plan-code` to explore the affected files listed, plan your changes, then implement
3. Within the explore-plan-code flow, run `/test-first` to write failing tests BEFORE writing implementation code
4. After implementation, run `/code-review` on all changed files and fix any issues found
5. Run `cd backend && python -m pytest` to verify no regressions
6. Commit with a descriptive message before moving to the next milestone

Do NOT skip milestones or reorder them. Do NOT mark a milestone complete until all its success criteria pass.

---

## Project Context

This is an existing full-stack web application (React + FastAPI) that detects and redacts PII from legal documents using spaCy NLP models, regex patterns, and an EntityRuler-based Indian name dictionary.

**Repository**: `rohankgeorge/PII-Redactor`
**Backend**: FastAPI on port 8000 — `backend/server.py`, `backend/pii_engine.py`, `backend/nlp_engine.py`
**Frontend**: React + Tailwind + Shadcn/UI on port 3000 — `frontend/src/`
**Tests**: `cd backend && python -m pytest`

### What Already Works
- Multi-pass PII detection engine: regex for structured IDs (Aadhaar, PAN, GST, IFSC, phone, email, UPI, bank account, DL, passport, voter ID, vehicle reg, PIN code, DOB), spaCy NER for names/entities/locations, address detection, entity detection with corporate suffix awareness
- .docx and .pdf file upload and processing
- Review mode: analyze → show candidates → user selects/deselects → apply redaction
- Individual candidate checkbox toggle, select all / clear all
- Rule library with ALLOW (never-redact) and FORCE (always-redact) rules
- Audit CSV export
- Docker Compose setup, Windows startup script

### What Needs to Be Built
1. **Context-preserving smart placeholders** — Current `[REDACTED_CATEGORY_N]` format loses structural context for LLM analysis
2. **Output format selection** — Currently only .docx output; needs .pdf and .md options
3. **Enhanced review pipeline** — Missing: term grouping, category toggles, inline force-redact, custom placeholder editing
4. **Standalone installer** — No installer exists; needs downloadable .exe (Windows) and .dmg (Mac)
5. **Validation against test documents** — User will provide `TYPES OF PII.docx` and `/Test Docs/` folder

---

## Milestone 1: Context-Preserving Smart Placeholders

### Goal
Replace `[REDACTED_CATEGORY_N]` placeholder format with entity-type-aware placeholders that preserve structural context so LLMs can produce better legal analysis from redacted documents.

### Skill Invocations
1. **`/goal-driven`** — Use the goal and success criteria below
2. **`/explore-plan-code`** — Explore the files listed, plan the changes described, then implement
3. **`/test-first`** — Write the tests listed below BEFORE implementation
4. **`/code-review`** — Review all changed files after implementation

### Success Criteria
- [ ] Entity names preserve corporate suffixes: "NeoSan Private Limited" → "X Private Limited", "TechCo LLP" → "Y LLP"
- [ ] Person names use "Person N" format: "Rajesh Sharma" → "Person 1"
- [ ] Person names with titles preserve the title: "Mr. Rajesh Sharma" → "Mr. Person 1", "Dr. Kamala Devi" → "Dr. Person 2"
- [ ] Structured IDs use human-readable format: "2345 6789 0123" → "[Aadhaar 1]", "ABCDE1234F" → "[PAN 1]"
- [ ] Locations use "[Location N]", addresses use "[Address N]"
- [ ] All other PII categories use `[Category N]` with human-readable names (see format table below)
- [ ] Same unique PII value always maps to the same placeholder across the document
- [ ] Audit CSV contains original text, new placeholder, and category for every redacted item
- [ ] All existing pytest tests pass (update assertions to match new format)
- [ ] `is_inside_placeholder()` and `is_placeholder_internal_text()` recognize both old and new formats

### Placeholder Format Specification

| PII Category | New Format | Example |
|---|---|---|
| ENTITY (Private Limited) | `X Private Limited` | "NeoSan Private Limited" → "X Private Limited" |
| ENTITY (LLP, Ltd, Inc, Corp, etc.) | `X LLP`, `Y Ltd`, `Z Inc` | "TechCo LLP" → "X LLP" |
| INDIVIDUAL | `Person N` | "Rajesh Sharma" → "Person 1" |
| INDIVIDUAL (with title) | `Mr. Person N`, `Dr. Person N` | "Mr. Rajesh Sharma" → "Mr. Person 1" |
| LOCATION | `[Location N]` | "Bangalore" → "[Location 1]" |
| ADDRESS | `[Address N]` | "123 MG Road, Bangalore 560001" → "[Address 1]" |
| AADHAAR_NUMBER | `[Aadhaar N]` | "2345 6789 0123" → "[Aadhaar 1]" |
| PAN_NUMBER | `[PAN N]` | "ABCDE1234F" → "[PAN 1]" |
| PHONE_NUMBER | `[Phone N]` | "+91 98765 43210" → "[Phone 1]" |
| EMAIL | `[Email N]` | "test@example.com" → "[Email 1]" |
| BANK_ACCOUNT | `[Bank Account N]` | "1234567890" → "[Bank Account 1]" |
| GST_NUMBER | `[GST N]` | "22AAAAA0000A1Z5" → "[GST 1]" |
| IFSC_CODE | `[IFSC N]` | "SBIN0001234" → "[IFSC 1]" |
| PASSPORT_NUMBER | `[Passport N]` | "A1234567" → "[Passport 1]" |
| VOTER_ID | `[Voter ID N]` | "ABC1234567" → "[Voter ID 1]" |
| DRIVING_LICENSE | `[DL N]` | "KA0120230001234" → "[DL 1]" |
| VEHICLE_REGISTRATION | `[Vehicle Reg N]` | "KA 01 AB 1234" → "[Vehicle Reg 1]" |
| UPI_ID | `[UPI N]` | "user@bank" → "[UPI 1]" |
| DATE_OF_BIRTH | `[DOB N]` | "15/03/1990" → "[DOB 1]" |
| PIN_CODE | `[PIN N]` | "560001" → "[PIN 1]" |

For entities, use letters (X, Y, Z, A, B, C...) instead of numbers. For all other categories, use numbers (1, 2, 3...).

### Files to Explore and Modify

**`backend/pii_engine.py`** — `PIITracker` class:
- Add a `PLACEHOLDER_FORMATS` dict mapping each category to its display format template
- Modify `PIITracker.placeholder()` method to generate the new format instead of `[REDACTED_CATEGORY_N]`
- For ENTITY categories: extract the corporate suffix (Private Limited, LLP, Ltd, Inc, etc.) from the original text and append it to the placeholder variable letter
- For INDIVIDUAL: use "Person N" format; if the original text had a title (Mr., Mrs., Dr., Smt., Shri, etc.), preserve it as a prefix
- For all other categories: use `[Category N]` format with human-readable category names
- The tracker must store both the display placeholder AND the original text in its audit log

**`backend/placeholder_utils.py`**:
- Update `is_inside_placeholder()` and `is_placeholder_internal_text()` to recognize BOTH new format patterns AND old `[REDACTED_...]` pattern for backward compatibility

**`frontend/src/components/ReviewPanel.jsx`**:
- Update Badge display for `candidate.placeholder` to render the new format correctly
- No structural changes needed — placeholders are just strings

### Tests to Write (via /test-first)
- `PIITracker.placeholder()` returns correct format for each PII category
- Entity with "Private Limited" suffix → "X Private Limited" format
- Entity with "LLP" suffix → "X LLP" format
- Person name → "Person N" format
- Person name with title → title is preserved ("Mr. Person 1")
- Same original value → same placeholder every time
- Different original values → different placeholders
- `is_inside_placeholder()` recognizes both old and new formats
- Full pipeline: mixed PII input produces correctly formatted output
- Audit log contains original text and new placeholder for each item

---

## Milestone 2: Output Format Selection (.docx, .pdf, .md)

### Goal
Allow users to select their preferred output format (.docx, .pdf, or .md) when downloading redacted documents.

### Skill Invocations
1. **`/goal-driven`** — Use the goal and success criteria below
2. **`/explore-plan-code`** — Explore, plan, implement
3. **`/test-first`** — Write tests before implementation
4. **`/code-review`** — Review changed files

### Success Criteria
- [ ] `GET /api/download/{file_id}` accepts `output_format` query parameter (values: `docx`, `pdf`, `md`; default: `docx`)
- [ ] .pdf output is generated using `fpdf2` (pure Python, works offline) and is valid/openable in any PDF reader
- [ ] .md output preserves document structure (headings, paragraphs) in proper markdown syntax
- [ ] Frontend shows a format selector (dropdown or radio group) before the download button
- [ ] Both .docx-input and .pdf-input documents can be downloaded in all 3 formats
- [ ] All output formats contain the same redacted text with smart placeholders from M1
- [ ] `fpdf2` is added to `backend/requirements.txt`

### Files to Explore and Modify

**New file: `backend/format_converter.py`**:
- `convert_to_pdf(docx_path: str) -> bytes` — Extract text from .docx, generate PDF using fpdf2. Preserve paragraph structure and headings
- `convert_to_markdown(docx_path: str) -> str` — Extract paragraphs from python-docx, convert headings to `#` syntax, output clean markdown

**`backend/server.py`**:
- Add `output_format` query parameter to `GET /api/download/{file_id}`
- On download: if requested format differs from stored format, call the converter

**`frontend/src/components/ResultsPanel.jsx`**:
- Add format selector (dropdown or radio group) before the download button with options: `.docx`, `.pdf`, `.md`
- Pass selected format as query parameter to the download URL

**`frontend/src/pages/Home.jsx`**:
- Add `outputFormat` state (default: `docx`)
- Pass through to ResultsPanel

### Tests to Write (via /test-first)
- `convert_to_pdf()` produces valid PDF bytes from a .docx file
- `convert_to_markdown()` produces valid markdown with headings and paragraphs
- Download endpoint with `?output_format=pdf` returns PDF content-type
- Download endpoint with `?output_format=md` returns text/markdown content-type
- Download endpoint with `?output_format=docx` or default returns .docx
- Redacted text is preserved identically across all output formats

---

## Milestone 3: Enhanced Pre-Redaction Review Pipeline

### Goal
Add 4 missing review pipeline features so users have full control over redaction decisions.

### Skill Invocations
1. **`/goal-driven`** — Use the goal and success criteria below
2. **`/explore-plan-code`** — Explore, plan, implement each feature
3. **`/test-first`** — Write tests before implementation
4. **`/code-review`** — Review all changed files

### Success Criteria
- [ ] **Term grouping**: Candidates viewed grouped by `original_text` with count badge and master toggle that selects/deselects ALL instances of that term
- [ ] **Category toggles**: All detected PII categories listed dynamically with toggle switches; toggling selects/deselects ALL candidates of that category
- [ ] **Inline force-redact**: Text input to add a custom term for force-redaction; term sent via `force_redact_terms` field in apply-redaction request
- [ ] **Custom placeholder editing**: Edit button per candidate/group to type custom replacement text; overrides sent via `placeholder_overrides` field
- [ ] All 4 features work together without conflicts
- [ ] Backend `/api/apply-redaction` accepts `force_redact_terms` (list of strings) and `placeholder_overrides` (dict of candidate_id → custom text)

### Files to Explore and Modify

**`frontend/src/components/ReviewPanel.jsx`** — All 4 features modify this file:

*Feature 3.1: Group by Term*
- Add view toggle: "Flat view" (current) vs "Grouped view"
- Group candidates by `original_text` (case-insensitive)
- Each group: master checkbox, term text, count badge "(N occurrences)", expandable sub-items
- Master checkbox toggles all instances of that term

*Feature 3.2: Category-Level Toggle*
- Replace current "Policy toggles" card with dynamic category section
- Extract all unique categories from candidates
- Each category: toggle switch + count badge
- Toggling selects/deselects ALL candidates of that category
- Absorb existing `redactLocations` / `redactCountries` toggles into this system

*Feature 3.3: Inline Force-Redact*
- Add "Add custom term" section: text input + "Add" button
- When added, create a local custom candidate in review state with generated candidate_id
- The custom candidates are included in the `force_redact_terms` field when applying

*Feature 3.4: Custom Placeholder Editing*
- Each candidate/group gets an edit icon → inline text input for custom replacement
- Store overrides as `{ candidate_id: "custom text" }` map in state
- Pass map to apply-redaction request as `placeholder_overrides`

**`frontend/src/pages/Home.jsx`**:
- Pass new state (force_redact_terms, placeholder_overrides) through the review → apply flow

**`backend/server.py`** — `/api/apply-redaction`:
- Add `force_redact_terms: Optional[list[str]]` to request body
- Add `placeholder_overrides: Optional[dict[str, str]]` to request body
- Pass force-redact terms through existing `apply_user_always_redact` logic
- Substitute overrides after tracker assigns default placeholders

**`backend/pii_engine.py`**:
- After tracker assigns a placeholder, check `placeholder_overrides` and substitute if present

### Tests to Write (via /test-first)

Backend:
- `/api/apply-redaction` with `force_redact_terms` correctly redacts additional terms
- `/api/apply-redaction` with `placeholder_overrides` uses custom text instead of auto-generated placeholder
- Combined `force_redact_terms` + `placeholder_overrides` work correctly
- Force-redact terms that overlap with existing candidates don't create duplicates

Frontend (if testing framework is available):
- Grouped view correctly groups candidates by original_text
- Master checkbox toggles all instances in a group
- Category toggle selects/deselects all candidates of that category
- Custom force-redact term creates a new candidate in the list
- Editing a placeholder stores the override correctly

---

## Milestone 4: Standalone Installer (Windows + Mac)

### Goal
Create downloadable GUI installers (.exe for Windows, .dmg for Mac) that bundle the entire application for completely offline use by non-technical users.

### Skill Invocations
1. **`/goal-driven`** — Use the goal and success criteria below
2. **`/explore-plan-code`** — Explore, plan, implement
3. **`/test-first`** — Write tests before implementation
4. **`/code-review`** — Review build scripts and Electron app

### Success Criteria
- [ ] PyInstaller bundles the Python backend including spaCy `en_core_web_sm` model into a directory executable
- [ ] React frontend is built to static files and served by the FastAPI backend (single server process)
- [ ] Electron wraps the app: launches backend, opens UI in a window, kills backend on quit
- [ ] Windows .exe installer (via electron-builder NSIS) creates Start Menu shortcut and desktop icon
- [ ] Mac .dmg (via electron-builder) creates a drag-to-install application
- [ ] Installed app works completely offline — no internet after installation
- [ ] Build script (`installer/build_installer.py`) automates the entire pipeline
- [ ] A non-technical user can install and run the app following included instructions

### Files to Create

**`installer/` directory**:
```
installer/
├── electron-app/
│   ├── main.js              # Electron main process — spawns backend, loads UI
│   ├── preload.js            # Preload script for security
│   └── package.json          # Electron + electron-builder config
├── build_backend.py          # PyInstaller build script
├── build_installer.py        # Master build script (backend + frontend + Electron)
├── pyinstaller.spec          # PyInstaller spec for backend
└── README_BUILD.md           # Build instructions
```

**`installer/pyinstaller.spec`**:
- Entry point: `backend/server.py`
- Bundle data: `backend/data/`, `backend/name_data/`, user lists, rules library
- Bundle spaCy model: `en_core_web_sm` directory as data
- Hidden imports: spaCy sub-modules, FastAPI, uvicorn, all dependencies
- Single directory output (not single file — spaCy model is too large)

**`installer/electron-app/main.js`**:
- On start: spawn backend executable as child process
- Poll `http://localhost:8000` until ready
- Load `http://localhost:8000` in BrowserWindow
- On quit: kill backend process, clean up

**`installer/build_installer.py`**:
1. Build React frontend: `cd frontend && npm run build`
2. Copy build output to `backend/frontend_build/`
3. Run PyInstaller to bundle backend
4. Run electron-builder to create platform installer

### Files to Modify

**`backend/server.py`** — Add static frontend serving:
```python
from fastapi.staticfiles import StaticFiles
# Mount React build at root, AFTER all API routes
app.mount("/", StaticFiles(directory="frontend_build", html=True), name="frontend")
```
This eliminates the need for a separate Node.js process at runtime.

### Tests to Write (via /test-first)
- Backend correctly serves static files from `frontend_build/` when directory exists
- Backend health endpoint responds when served from PyInstaller bundle
- Build script runs without errors on the current platform
- Bundled backend starts and responds to API requests

---

## Milestone 5: Testing Against User-Provided Documents

### Goal
Validate the complete system against test documents and the PII type reference. Fix any detection gaps.

### Prerequisites
User must add these to the repo before starting this milestone:
- `TYPES OF PII.docx` — reference listing all PII types to detect
- `/Test Docs/` folder — sample legal documents for testing

### Skill Invocations
1. **`/goal-driven`** — Use the goal and success criteria below
2. **`/explore-plan-code`** — Read test docs, cross-reference against detection engine, fix gaps
3. **`/test-first`** — Create regression tests from test documents
4. **`/code-review`** — Review all detection/pattern changes

### Success Criteria
- [ ] Every PII type listed in `TYPES OF PII.docx` is detected by the system
- [ ] Test documents produce zero false negatives (no PII left unredacted)
- [ ] Test documents produce zero false positives (no generic legal terms incorrectly redacted)
- [ ] Placeholders in output preserve structural context per Milestone 1 specification
- [ ] Regression test cases created from test documents
- [ ] All existing pytest tests still pass

### Steps
1. Read `TYPES OF PII.docx` and list every PII type specified
2. Cross-reference against `backend/indian_pii_data.py` (regex patterns) and `backend/pii_engine.py` (detection passes)
3. Run each test document through the full pipeline (analyze → review → apply)
4. For each document verify: all PII detected, no false positives, correct placeholder format
5. For each gap found:
   - Missing regex pattern → add to `backend/indian_pii_data.py`
   - False positive → add stop phrase to `backend/data/stop_phrases.json`
   - NLP miss → adjust thresholds in `backend/nlp_engine.py` or `backend/pii_engine.py`
6. Create regression test cases from the test documents

### Tests to Write (via /test-first)
- For each test document: extract key PII items, assert they are redacted with correct placeholder format
- For specific non-PII terms in test documents: assert they are NOT redacted
- Cross-reference test: every PII type from `TYPES OF PII.docx` has at least one passing test case

---

## Final Validation

After all 5 milestones are complete, run `/goal-driven` one final time with the FULL success criteria below. The project is NOT complete until ALL criteria pass.

### SC-1: PII Detection Accuracy
- [ ] All PII types listed in `TYPES OF PII.docx` are detected by the system
- [ ] Test documents in `/Test Docs/` produce zero false negatives
- [ ] Test documents produce zero false positives
- [ ] spaCy NLP models are used for name/entity/location detection (not dictionary-only)

### SC-2: Context-Preserving Placeholders
- [ ] Entity names preserve corporate suffixes: "X Private Limited", "Y LLP", "Z Inc"
- [ ] Person names use "Person N" format, preserving titles ("Mr. Person 1", "Dr. Person 2")
- [ ] All other PII categories use human-readable `[Category N]` format
- [ ] An LLM reading the redacted output can determine entity types, person roles, and ID types without seeing the original PII

### SC-3: Input/Output Format Support
- [ ] System accepts .docx and .pdf as input
- [ ] System produces .docx, .pdf, or .md as output per user selection
- [ ] Output files are valid and openable in standard applications

### SC-4: Pre-Redaction Review Pipeline
- [ ] User can see all proposed redaction candidates before redaction is applied
- [ ] User can unselect individual candidates via checkbox
- [ ] User can unselect ALL instances of a specific term at once (grouped toggle)
- [ ] User can select/unselect all instances of a PII category at once (category toggle)
- [ ] User can add a custom word/phrase to be force-redacted during review
- [ ] User can edit/change the placeholder text for any candidate (custom override)

### SC-5: Installer & Offline Operation
- [ ] A Windows .exe installer installs the app without requiring Python, Node, or Docker
- [ ] A Mac .dmg installs the app without requiring Python, Node, or Docker
- [ ] The installed app works completely offline (no internet after installation)
- [ ] A non-technical user can install and run the app following included instructions

### SC-6: Regression
- [ ] All existing pytest tests pass with new placeholder format (assertions updated)
- [ ] Regex-based ID detection works identically to before
- [ ] The two-stage pipeline (analyze → review → apply) works end-to-end
- [ ] Audit CSV export contains original text, placeholder, and category for every item

---

## Critical Files Reference

| File | Role | Milestones |
|---|---|---|
| `backend/pii_engine.py` | Core redaction engine, PIITracker class | M1, M3, M5 |
| `backend/nlp_engine.py` | spaCy NLP pipeline, NER detection | M1, M5 |
| `backend/server.py` | FastAPI routes, file handling | M1, M2, M3, M4 |
| `backend/placeholder_utils.py` | Placeholder detection helpers | M1 |
| `backend/indian_pii_data.py` | Regex patterns, Indian PII data | M5 |
| `backend/rule_library.py` | Allow/Force rule management | M3 |
| `backend/data/stop_phrases.json` | False positive prevention | M5 |
| `backend/requirements.txt` | Python dependencies | M2, M4 |
| `frontend/src/pages/Home.jsx` | Main page, upload flow | M2, M3 |
| `frontend/src/components/ReviewPanel.jsx` | Pre-redaction review UI | M1, M3 |
| `frontend/src/components/ResultsPanel.jsx` | Results display, download | M2 |
| `frontend/src/pages/RuleLibrary.jsx` | Rule management page | M3 |
| `installer/` (new) | Build scripts, Electron app | M4 |
| `backend/format_converter.py` (new) | PDF/MD output conversion | M2 |
