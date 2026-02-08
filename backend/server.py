from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
import io
import base64
from pathlib import Path
from typing import Dict
from docx import Document as DocxDocument

from indian_pii_data import (
    PII_REGEX_PATTERNS,
    INDIAN_FIRST_NAMES,
    INDIAN_SURNAMES,
    INDIAN_CITIES,
    INDIAN_STATES,
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# MongoDB connection (required by template)
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# ── Pre‑compile name & location patterns ────────────────────
_all_names = sorted(INDIAN_FIRST_NAMES | INDIAN_SURNAMES, key=len, reverse=True)
NAME_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in _all_names) + r")\b"
) if _all_names else None

_all_locations = sorted(INDIAN_CITIES | INDIAN_STATES, key=len, reverse=True)
LOCATION_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(loc) for loc in _all_locations) + r")\b",
    re.IGNORECASE,
) if _all_locations else None


# ── Core redaction logic ────────────────────────────────────
def redact_text(text: str, stats: Dict[str, int]) -> str:
    if not text or not text.strip():
        return text

    # 1. Regex‑based patterns (most → least specific)
    for category, pattern in PII_REGEX_PATTERNS:
        def _replacer(match, cat=category):
            stats[cat] = stats.get(cat, 0) + 1
            return f"[REDACTED_{cat}]"
        text = pattern.sub(_replacer, text)

    # 2. Dictionary‑based name detection
    if NAME_PATTERN:
        def _name_replacer(match):
            stats["NAME"] = stats.get("NAME", 0) + 1
            return "[REDACTED_NAME]"
        text = NAME_PATTERN.sub(_name_replacer, text)

    # 3. Dictionary‑based location detection
    if LOCATION_PATTERN:
        def _loc_replacer(match):
            stats["LOCATION"] = stats.get("LOCATION", 0) + 1
            return "[REDACTED_LOCATION]"
        text = LOCATION_PATTERN.sub(_loc_replacer, text)

    return text


def _process_paragraph(para, stats: Dict[str, int]):
    full_text = para.text
    if not full_text.strip():
        return
    new_text = redact_text(full_text, stats)
    if new_text != full_text and para.runs:
        for i, run in enumerate(para.runs):
            run.text = new_text if i == 0 else ""


def process_document(doc_bytes: bytes):
    doc = DocxDocument(io.BytesIO(doc_bytes))
    stats: Dict[str, int] = {}

    # Paragraphs
    for para in doc.paragraphs:
        _process_paragraph(para, stats)

    # Tables (including nested)
    def _process_table(table):
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    _process_paragraph(para, stats)
                for nested in cell.tables:
                    _process_table(nested)

    for table in doc.tables:
        _process_table(table)

    # Headers & footers
    for section in doc.sections:
        if section.header:
            for para in section.header.paragraphs:
                _process_paragraph(para, stats)
        if section.footer:
            for para in section.footer.paragraphs:
                _process_paragraph(para, stats)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return stats, sum(stats.values()), buf.read()


# ── Routes ──────────────────────────────────────────────────
@api_router.get("/")
async def root():
    return {"message": "RedactAI API is running"}


@api_router.post("/redact")
async def redact_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB.")

    try:
        stats, total, redacted_bytes = process_document(content)
    except Exception as exc:
        logger.error("Document processing failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}")

    original_stem = file.filename.rsplit(".", 1)[0]
    return {
        "stats": stats,
        "total": total,
        "file_base64": base64.b64encode(redacted_bytes).decode("utf-8"),
        "filename": f"redacted_{original_stem}.docx",
    }


# ── App wiring ──────────────────────────────────────────────
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
