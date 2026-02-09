from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.responses import Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
import io
import csv
import uuid
import time
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
from pii_engine import PIITracker, redact_text

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# MongoDB connection (optional; used for deployments that need persistence).
mongo_url = os.environ.get("MONGO_URL")
db_name = os.environ.get("DB_NAME")
client = None
db = None
if mongo_url and db_name:
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    logger.info("MongoDB client initialized for optional persistence.")

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# ── Temporary in-memory file store for reliable downloads ────
_file_store: Dict[str, dict] = {}
_FILE_TTL = 600  # 10 minutes


def _store_file(data: bytes, filename: str, audit_log: list, stats: dict, total: int) -> str:
    """Store file data and return a unique download ID."""
    _cleanup_expired()
    file_id = uuid.uuid4().hex
    _file_store[file_id] = {
        "data": data,
        "filename": filename,
        "audit_log": audit_log,
        "stats": stats,
        "total": total,
        "created": time.time(),
    }
    return file_id


def _cleanup_expired():
    now = time.time()
    expired = [k for k, v in _file_store.items() if now - v["created"] > _FILE_TTL]
    for k in expired:
        del _file_store[k]


# ── .doc → .docx conversion ─────────────────────────────────
def convert_doc_to_docx(doc_bytes: bytes) -> bytes:
    """Convert legacy .doc to .docx via antiword text extraction."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as tmp:
            tmp.write(doc_bytes)
            tmp_path = tmp.name

        env = {**os.environ, "HOME": "/tmp"}
        result = subprocess.run(
            ["antiword", tmp_path],
            capture_output=True, text=True, timeout=30, env=env,
        )
        if result.returncode != 0:
            # Fallback: try reading as plain text
            logger.warning("antiword failed, attempting plain-text fallback: %s", result.stderr.strip())
            try:
                text = doc_bytes.decode("utf-8", errors="ignore")
            except Exception:
                text = doc_bytes.decode("latin-1", errors="ignore")
        else:
            text = result.stdout

        doc = DocxDocument()
        for line in text.split("\n"):
            doc.add_paragraph(line)

        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return buf.read()
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ── Core redaction logic ────────────────────────────────────
def _process_paragraph(para, tracker: PIITracker, ctx: str):
    full_text = para.text
    if not full_text.strip():
        return
    new_text = redact_text(full_text, tracker, ctx)
    if new_text != full_text and para.runs:
        for i, run in enumerate(para.runs):
            run.text = new_text if i == 0 else ""


def process_document(doc_bytes: bytes):
    doc = DocxDocument(io.BytesIO(doc_bytes))
    tracker = PIITracker()
    para_num = 0

    # Paragraphs
    for para in doc.paragraphs:
        para_num += 1
        _process_paragraph(para, tracker, f"Paragraph {para_num}")

    # Tables (including nested)
    table_num = 0

    def _process_table(table, prefix=""):
        nonlocal table_num
        table_num += 1
        for r_idx, row in enumerate(table.rows):
            for c_idx, cell in enumerate(row.cells):
                ctx = f"{prefix}Table {table_num}, Row {r_idx+1}, Col {c_idx+1}"
                for para in cell.paragraphs:
                    _process_paragraph(para, tracker, ctx)
                for nested in cell.tables:
                    _process_table(nested, prefix=f"{ctx} > ")

    for table in doc.tables:
        _process_table(table)

    # Headers & footers
    for s_idx, section in enumerate(doc.sections):
        if section.header:
            for para in section.header.paragraphs:
                _process_paragraph(para, tracker, f"Header (section {s_idx+1})")
        if section.footer:
            for para in section.footer.paragraphs:
                _process_paragraph(para, tracker, f"Footer (section {s_idx+1})")

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return tracker.stats, tracker.total, buf.read(), tracker.audit_log


# ── Routes ──────────────────────────────────────────────────
@api_router.get("/")
async def root():
    return {"message": "RedactAI API is running"}


@api_router.get("/health")
async def health_check():
    if not client:
        return {"status": "ok", "mongo": "disabled"}
    try:
        await client.admin.command("ping")
    except Exception as exc:
        logger.warning("MongoDB ping failed: %s", exc)
        return {"status": "degraded", "mongo": "unavailable"}
    return {"status": "ok", "mongo": "connected"}


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
    filename = f"redacted_{original_stem}.docx"

    file_id = _store_file(redacted_bytes, filename, audit_log, stats, total)

    return {
        "stats": stats,
        "total": total,
        "file_id": file_id,
        "filename": filename,
        "audit_log": audit_log,
    }


@api_router.get("/download/{file_id}")
async def download_redacted(file_id: str):
    entry = _file_store.get(file_id)
    if not entry:
        raise HTTPException(status_code=404, detail="File expired or not found. Please re-process.")
    return Response(
        content=entry["data"],
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{entry["filename"]}"'},
    )


@api_router.get("/audit-csv/{file_id}")
async def download_audit_csv(file_id: str):
    entry = _file_store.get(file_id)
    if not entry:
        raise HTTPException(status_code=404, detail="File expired or not found. Please re-process.")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Category", "Placeholder", "Location"])
    for row in entry["audit_log"]:
        writer.writerow([row["category"], row["placeholder"], row["location"]])
    writer.writerow([])
    writer.writerow(["Summary"])
    writer.writerow(["Category", "Count"])
    for cat, count in sorted(entry["stats"].items(), key=lambda x: -x[1]):
        writer.writerow([cat, count])
    writer.writerow(["TOTAL", entry["total"]])

    csv_bytes = buf.getvalue().encode("utf-8")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="audit_{entry["filename"].replace(".docx", ".csv")}"'},
    )


@api_router.post("/audit-csv-batch")
async def download_batch_audit_csv(file_ids: List[str] = File(default=[])):
    """Generate a single audit CSV combining multiple processed files."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Document", "Category", "Placeholder", "Location"])

    for fid in file_ids:
        entry = _file_store.get(fid)
        if not entry:
            continue
        for row in entry["audit_log"]:
            writer.writerow([entry["filename"], row["category"], row["placeholder"], row["location"]])

    writer.writerow([])
    writer.writerow(["Summary"])
    writer.writerow(["Document", "Total PII", "Status"])
    for fid in file_ids:
        entry = _file_store.get(fid)
        if entry:
            writer.writerow([entry["filename"], entry["total"], "Success"])
        else:
            writer.writerow([fid, 0, "Expired/Not Found"])

    writer.writerow([])
    writer.writerow(["Category Breakdown"])
    writer.writerow(["Document", "Category", "Count"])
    for fid in file_ids:
        entry = _file_store.get(fid)
        if entry:
            for cat, count in sorted(entry["stats"].items(), key=lambda x: -x[1]):
                writer.writerow([entry["filename"], cat, count])

    csv_bytes = buf.getvalue().encode("utf-8")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="pii_audit_report.csv"'},
    )


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
    if client:
        client.close()
