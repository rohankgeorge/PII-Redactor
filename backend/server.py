from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
import io
import base64
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List
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


# ── .doc → .docx conversion ─────────────────────────────────
def convert_doc_to_docx(doc_bytes: bytes) -> bytes:
    """Convert legacy .doc to .docx via antiword text extraction."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as tmp:
            tmp.write(doc_bytes)
            tmp_path = tmp.name

        result = subprocess.run(
            ["antiword", tmp_path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"antiword conversion failed: {result.stderr.strip()}")

        doc = DocxDocument()
        for line in result.stdout.split("\n"):
            doc.add_paragraph(line)

        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf.read()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ── Core redaction logic ────────────────────────────────────
def redact_text(
    text: str,
    stats: Dict[str, int],
    audit_log: List[dict] | None = None,
    context: str = "",
) -> str:
    if not text or not text.strip():
        return text

    # 1. Regex‑based patterns (most → least specific)
    for category, pattern in PII_REGEX_PATTERNS:
        def _replacer(match, cat=category):
            stats[cat] = stats.get(cat, 0) + 1
            if audit_log is not None:
                audit_log.append({"category": cat, "placeholder": f"[REDACTED_{cat}]", "location": context})
            return f"[REDACTED_{cat}]"
        text = pattern.sub(_replacer, text)

    # 2. Dictionary‑based name detection
    if NAME_PATTERN:
        def _name_replacer(match):
            stats["NAME"] = stats.get("NAME", 0) + 1
            if audit_log is not None:
                audit_log.append({"category": "NAME", "placeholder": "[REDACTED_NAME]", "location": context})
            return "[REDACTED_NAME]"
        text = NAME_PATTERN.sub(_name_replacer, text)

    # 3. Dictionary‑based location detection
    if LOCATION_PATTERN:
        def _loc_replacer(match):
            stats["LOCATION"] = stats.get("LOCATION", 0) + 1
            if audit_log is not None:
                audit_log.append({"category": "LOCATION", "placeholder": "[REDACTED_LOCATION]", "location": context})
            return "[REDACTED_LOCATION]"
        text = LOCATION_PATTERN.sub(_loc_replacer, text)

    return text


def _process_paragraph(para, stats: Dict[str, int], audit_log: list, ctx: str):
    full_text = para.text
    if not full_text.strip():
        return
    new_text = redact_text(full_text, stats, audit_log, ctx)
    if new_text != full_text and para.runs:
        for i, run in enumerate(para.runs):
            run.text = new_text if i == 0 else ""


def process_document(doc_bytes: bytes):
    doc = DocxDocument(io.BytesIO(doc_bytes))
    stats: Dict[str, int] = {}
    audit_log: list = []
    para_num = 0

    # Paragraphs
    for para in doc.paragraphs:
        para_num += 1
        _process_paragraph(para, stats, audit_log, f"Paragraph {para_num}")

    # Tables (including nested)
    table_num = 0

    def _process_table(table, prefix=""):
        nonlocal table_num
        table_num += 1
        for r_idx, row in enumerate(table.rows):
            for c_idx, cell in enumerate(row.cells):
                ctx = f"{prefix}Table {table_num}, Row {r_idx+1}, Col {c_idx+1}"
                for para in cell.paragraphs:
                    _process_paragraph(para, stats, audit_log, ctx)
                for nested in cell.tables:
                    _process_table(nested, prefix=f"{ctx} > ")

    for table in doc.tables:
        _process_table(table)

    # Headers & footers
    for s_idx, section in enumerate(doc.sections):
        if section.header:
            for para in section.header.paragraphs:
                _process_paragraph(para, stats, audit_log, f"Header (section {s_idx+1})")
        if section.footer:
            for para in section.footer.paragraphs:
                _process_paragraph(para, stats, audit_log, f"Footer (section {s_idx+1})")

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return stats, sum(stats.values()), buf.read(), audit_log


# ── Routes ──────────────────────────────────────────────────
@api_router.get("/")
async def root():
    return {"message": "RedactAI API is running"}


@api_router.post("/redact")
async def redact_document(file: UploadFile = File(...)):
    fname = (file.filename or "").lower()
    if not (fname.endswith(".docx") or fname.endswith(".doc")):
        raise HTTPException(status_code=400, detail="Only .doc and .docx files are supported")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB.")

    try:
        # Convert legacy .doc → .docx when needed
        if fname.endswith(".doc") and not fname.endswith(".docx"):
            content = convert_doc_to_docx(content)

        stats, total, redacted_bytes, audit_log = process_document(content)
    except Exception as exc:
        logger.error("Document processing failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}")

    original_stem = (file.filename or "document").rsplit(".", 1)[0]
    return {
        "stats": stats,
        "total": total,
        "file_base64": base64.b64encode(redacted_bytes).decode("utf-8"),
        "filename": f"redacted_{original_stem}.docx",
        "audit_log": audit_log,
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
