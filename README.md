# RedactAI - Indian PII Redactor

RedactAI is a desktop application that finds and removes personally identifiable information (PII) from legal documents. It is designed for Indian legal professionals who need to share contracts, affidavits, arbitration awards, and other legal documents with AI tools (like ChatGPT or Claude) without exposing the real names, addresses, or ID numbers of the people and companies involved.

You upload a Word or PDF document, the app scans it, and you download a clean version where every piece of PII has been replaced with a safe placeholder.

---

## What it does

You give the app a legal document. It gives you back the same document with every piece of sensitive information replaced:

| Original text | What the app produces |
|---|---|
| Rajesh Sharma | Person 1 |
| Mr. Rajesh Sharma | Mr. Person 1 |
| Dr. Kamala Devi | Dr. Person 2 |
| NeoSan Private Limited | X Private Limited |
| TechCo LLP | Y LLP |
| 2345 6789 0123 (Aadhaar) | [Aadhaar 1] |
| ABCDE1234F (PAN) | [PAN 1] |
| +91 98765 43210 | [Phone 1] |
| test@example.com | [Email 1] |
| No. 12, MG Road, Bangalore 560001 | [Address 1] |
| 560001 (PIN code) | [PIN 1] |

The same person or company always gets the same placeholder throughout the document, so the structure and meaning of the document is preserved. An LLM reading the redacted version can still understand who did what to whom &mdash; it just cannot see the real identities.

---

## Features

### PII detection
The app detects 20+ categories of Indian PII:

- **Identity documents**: Aadhaar numbers, PAN numbers, passport numbers, voter IDs, driving licences
- **Financial identifiers**: bank account numbers, IFSC codes, GST numbers, UPI IDs, credit/debit card patterns
- **Contact information**: phone numbers, email addresses
- **Personal details**: full names (Indian and international), dates of birth
- **Location data**: full addresses (street, city, state, PIN code), standalone PIN codes, city and state names
- **Organisations**: company names with corporate suffixes (Private Limited, LLP, Ltd, Inc, Trust, etc.)
- **Vehicle identifiers**: vehicle registration numbers

Detection uses a combination of:
- Regular expressions for structured IDs (Aadhaar, PAN, GST, etc.)
- spaCy NLP models for names, locations, and organisations
- An EntityRuler dictionary with 500+ Indian first names and surnames
- Heuristic scoring for address detection (even addresses without PIN codes)
- A final QA pass that catches anything the earlier passes missed

### Smart placeholders
Instead of generic `[REDACTED]` tags, the app produces human-readable placeholders that preserve the structural meaning of the document:
- Person names become **Person 1**, **Person 2**, etc. (titles like Mr., Dr. are preserved)
- Company names become **X Private Limited**, **Y LLP**, etc. (corporate suffix preserved)
- ID numbers become **[Aadhaar 1]**, **[PAN 1]**, **[Email 1]**, etc.
- The same original value always maps to the same placeholder everywhere in the document

### Review mode
Before the app applies redaction, you can review every proposed change:
- See all detected PII candidates with their category, location, and proposed placeholder
- Uncheck individual items you do not want redacted
- Toggle entire PII categories on or off (e.g., turn off all location redaction)
- Group candidates by term to select/deselect all occurrences at once
- Add custom words or phrases to force-redact (even if the engine did not detect them)
- Edit the placeholder text for any candidate to use your own wording

### Output formats
Download your redacted document in three formats:
- **.docx** (Word) &mdash; default
- **.pdf** &mdash; generated from the redacted text
- **.md** (Markdown) &mdash; clean text with heading structure preserved

### Audit trail
Export a CSV report listing every redaction: what was found, what it was replaced with, and where in the document it appeared.

### Rule library
Build a persistent library of rules that apply to every future document:
- **Always Redact** rules: terms that should always be redacted, even if the engine does not detect them as PII
- **Never Redact** rules: terms that should never be redacted, even if the engine thinks they are PII (useful for company names that should remain visible)

### Privacy
All processing happens locally on your own computer. No data is sent to any cloud service, API, or third-party server. The app runs entirely offline after installation.

---

## Limitations

Be aware of these before relying on the app for sensitive work:

