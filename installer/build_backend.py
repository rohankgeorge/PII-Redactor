"""Build the Python backend into a standalone directory using PyInstaller.

Usage:
    python build_backend.py

This script:
  1. Verifies that required tools are installed (PyInstaller, spaCy model).
  2. Runs PyInstaller with the spec file to produce ``backend_dist/server/``.
  3. Copies the dist output to the project root ``backend_dist/`` for
     electron-builder to pick up.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = Path(__file__).resolve().parent / "pyinstaller.spec"
PYINSTALLER_OUTPUT = ROOT / "installer" / "dist" / "server"
DEST = ROOT / "backend_dist"


def _check_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller is not installed. Run: pip install pyinstaller")
        sys.exit(1)


def _check_spacy_model() -> None:
    try:
        import spacy
        spacy.util.get_package_path("en_core_web_sm")
    except Exception:
        print("spaCy model 'en_core_web_sm' not found.")
        print("Install with: python -m spacy download en_core_web_sm")
        sys.exit(1)


def build() -> None:
    _check_pyinstaller()
    _check_spacy_model()

    print("=" * 60)
    print("Building backend with PyInstaller ...")
    print("=" * 60)

    # Clean previous build artifacts
    for d in [ROOT / "installer" / "build", ROOT / "installer" / "dist"]:
        if d.exists():
            shutil.rmtree(d)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            str(SPEC_FILE),
            "--distpath",
            str(ROOT / "installer" / "dist"),
            "--workpath",
            str(ROOT / "installer" / "build"),
        ],
        cwd=str(ROOT / "installer"),
    )

    if result.returncode != 0:
        print("PyInstaller build FAILED.")
        sys.exit(1)

    if not PYINSTALLER_OUTPUT.is_dir():
        print(f"Expected output not found: {PYINSTALLER_OUTPUT}")
        sys.exit(1)

    # Copy to project-root backend_dist/ for electron-builder
    if DEST.exists():
        shutil.rmtree(DEST)
    shutil.copytree(PYINSTALLER_OUTPUT, DEST)

    print()
    print(f"Backend built successfully -> {DEST}")
    print(f"  Contents: {len(list(DEST.rglob('*')))} files")


if __name__ == "__main__":
    build()
