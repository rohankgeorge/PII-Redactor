# RedactAI - Indian PII Redaction Tool

## Problem Statement
Build a redaction tool that receives Word documents (.docx), identifies Indian PII using rule-based detection, and replaces them with categorized placeholders. Designed to prepare documents for LLM processing.

## Architecture
- **Frontend**: React + Tailwind + Shadcn/UI (dark theme)
- **Backend**: FastAPI with python-docx for in-memory document processing
- **Database**: MongoDB (template requirement, no PII storage)

## User Persona
Indian professionals, legal teams, compliance officers preparing documents for LLM processing.

## Core Requirements
- Rule-based PII detection (regex + dictionary)
- 16 Indian PII categories: Aadhaar, PAN, Phone, Email, Passport, Voter ID, IFSC, GST, UPI, Vehicle Registration, Driving License, Bank Account, Address, PIN Code, Date of Birth, Names, Locations
- Categorized placeholders: [REDACTED_NAME], [REDACTED_AADHAAR_NUMBER], etc.
- Download redacted .docx file
- No data persistence — in-memory processing only

## What's Been Implemented (Feb 8, 2026)
- Full backend with comprehensive Indian PII regex patterns + name/location dictionaries
- Drag & drop file upload with .docx validation
- Processing state with scan animation
- Results panel with bento grid stats by PII category
- Download redacted document
- Start Over flow
- PII Types dropdown in header
- Privacy footer with assurance notices
- Dark professional theme with Chivo/Manrope/JetBrains Mono fonts
- All 15+ PII categories detected and tested

## Test Results
- Backend: 100% (5/5 tests)
- Frontend: 100% (all features working)
- Integration: 100% (seamless communication)

## Backlog
- P1: Add preview of redacted text before download
- P1: Support .doc (legacy Word) format
- P2: Batch upload multiple documents
- P2: Custom PII category toggle (enable/disable specific types)
- P2: Export PII audit report (PDF/CSV)
- P3: Browser-only mode (WebAssembly for fully client-side processing)