- **Image-based (scanned) PDFs are not supported.** The app can only process PDFs that contain a text layer. If your PDF was created by scanning paper, the app cannot read it. You would need to run OCR on it first (using a separate tool) and then process the resulting text-based PDF.
- **Not 100% accurate.** No automated PII detection system is perfect. The app may occasionally miss a name or ID number (false negative), or incorrectly flag a legal term as PII (false positive). Always use Review Mode for important documents and verify the output yourself.
- **Designed for Indian legal documents.** The regex patterns, name dictionaries, and address heuristics are tuned for Indian PII formats. The app will detect some international PII (emails, phone numbers, US ZIP codes, UK postcodes), but it is not optimised for non-Indian documents.
- **Does not detect PII in images, headers/footers of PDFs, or embedded objects.** Only the main text content of the document is scanned.
- **Maximum file size is 10 MB per document.**
- **The app uses a lightweight NLP model (en_core_web_sm).** Larger transformer models would be more accurate but would make the app much slower and harder to install offline. Optional models (OpenNyAI Legal NER, IndicNER) can be installed separately for better legal-domain accuracy.
- **Financial figures (e.g., "INR 25 crores") are not redacted** because they are not personally identifiable on their own. Court case numbers and invoice numbers are also not redacted by default.

---

## How to install and run

There are three ways to run RedactAI, from easiest to most technical. Pick the one that matches your comfort level.

---

### Option A: Standalone installer (easiest &mdash; no technical knowledge needed)

> **Note:** The standalone installer must first be built from source. If someone has already built it for you and given you the installer file, skip straight to the installation steps below.

#### Windows

1. Find the installer file. It will be named something like **PII Redactor Setup 1.0.0.exe**.
2. Double-click the installer file.
3. If Windows shows a "Windows protected your PC" warning:
   - Click **More info**.
   - Click **Run anyway**.
4. Follow the installer steps:
   - Choose where to install (the default location is fine).
   - Click **Install**.
   - Wait for it to finish (this may take a minute).
   - Click **Finish**.
5. Find **PII Redactor** in your Start Menu or on your Desktop and double-click to open it.
6. The app will take 15-30 seconds to start up the first time (it is loading the language model). A window will open when it is ready.
7. You are now ready to use the app. See the **How to use the app** section below.

To uninstall: go to **Settings > Apps > Installed apps**, find PII Redactor, and click **Uninstall**.

#### Mac

1. Find the installer file. It will be named something like **PII Redactor-1.0.0.dmg**.
2. Double-click the .dmg file to open it.
3. Drag the **PII Redactor** icon into the **Applications** folder.
4. Open your **Applications** folder and double-click **PII Redactor**.
5. If macOS shows a warning that the app is from an unidentified developer:
   - Go to **System Settings > Privacy & Security**.
   - Scroll down and click **Open Anyway** next to the PII Redactor message.
   - Click **Open** in the confirmation dialog.
6. The app will take 15-30 seconds to start up the first time. A window will open when it is ready.
7. You are now ready to use the app. See the **How to use the app** section below.

To uninstall: drag PII Redactor from your Applications folder to the Trash.

---

### Option B: Run from source with the startup script (Windows)

Use this if you do not have the standalone installer, or if you want to run the latest version directly from the source code. This requires installing three free programs first.

#### Step 1: Install required software (one-time setup)

Install these three programs in this order. All are free.

**1. Git**
- Go to https://git-scm.com/download/win
- Download and run the installer.
- Keep all default options (click **Next** until done).

**2. Python (version 3.10, 3.11, 3.12, or 3.13)**
- Go to https://www.python.org/downloads/
- Download **Python 3.13** (or 3.12, 3.11, or 3.10). Do **not** use Python 3.14.
- **Important:** In the installer, check the box that says **"Add Python to PATH"** before clicking Install.
- Click **Install Now**.

**3. Node.js**
- Go to https://nodejs.org/
- Download the **LTS** version (the button on the left).
- Run the installer with default settings.

After installing all three, restart your computer.

#### Step 2: Download RedactAI

**Easy way (download ZIP):**
1. On the GitHub page for this project, click the green **Code** button.
2. Click **Download ZIP**.
3. Extract the ZIP to a simple location, for example: `C:\RedactAI`

