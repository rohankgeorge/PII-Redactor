# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the PII Redactor FastAPI backend.

Bundles the Python backend including spaCy models, data files, and all
dependencies into a single-directory executable.

Usage:
    cd installer
    pyinstaller pyinstaller.spec
"""

import os
import sys
from pathlib import Path

import spacy

block_cipher = None

# ── Paths ────────────────────────────────────────────────────
ROOT = Path(SPECPATH).parent
BACKEND = ROOT / "backend"
SPACY_MODEL_PATH = Path(spacy.util.get_package_path("en_core_web_sm"))

# ── Data files to bundle ────────────────────────────────────
datas = [
    # Backend data files
    (str(BACKEND / "data"), "data"),
    (str(BACKEND / "name_data"), "name_data"),
    # User lists and rules
    (str(BACKEND / "user_allow_list.txt"), "."),
    (str(BACKEND / "user_redact_list.txt"), "."),
    # spaCy model
    (str(SPACY_MODEL_PATH), os.path.join("en_core_web_sm", SPACY_MODEL_PATH.name)),
]

# Include frontend_build if it exists (for standalone serving)
frontend_build = BACKEND / "frontend_build"
if frontend_build.is_dir():
    datas.append((str(frontend_build), "frontend_build"))

# ── Hidden imports ───────────────────────────────────────────
hiddenimports = [
    # spaCy internals
    "spacy",
    "spacy.lang.en",
    "spacy.pipeline",
    "spacy.pipeline.ner",
    "spacy.pipeline.sentencizer",
    "spacy.pipeline.entity_ruler",
    "spacy.pipeline.span_ruler",
    "spacy.tokenizer",
    "spacy.vocab",
    "spacy.kb",
    "spacy.tokens",
    "spacy.attrs",
    "spacy.morphology",
    "spacy.lookups",
    "spacy.vectors",
    "thinc",
    "thinc.api",
    "thinc.backends",
    "thinc.shims",
    "thinc.model",
    "cymem",
    "cymem.cymem",
    "preshed",
    "preshed.maps",
    "murmurhash",
    "murmurhash.mrmr",
    "blis",
    "srsly",
    "srsly.msgpack",
    "catalogue",
    "wasabi",
    "typer",
    # FastAPI and web stack
    "fastapi",
    "starlette",
    "starlette.middleware.cors",
    "starlette.staticfiles",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "h11",
    "pydantic",
    "pydantic_core",
    "anyio",
    "anyio._backends",
    "anyio._backends._asyncio",
    # Document processing
    "docx",
    "pypdf",
    "fpdf",
    "fpdf2",
    # Data / ML support
    "numpy",
    "regex",
    # Motor / pymongo (may be optional but imported)
    "motor",
    "motor.motor_asyncio",
    "pymongo",
    # Format converter
    "format_converter",
    # Other backend modules
    "pii_engine",
    "nlp_engine",
    "placeholder_utils",
    "indian_pii_data",
    "global_pii_data",
    "generated_indian_names",
    "rule_library",
    "test_doc_support",
]

# ── Analysis ─────────────────────────────────────────────────
a = Analysis(
    [str(BACKEND / "server.py")],
    pathex=[str(BACKEND)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
    ],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Keep console for server logging
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="server",
)
