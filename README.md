# PII-Redactor

## Run with Docker

```bash
docker-compose up --build
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`

## Run without Docker (Windows)

Double-click `start_windows.bat`.

## Optional models

OpenNyAI Legal NER (optional):

```bash
pip install https://huggingface.co/opennyaiorg/en_legal_ner_trf/resolve/main/en_legal_ner_trf-any-py3-none-any.whl
```

IndicNER (optional):

```bash
pip install transformers torch
```

## User list files

- Always redact list: `backend/user_redact_list.txt`
- Never redact list: `backend/user_allow_list.txt`

One term per line. Lines beginning with `#` are ignored.

## Tests

```bash
cd backend
python test_full_pipeline.py
```