**Alternative (using Git):**
1. Open **Command Prompt** (press Windows key, type `cmd`, press Enter).
2. Type this and press Enter:
   ```
   git clone https://github.com/rohankgeorge/PII-Redactor.git
   ```
3. This creates a folder called `PII-Redactor`.

#### Step 3: Start the app

1. Open the `PII-Redactor` folder in File Explorer.
2. Find `start_windows.bat` and double-click it.
3. Two terminal windows will open. This is normal. They are running the backend and frontend servers.
4. **Wait 1-2 minutes** the first time. The app is downloading a language model and installing packages. You will see text scrolling in the terminal windows. Wait until the text stops and you see messages like "Uvicorn running" and "Compiled successfully".
5. Open your web browser and go to: **http://localhost:3000**
6. You are now ready to use the app. See the **How to use the app** section below.

#### How to stop the app

Close both terminal windows that were opened by `start_windows.bat`, or press `Ctrl + C` in each window.

---

### Option C: Run from source on Mac / Linux (manual setup)

#### Step 1: Install required software

**Mac:**
1. Open **Terminal** (press Cmd + Space, type "Terminal", press Enter).
2. Install Homebrew (if you do not have it already):
   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
3. Install Python and Node.js:
   ```
   brew install python@3.13 node
   ```

**Linux (Ubuntu/Debian):**
```
sudo apt update
sudo apt install python3 python3-pip python3-venv nodejs npm
```

#### Step 2: Download RedactAI

```
git clone https://github.com/rohankgeorge/PII-Redactor.git
cd PII-Redactor
```

Or download the ZIP from GitHub and extract it.

#### Step 3: Set up the backend

Open Terminal and run these commands one at a time:

```
cd PII-Redactor/backend
pip3 install -r requirements.txt
python3 -m spacy download en_core_web_sm
```

This will take a few minutes the first time (it is downloading a language model and installing packages).

#### Step 4: Set up the frontend

Open a **second** Terminal window and run:

```
cd PII-Redactor/frontend
npm install
```

#### Step 5: Start the app

In the **first** Terminal window (backend):
```
cd PII-Redactor/backend
uvicorn server:app --host 0.0.0.0 --port 8000
```

In the **second** Terminal window (frontend):
```
cd PII-Redactor/frontend
npm start
```

Wait until you see "Compiled successfully" in the frontend terminal.

Open your web browser and go to: **http://localhost:3000**

#### How to stop the app

Press `Ctrl + C` in both terminal windows.

---

## How to use the app

Once the app is running (whether from the installer or from source), the workflow is the same:

### Quick mode (one-click redaction)

1. Leave the **Review mode** toggle OFF (it is off by default).
2. Drag and drop your document onto the upload area, or click to browse for a file. Supported formats: `.doc`, `.docx`, and text-based `.pdf`. You can upload multiple files at once.
3. Wait while the app scans your document. This usually takes 5-30 seconds depending on the document length.
4. The results screen shows how many PII items were found, broken down by category.
5. Choose your preferred output format: **.docx**, **.pdf**, or **.md**.
6. Click **Download Redacted Document**.
7. Click **Export Audit Report** to download a CSV file listing every redaction that was made.
8. Click **Start Over** to process another document.

### Review mode (recommended for important documents)

1. Turn ON the **Review mode** toggle before uploading.
2. Upload a single document.
3. The app shows you every PII candidate it found, with:
   - The PII category (e.g., "Individual", "Aadhaar Number", "Address")
   - The original text
   - The proposed placeholder
   - Where in the document it was found
4. For each candidate, you can:
   - **Uncheck** it to prevent that item from being redacted
   - Click **Edit placeholder** to change the replacement text
5. Use the **Category toggles** to turn entire categories on or off (e.g., turn off all location redaction).
6. Switch to **Grouped view** to see all occurrences of the same term together, with a master checkbox to select/deselect all at once.
7. Use the **Force-redact custom terms** section to add words or phrases the app missed.
8. When you are satisfied, click **Apply Selected Redactions**.
9. Download your redacted document in your preferred format.

### Rule library

Click **Rule Library** in the top navigation bar to manage persistent rules:

- **Always Redact**: add terms that should be redacted in every document you process, even if the engine does not detect them as PII. Example: a client name that does not follow standard Indian naming patterns.
- **Never Redact**: add terms that should never be redacted, even if the engine thinks they are PII. Example: your own law firm's name, which you want to keep visible in redacted documents.

