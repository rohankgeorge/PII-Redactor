# PII Redactor — Build Instructions

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.10+ | https://python.org |
| Node.js | 18+ | https://nodejs.org |
| Yarn | 1.22+ | `npm install -g yarn` |
| PyInstaller | 6+ | `pip install pyinstaller` |

### Python dependencies

```bash
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Frontend dependencies

```bash
cd frontend
yarn install
```

## Quick Build (Full Pipeline)

```bash
cd installer
python build_installer.py
```

This runs the complete pipeline:

1. **Frontend** — Builds React to static files, copies to `backend/frontend_build/`
2. **Backend** — Bundles Python + spaCy + FastAPI via PyInstaller to `backend_dist/`
3. **Electron** — Wraps everything into a platform installer in `dist/`

### Platform-specific builds

```bash
# Windows only (.exe)
python build_installer.py --platform win

# Mac only (.dmg)
python build_installer.py --platform mac

# Both platforms
python build_installer.py --platform all
```

### Partial builds

```bash
# Skip frontend (use existing frontend_build/)
python build_installer.py --skip-frontend

# Skip backend (use existing backend_dist/)
python build_installer.py --skip-backend
```

## Output

| Platform | Output | Location |
|---|---|---|
| Windows | NSIS installer (.exe) | `dist/PII Redactor Setup *.exe` |
| Mac | DMG image (.dmg) | `dist/PII Redactor-*.dmg` |

## How It Works

The standalone app uses a single-process architecture:

1. **FastAPI backend** serves both the API (`/api/*`) and the React frontend (`/`) from static files
2. **Electron** launches the backend as a child process, waits for it to be ready, then opens a window pointing at `http://localhost:8000`
3. On quit, Electron kills the backend process

No internet connection is required after installation.

## Troubleshooting

### PyInstaller fails with missing module

Add the module to `hiddenimports` in `pyinstaller.spec` and rebuild.

### spaCy model not found in bundle

Ensure `en_core_web_sm` is installed (`python -m spacy download en_core_web_sm`) before building.

### Frontend build fails

```bash
cd frontend
yarn install
yarn build
```

If the build succeeds manually, try `python build_installer.py --skip-frontend` and copy the `frontend/build/` output to `backend/frontend_build/` manually.
