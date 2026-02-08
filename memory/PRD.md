# RedactAI - Indian PII Redaction Tool

## Problem Statement
Build a redaction tool that receives Word documents (.docx/.doc), identifies Indian PII using rule-based detection, and replaces them with categorized placeholders. Designed to prepare documents for LLM processing.

## Architecture
- **Frontend**: React + Tailwind + Shadcn/UI (dark theme)
- **Backend**: FastAPI with python-docx + antiword for document processing
- **Database**: MongoDB (template requirement, no PII storage)

## What's Been Implemented (Feb 8, 2026)

### Phase 1 (Initial Build)
- Full backend with 16 Indian PII regex patterns + name/location dictionaries
- Drag & drop file upload with .docx validation
- Processing state with scan animation
- Results panel with bento grid stats by category
- Download redacted document, Start Over flow
- PII Types dropdown in header, Privacy footer
- Dark professional theme

### Phase 2 (Feature Additions)
- **Download fix**: Added setTimeout before URL revocation for reliable downloads
- **PII Audit Report**: CSV export with per-detection log, summary, and category breakdown
- **.doc support**: Legacy .doc files handled via antiword + plaintext fallback
- **Batch upload**: Multiple files processed in parallel via Promise.allSettled
- **Per-file breakdown**: Individual download buttons and PII counts per file
- **Combined stats**: Aggregated stats across all uploaded documents

## Test Results
- Backend: 100% (7/7 tests)
- Frontend: 100% (all features)
- Integration: 100%

## Backlog
- P1: Add preview of redacted text before download
- P2: Custom PII category toggle (enable/disable specific types)
- P2: Drag-to-reorder PII priority
- P3: Browser-only mode (WebAssembly for fully client-side processing)
