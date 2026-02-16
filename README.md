# PII-Redactor

A beginner-friendly tool that removes personally identifiable information (PII) from text.

---

## If you are brand new: use this exact guide (Windows)

This section is written for users who have never run code from GitHub before.

## What you will do

1. Install 3 things (Git, Python, Node.js)
2. Download this project from GitHub
3. Double-click one file: `start_windows.bat`
4. Open the app in your browser

---

## Step 1) Install required software (one time setup)

Install these in this exact order:

### 1. Git
- Go to: https://git-scm.com/download/win
- Download and run the installer.
- During install, keep default options (click **Next** until done).

### 2. Python (3.10 to 3.13)
- Go to: https://www.python.org/downloads/windows/
- Download **Python 3.10, 3.11, 3.12, or 3.13** (do not use Python 3.14 for this project).
- IMPORTANT: In the installer, check the box: **Add Python to PATH**.
- Click **Install Now**.

### 3. Node.js (LTS version)
- Go to: https://nodejs.org/
- Download the **LTS** version.
- Run installer with default settings.

---

## Step 2) Download this project from GitHub

You can do this with either method below.

### Option A (easiest): Download ZIP
1. Open this repository page on GitHub.
2. Click **Code** → **Download ZIP**.
3. Extract ZIP to a simple location, for example:
   - `C:\PII-Redactor`

### Option B: Clone with Git
1. Open **Command Prompt**.
2. Run:

```bat
git clone <REPOSITORY_URL>
```

3. Move into the folder:

```bat
cd PII-Redactor
```

> If you used ZIP download, just open the extracted `PII-Redactor` folder in File Explorer.

---

## Step 3) Start the app

1. Open the `PII-Redactor` folder.
2. Find `start_windows.bat`.
3. Double-click `start_windows.bat`.

It will open terminal windows and do setup automatically:
- install Python packages
- download a language model
- install frontend packages
- start backend on port `8000`
- start frontend on port `3000`

Supported uploads: `.doc`, `.docx`, and text-based `.pdf` (image-only/scanned PDFs are not supported yet).

### First run can take several minutes
This is normal.

---

## Step 4) Open the app in browser

After startup finishes, open:

- **Frontend (main app):** http://localhost:3000
- **Backend API (technical endpoint):** http://localhost:8000

Use the frontend URL (`3000`) to use the application.

---

## How to stop the app

- Close the terminal windows that were opened by `start_windows.bat`,
  **or**
- Press `Ctrl + C` in each terminal window.

---

## Troubleshooting (common beginner issues)

### “python is not recognized”
Python was likely not added to PATH.

Fix:
1. Re-run Python installer.
2. Enable **Add Python to PATH**.
3. Restart Command Prompt.

### `KeyError: 'MONGO_URL'` when starting backend
This happened in older versions that required MongoDB environment variables.

Fix:
1. Pull/download the latest version of this repo (backend now has local defaults).
2. Re-run `start_windows.bat`.

Optional (if you want to set values manually), create `backend/.env` with:
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=pii_redactor
```

### `No matching distribution found for spacy-transformers==1.3.9`
This usually means you installed an unsupported Python version (most often Python 3.14).

Fix:
1. Install Python **3.13** from https://www.python.org/downloads/windows/
2. In Windows, open **Command Prompt** in the project root and run:
   ```bat
   py -3.13 -m venv .venv
   .venv\Scripts\activate
   pip install -r backend\requirements.txt
   python -m spacy download en_core_web_sm
   ```
3. Then run `start_windows.bat` again.

Tip: If you have Python 3.14 installed, keep it if you want, but make sure this project uses `py -3.13`.

### “npm is not recognized”
Node.js is missing or PATH not updated.

Fix:
1. Reinstall Node.js LTS.
2. Restart your PC (or sign out/in).

### If you still get `npm ERR! ERESOLVE`
This usually means your local frontend dependencies are cached from an older setup.

Fix:
1. Close frontend terminal.
2. In `PII-Redactor\frontend`, delete `node_modules` folder if it exists.
3. Delete `package-lock.json` if it exists.
4. Run `start_windows.bat` again (it will reinstall cleanly).

### `ERESOLVE` mentioning `react-day-picker` and `react@19`
This means npm resolved React 19, but `react-day-picker@8.10.1` supports React up to 18.

Fix:
1. Pull/download the latest version of this repo (it pins React to 18).
2. Delete old frontend install files:
   - `PII-Redactor\frontend\node_modules`
   - `PII-Redactor\frontend\package-lock.json`
3. Re-run `start_windows.bat`.

### Frontend shows "All files failed to process" at `http://localhost:3000`
Most commonly, frontend cannot reach backend.

Quick checks:
1. Make sure backend terminal is running and shows no crash tracebacks.
2. Open `http://localhost:8000/api/` in browser. You should see JSON message.
3. If backend is running on a different URL, create `frontend/.env` with:
   ```env
   REACT_APP_BACKEND_URL=http://localhost:8000
   ```
4. Restart frontend terminal after any `.env` change.

### Frontend opens but page is blank / errors
1. Check backend window for errors.
2. Make sure backend says it is running on `http://0.0.0.0:8000`.
3. Re-run `start_windows.bat`.

### Port already in use (3000 or 8000)
Another program is already using that port.

Quick fix:
1. Close old terminal windows from previous runs.
2. Restart your computer.
3. Run `start_windows.bat` again.

---


## Pre-redaction review pipeline (analyze → apply)

The app now supports a two-step flow that lets you review redaction candidates before finalizing output:

1. **Analyze** (`POST /api/analyze`) uploads a document, runs detection, and returns:
   - `analysis_id`
   - `candidates` (with `candidate_id`, category, placeholder, location, policy tags)
   - review metadata (`review`, `qa_signals`, `audit_log`)
2. **Apply redaction** (`POST /api/apply-redaction`) uses the `analysis_id` to produce the downloadable redacted file and supports:
   - Candidate filtering with `include_candidate_ids` **or** `exclude_candidate_ids`
   - Policy toggles: `redact_locations` and `redact_countries`

Backward compatibility is preserved:
- **`POST /api/redact`** still works as the one-shot endpoint for the existing frontend and older clients.

### Quick API examples

Analyze:

```bash
curl -X POST http://localhost:8000/api/analyze \
  -F "file=@sample.docx"
```

Apply all candidates:

```bash
curl -X POST http://localhost:8000/api/apply-redaction \
  -H "Content-Type: application/json" \
  -d '{"analysis_id":"<analysis_id>"}'
```

Apply with policy toggles:

```bash
curl -X POST http://localhost:8000/api/apply-redaction \
  -H "Content-Type: application/json" \
  -d '{"analysis_id":"<analysis_id>","redact_locations":false,"redact_countries":false}'
```

### Pipeline test commands

From the repository root:

```bash
pytest -q backend/test_analysis_pipeline.py
```

Optional broader validation:

```bash
pytest -q backend/test_analysis_pipeline.py backend/test_audit_original_text.py
```

## Optional custom word lists

You can customize what should always or never be redacted:

- Always redact list: `backend/user_redact_list.txt`
- Never redact list: `backend/user_allow_list.txt`

Rules:
- One term per line
- Lines starting with `#` are ignored

---

## Optional models

OpenNyAI Legal NER (optional):

```bash
pip install https://huggingface.co/opennyaiorg/en_legal_ner_trf/resolve/main/en_legal_ner_trf-any-py3-none-any.whl
```

IndicNER (optional):

```bash
pip install transformers torch
```

---

## Alternative: Run with Docker

If you already know Docker:

```bash
docker-compose up --build
```

Then open:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
