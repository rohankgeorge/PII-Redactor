# PII-Redactor Repository Agent Instructions

## Project Overview

This is a PII (Personally Identifiable Information) redaction web application with a Python backend and JavaScript frontend. The backend detects and redacts Indian PII from text using regex patterns and name dictionaries. The frontend provides a browser-based interface.

Repository structure:
- `backend/` — Python backend (pii_engine.py, indian_pii_data.py, and server files)
- `frontend/` — JavaScript/HTML/CSS frontend
- `tests/` — Test files
- `test_reports/` — Test output reports

## Key Constraints

- The regex-based detection for structured Indian IDs (Aadhaar, PAN, GST, IFSC, phone numbers, email, UPI, bank accounts, driving licence, passport, voter ID, vehicle registration, PIN codes) must remain untouched. These patterns work correctly and must not be replaced.
- The dictionary-based name and location detection (INDIAN_FIRST_NAMES, INDIAN_SURNAMES, INDIAN_CITIES, INDIAN_STATES sets in indian_pii_data.py) is what is being replaced/augmented by NLP models.
- The frontend should require zero changes for backend-only modifications. The API contract between frontend and backend must be preserved.
- All new Python dependencies must be added to requirements.txt.
- The application must remain runnable on Windows 11 with Python 3.10+ and Node.js 18+.

## ExecPlans

When writing complex features or significant refactors, use an ExecPlan (as described in .agent/PLANS.md) from design to implementation.

## Testing

- Run backend tests with: `cd backend && python -m pytest` or `python backend_test.py` from the repo root.
- The frontend can be tested by running `cd frontend && npm start` and verifying the UI loads and accepts text input.
- After any backend change, verify that: (a) existing regex-based ID detection still works, (b) name detection works, (c) the redacted output uses the same `[REDACTED_CATEGORY_N]` placeholder format.

## Git Workflow

- Create a git checkpoint before starting each milestone.
- Commit after each milestone with a descriptive message.
- If a milestone fails, revert to the checkpoint and retry.