Rules are saved locally on your computer and apply to all future documents.

---

## Troubleshooting

### "Python is not recognized" (Windows)

Python was not added to your system PATH during installation.

**Fix:**
1. Re-run the Python installer (download it again from python.org if needed).
2. Choose **Modify**.
3. Make sure **"Add Python to PATH"** is checked.
4. Complete the installation.
5. Close and re-open Command Prompt.

### "npm is not recognized" (Windows)

Node.js is not installed or your PATH was not updated.

**Fix:**
1. Re-install Node.js from https://nodejs.org/ (LTS version).
2. Restart your computer.

### The app says "All files failed to process"

The frontend cannot reach the backend server.

**Fix:**
1. Check that the backend terminal window is still open and running (look for "Uvicorn running on http://0.0.0.0:8000").
2. Open http://localhost:8000/api/ in your browser. You should see a JSON message. If not, the backend has crashed &mdash; close and re-open `start_windows.bat`.
3. If the backend is running but the frontend still cannot connect, create a file called `.env` inside the `frontend` folder with this content:
   ```
   REACT_APP_BACKEND_URL=http://localhost:8000
   ```
   Then restart the frontend.

### Port 3000 or 8000 is already in use

Another program is using that port, or a previous session did not shut down cleanly.

**Fix:**
1. Close any old terminal windows from previous runs.
2. Restart your computer.
3. Run `start_windows.bat` again.

### The app is very slow on the first document

This is normal. The first document triggers the loading of the NLP language model into memory, which takes 10-20 seconds. Subsequent documents will be much faster.

### Python 3.14 causes installation errors

Some dependencies (like spaCy) do not yet support Python 3.14.

**Fix:** Install Python 3.13 instead from https://www.python.org/downloads/

### The app missed some PII in my document

No automated system is 100% accurate. You can:
1. Use **Review mode** and check the candidates list and manual review warnings.
2. Add the missed term to the **Rule Library** as an "Always Redact" rule so it is caught in future documents.
3. Use the **Force-redact** feature in Review mode to add the term for the current document.

### The app incorrectly redacted a term that is not PII

1. Use **Review mode** and uncheck that candidate before applying.
2. Add the term to the **Rule Library** as a "Never Redact" rule so it is preserved in future documents.

---

## Alternative: Run with Docker

If you are familiar with Docker:

```
docker-compose up --build
```

Then open:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

---

## For developers

### Running tests

```
cd backend
python -m pytest
```

### Building the standalone installer

See [installer/README_BUILD.md](installer/README_BUILD.md) for detailed build instructions.

### Optional NLP models

For better accuracy on legal documents, you can install optional models:

**OpenNyAI Legal NER** (trained on Indian legal text):
```
pip install https://huggingface.co/opennyaiorg/en_legal_ner_trf/resolve/main/en_legal_ner_trf-any-py3-none-any.whl
```

**IndicNER** (better for Indic-language names):
```
pip install transformers torch
```

These models are automatically used if installed. They are not required for basic operation.

### Project structure

```
PII-Redactor/
  backend/
    server.py              # FastAPI routes and file handling
    pii_engine.py          # Core PII detection and redaction engine
    nlp_engine.py          # spaCy NLP pipeline and name/location detection
    placeholder_utils.py   # Placeholder pattern recognition helpers
    format_converter.py    # PDF and Markdown output conversion
    rule_library.py        # Persistent allow/force rule management
    indian_pii_data.py     # Regex patterns for Indian PII formats
    data/stop_phrases.json # False positive prevention lists
    requirements.txt       # Python dependencies
  frontend/
    src/pages/Home.jsx          # Main upload and redaction flow
    src/components/ReviewPanel.jsx  # Pre-redaction review UI
    src/components/ResultsPanel.jsx # Results display and download
    src/pages/RuleLibrary.jsx       # Rule management page
  installer/
    build_installer.py     # Master build script for standalone installer
    electron-app/          # Electron wrapper for desktop app
    pyinstaller.spec       # PyInstaller configuration for backend bundling
  start_windows.bat        # One-click startup for Windows
  docker-compose.yml       # Docker setup
```
