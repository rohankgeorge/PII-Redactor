# RedactAI - Indian PII Redaction Tool

## Problem Statement
Build a redaction tool that receives Word documents (.docx/.doc), identifies all PII using rule-based detection, and replaces with uniquely numbered categorized placeholders. Designed to prepare documents for LLM processing.

## Architecture
- **Frontend**: React + Tailwind + Shadcn/UI (dark theme)
- **Backend**: FastAPI + python-docx + antiword + pii_engine.py (multi-pass redaction)
- **Database**: MongoDB (template, no PII storage)
- **Key file**: `/app/backend/pii_engine.py` - PIITracker + 6-pass redaction engine

## What's Been Implemented

### Phase 1: Initial Build (Feb 8, 2026)
- Basic PII detection (16 categories)
- Upload, processing, results, download flow
- Dark professional UI

### Phase 2: Feature Additions
- Download fix (iframe-based server-side downloads)
- PII Audit Report (CSV export)
- .doc legacy format support (antiword)
- Batch multi-file upload

### Phase 3: Redaction Engine Overhaul (Current)
- **PIITracker class**: Unique numbered placeholders per category ([REDACTED_INDIVIDUAL1], [REDACTED_ADDRESS2], etc.)
- **Entity name detection**: Private Limited, Pvt Ltd, LLP, Co, Ltd, Corporation + standalone entity references
- **Full address redaction**: Complete address blocks (number → PIN code) in single placeholder
- **Universal person names**: Title-based (Mr./Mrs./Dr.), context-based (Name:), consecutive capitalized words, dictionary
- **Handles**: D'Rozario, initials (N.), non-Indian names
- **Same person = same number**: "Mr. Dhwaj Bagrecha" and "Dhwaj Bagrecha" get same [REDACTED_INDIVIDUAL_] number
- **Processing order**: IDs → Addresses → Entities → PIN codes → Names → Locations
- **Year exclusion**: "2013" in "Companies Act, 2013" not confused with address

## Test Results
- All tests pass (100% frontend, integration, new features)

## Backlog
- P1: Entity aliasing ("NeoSan Private Limited" and "NeoSan Pvt Ltd" → same number)
- P2: Redacted text preview before download
- P2: Custom PII category toggle
