# Migrate PII-Redactor from Hardcoded Dictionaries to Hybrid NLP Pipeline

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. This document must be maintained in accordance with .agent/PLANS.md.


## Purpose / Big Picture

The PII-Redactor currently detects Indian person names, surnames, cities, and states using hardcoded Python sets of roughly 550 names and 170 locations. This means any name not in the list is missed entirely. After this change, the application will use spaCy NLP models to detect names and locations from context (the way a human reader would), supplemented by a large Indian name dataset of 28,000+ names loaded into a spaCy EntityRuler, further supplemented by user-supplied always-redact and never-redact lists. As a second pass, the OpenNyAI Legal NER model (trained specifically on Indian legal documents) and the IndicNER model (trained on 11 Indian languages) will catch additional entities.

After this change is complete, a user can: (1) paste text into the web frontend, (2) receive redacted output where names and locations are detected by NLP rather than dictionary lookup, (3) add custom names to an always-redact list and terms to a never-redact list, and (4) see redaction results that combine regex-based ID detection, spaCy NER, EntityRuler dictionary matching, OpenNyAI Legal NER, and IndicNER — all producing the same `[REDACTED_CATEGORY_N]` placeholder format.

The regex-based detection for structured Indian IDs (Aadhaar, PAN, GST, IFSC, phone numbers, email, UPI, bank accounts, driving licence, passport, voter ID, vehicle registration, PIN codes) is not touched by this plan. It remains exactly as-is.


## Progress

- [ ] Milestone 1: Core spaCy integration with EntityRuler, user lists, and allowlist.
- [ ] Milestone 2: OpenNyAI Legal NER and IndicNER as second-pass models.
- [ ] Milestone 3: Download and integrate large Indian name datasets into EntityRuler.
- [ ] Milestone 4: Hosting and end-to-end testing setup.


## Surprises & Discoveries

(To be updated as work proceeds.)


## Decision Log

- Decision: Feed large Indian name datasets into the spaCy EntityRuler, not into regex patterns and not by retraining models.
  Rationale: The EntityRuler is purpose-built for gazetteer-style matching within the spaCy pipeline. Regex is designed for structured patterns (Aadhaar, PAN) not name dictionaries. Retraining models requires annotated data and significant effort. The EntityRuler gives the same detection benefit with zero training.
  Date/Author: 2025-02-10 / Plan author.

- Decision: Keep all regex-based ID detection exactly as-is in pii_engine.py. Only the name-detection and location-detection passes are being replaced.
  Rationale: The regex patterns for Aadhaar, PAN, GST, IFSC, phone numbers, email, UPI, bank accounts, driving licence, passport, voter ID, vehicle registration, and PIN codes are correct and well-tested. Changing them would introduce risk with no benefit.
  Date/Author: 2025-02-10 / Plan author.

- Decision: Create a new file `backend/nlp_engine.py` for all NLP logic rather than modifying pii_engine.py heavily.
  Rationale: Isolating NLP logic in its own module means (a) pii_engine.py changes are minimal (just calling the new module instead of dictionary functions), (b) the new module can be tested independently, and (c) Milestone 2 additions (OpenNyAI, IndicNER) go into the same module without touching pii_engine.py again.
  Date/Author: 2025-02-10 / Plan author.

- Decision: The pipeline order is: (1) regex for structured IDs, (2) address detection, (3) entity/company detection, (4) spaCy NER + EntityRuler for names and locations, (5) OpenNyAI Legal NER second pass, (6) IndicNER second pass, (7) user always-redact list, (8) user never-redact list (restores false positives). This order ensures each layer only adds to what prior layers found, and the never-redact list runs last so it can override everything.
  Rationale: Running user never-redact last is critical because it must be able to undo false positives from any prior layer. Running user always-redact before never-redact ensures that if a term appears on both lists, the never-redact wins (which is the safer default — if someone explicitly says "do not redact this," that should take priority).
  Date/Author: 2025-02-10 / Plan author.

- Decision: Use spaCy `en_core_web_sm` (small English model, roughly 12 MB) as the default model, not `en_core_web_trf` (transformer model, roughly 500 MB + PyTorch).
  Rationale: The small model is fast, lightweight, and sufficient for most name detection. The transformer model requires PyTorch (2+ GB) which complicates installation for a beginner and makes standalone packaging impractical. Users who want higher accuracy can switch to `en_core_web_trf` by changing one line of configuration.
  Date/Author: 2025-02-10 / Plan author.

- Decision: Store user always-redact and never-redact lists as plain text files (`backend/user_redact_list.txt` and `backend/user_allow_list.txt`), one entry per line.
  Rationale: Simplest possible format. No database, no JSON parsing, no frontend changes needed. Users can edit these files with Notepad. A future milestone could add a frontend UI for managing these lists, but that is out of scope for this plan.
  Date/Author: 2025-02-10 / Plan author.


## Outcomes & Retrospective

(To be updated at completion of each milestone and at final completion.)


## Context and Orientation

The repository is at https://github.com/rohankgeorge/PII-Redactor on the `Adding-Spacy-and-Indian-NER` branch. It is a web application with:

- `backend/pii_engine.py` — The main redaction engine. It contains a `PIITracker` class that assigns unique numbered placeholders like `[REDACTED_INDIVIDUAL1]`, and a `redact_text()` function that runs sequential detection passes: (1) regex for IDs, (2) address detection, (3) entity/company detection, (4) name detection via dictionary matching, (5) location detection via dictionary matching. Each pass calls `tracker.placeholder(category, original, context)` to register and replace detected PII.

- `backend/indian_pii_data.py` — Contains: `PII_REGEX_PATTERNS` (a list of compiled regex patterns for Indian IDs), `INDIAN_FIRST_NAMES` (a set of roughly 300 Indian first names as title-cased strings), `INDIAN_SURNAMES` (a set of roughly 250 Indian surnames), `INDIAN_CITIES` (a set of roughly 90 Indian city names), `INDIAN_STATES` (a set of Indian state and union territory names).

- `backend/` — Also contains the backend server file(s) that expose an API to the frontend. The exact file may be `app.py`, `main.py`, or `server.py`. Examine the directory listing to determine which file runs the server.

- `frontend/` — A JavaScript/HTML/CSS frontend that sends text to the backend API and displays redacted output. The frontend does not need to change for any milestone in this plan.

The critical functions being modified are `_redact_names()` and `_redact_locations()` in `backend/pii_engine.py`. These currently use dictionary-based matching via compiled regex patterns built from `INDIAN_FIRST_NAMES`, `INDIAN_SURNAMES`, `INDIAN_CITIES`, and `INDIAN_STATES`. After the migration, these functions will call into the new `backend/nlp_engine.py` module instead.

Key terms used in this plan:

- "NER" (Named Entity Recognition): The task of identifying named entities (people, places, organisations, dates) in text. spaCy's NER component does this using a statistical model trained on labelled text.

- "EntityRuler" (also called SpanRuler in newer spaCy versions): A spaCy pipeline component that matches entities from a list of patterns (like a dictionary). It runs alongside the statistical NER model. It does not learn or generalise — it matches exactly what is in its pattern list.

- "spaCy pipeline": When you call `nlp(text)` in spaCy, the text passes through a sequence of components (tokenizer, tagger, parser, NER, EntityRuler, etc.). Each component annotates the text. At the end, `doc.ents` contains all detected entities from all components.

- "OpenNyAI Legal NER" (`en_legal_ner_trf`): A spaCy-compatible NER model trained by the OpenNyAI project specifically on Indian court judgments. It detects entity types like PETITIONER, RESPONDENT, JUDGE, LAWYER, COURT, STATUTE, PROVISION, PRECEDENT, DATE. It is Apache 2.0 licensed and installable via pip from Hugging Face.

- "IndicNER" (`ai4bharat/IndicNER`): A Hugging Face transformer model trained on 11 Indian languages (Assamese, Bengali, Gujarati, Hindi, Kannada, Malayalam, Marathi, Oriya, Punjabi, Tamil, Telugu). It is a BERT-based model, not a spaCy pipeline, so it requires a small adapter to integrate. It is useful for documents that contain Indian-language text in native scripts. It is openly available on Hugging Face.

- "PIITracker": The class in `pii_engine.py` that maintains a registry of detected PII values and assigns unique numbered placeholders. All detection methods must call `tracker.placeholder(category, original, context)` to register their finds. This ensures consistent numbering across all detection methods.

- "Allowlist" / "Never-redact list": A list of terms that should never be redacted even if a model flags them. For example, "Supreme Court" or "Reserve Bank of India" might be detected as entities but should not be redacted.

- "Always-redact list" / "User-supplied name list": A list of terms that should always be redacted regardless of whether any model detects them. For example, a specific person's name that spaCy misses.


## Plan of Work


### Milestone 1: Core spaCy Integration, EntityRuler Fallback, User Lists

This milestone replaces the dictionary-based name and location detection with spaCy NER plus an EntityRuler loaded with the existing 550-name dictionary from `indian_pii_data.py`. It also adds user-supplied always-redact and never-redact lists. At the end of this milestone, the application works exactly as before from the user's perspective (same input, same placeholder format, same API) but names and locations are detected by spaCy plus EntityRuler instead of pure dictionary matching.

The changes are:

1. Add `spacy` and `en_core_web_sm` to `backend/requirements.txt`. If `requirements.txt` does not exist, create it.

2. Create `backend/nlp_engine.py` with the following structure:

   - A module-level function `load_nlp_pipeline()` that: (a) loads the `en_core_web_sm` model, (b) adds a SpanRuler (or EntityRuler, depending on spaCy version — check `spacy.__version__` and use `SpanRuler` if spaCy >= 3.3, otherwise `EntityRuler`) to the pipeline before the NER component, (c) loads the existing `INDIAN_FIRST_NAMES` and `INDIAN_SURNAMES` from `indian_pii_data.py` as PERSON patterns and `INDIAN_CITIES` and `INDIAN_STATES` as GPE/LOC patterns into the ruler, (d) returns the loaded `nlp` object. This function must be called once at server startup, not on every request.

   - A function `detect_names_and_locations(text: str, nlp) -> list[dict]` that: (a) runs `doc = nlp(text)`, (b) iterates over `doc.ents`, (c) for each entity with label PERSON, ORG, GPE, LOC, or NORP, returns a list of dicts with keys `{"start": int, "end": int, "text": str, "label": str}`. The `start` and `end` are character offsets in the original text.

   - A function `load_user_list(filepath: str) -> set[str]` that reads a plain text file (one entry per line, stripping whitespace, ignoring blank lines and lines starting with #) and returns a set of strings. If the file does not exist, return an empty set.

   - A function `apply_user_always_redact(text: str, always_redact: set[str], tracker: PIITracker, context: str) -> str` that: for each term in the always-redact set, finds all case-insensitive occurrences in the text that are not already inside a `[REDACTED_...]` placeholder, and replaces them using `tracker.placeholder("INDIVIDUAL", term, context)`.

   - A function `apply_user_never_redact(text: str, never_redact: set[str]) -> str` that: for each term in the never-redact set, finds all `[REDACTED_..._N]` placeholders in the text, checks if the original value (stored in the tracker) matches any never-redact term (case-insensitive), and if so, restores the original text. This requires the PIITracker to store a reverse mapping from placeholder back to original value. If implementing the reverse lookup is complex, an alternative approach is: before running any redaction, pre-scan the text and wrap never-redact terms in a protective marker (e.g., `__PROTECTED_0__`), run all redaction passes, then unwrap the protective markers back to the original terms. This approach is simpler and more robust. Use the protective-marker approach.

3. Modify the `PIITracker` class in `backend/pii_engine.py`:

   - No structural changes needed if using the protective-marker approach for never-redact.

4. Modify `backend/pii_engine.py`:

   - In the `_redact_names()` function: replace the four sub-passes (title-based, context-based, consecutive-capitalized, dictionary-based) with a single call to `nlp_engine.detect_names_and_locations()`. For each detected entity, call `tracker.placeholder()` with category "INDIVIDUAL" for PERSON entities and "LOCATION" for GPE/LOC entities. Preserve the `_is_inside_placeholder()` check so that entities detected inside already-redacted regions are skipped.

   - In the `_redact_locations()` function: this function can be simplified to a no-op or removed entirely, because location detection is now handled by the spaCy call in the modified `_redact_names()` function. If removing it, also remove its call in `redact_text()`.

   - In the `redact_text()` function: before any redaction passes, call `nlp_engine.apply_user_never_redact()` to wrap protected terms. After all redaction passes, unwrap the protected terms. Add a call to `nlp_engine.apply_user_always_redact()` after the NLP name pass but before unwrapping protected terms.

   - Import `nlp_engine` at the top of the file.

   - The `nlp` object must be loaded once (at module import time or via a lazy singleton) and passed to the detection function. Do not reload the model on every call to `redact_text()`.

5. Create `backend/user_redact_list.txt` with a comment header explaining the format:

       # Always-redact list: one name or term per line.
       # These terms will be redacted even if no NLP model detects them.
       # Lines starting with # are comments and are ignored.

6. Create `backend/user_allow_list.txt` with a comment header explaining the format:

       # Never-redact list (allowlist): one term per line.
       # These terms will never be redacted even if a model flags them.
       # Lines starting with # are comments and are ignored.

7. Do NOT delete `INDIAN_FIRST_NAMES`, `INDIAN_SURNAMES`, `INDIAN_CITIES`, or `INDIAN_STATES` from `indian_pii_data.py`. They are still used — they are loaded into the EntityRuler in step 2. They will also be used in Milestone 3 when the larger dataset is merged with them. Do NOT delete any regex patterns from `PII_REGEX_PATTERNS`. Do NOT modify any regex-based detection functions (`_redact_pre_address_ids`, `_redact_post_address_ids`, `_redact_addresses`, `_redact_entities`).

8. Update the backend server file (identify it by examining the `backend/` directory — it is likely `app.py`, `main.py`, or `server.py`) to call `nlp_engine.load_nlp_pipeline()` once at startup and store the resulting `nlp` object where `redact_text()` can access it (either as a module-level variable in `nlp_engine.py` or passed explicitly).

Validation for Milestone 1: After completing all changes, run the following test from the repository root:

    cd backend
    python -c "
    from pii_engine import PIITracker, redact_text
    tracker = PIITracker()
    sample = 'Mr. Rajesh Sharma lives in Bangalore and his Aadhaar is 2345 6789 0123.'
    result = redact_text(sample, tracker)
    print(result)
    print('Stats:', tracker.stats)
    assert '[REDACTED_' in result
    assert 'AADHAAR_NUMBER' in str(tracker.stats)
    print('Milestone 1 basic test PASSED')
    "

Also verify the server starts and the frontend can send text and receive redacted output. Start the backend (e.g., `python app.py`), start the frontend (`cd frontend && npm start`), open the browser, paste sample text, and confirm redacted output appears with `[REDACTED_...]` placeholders.


### Milestone 2: OpenNyAI Legal NER and IndicNER as Second-Pass Models

This milestone adds two additional NER models that run as a second pass after the core spaCy pipeline. Their purpose is to catch entities that spaCy's general English model misses, particularly in legal documents (OpenNyAI) and documents containing Indian-language text (IndicNER). These models add to the detections from Milestone 1 — they never remove or override prior detections.

The changes are:

1. Add dependencies to `backend/requirements.txt`:
   - The OpenNyAI model: add a comment and the pip URL. The install command is: `pip install https://huggingface.co/opennyaiorg/en_legal_ner_trf/resolve/main/en_legal_ner_trf-any-py3-none-any.whl`. This model depends on `spacy-transformers` and `torch`, which are large dependencies (2+ GB). Because of this, make the OpenNyAI model optional — it should be loaded only if it is installed, and the application should work without it.
   - For IndicNER: add `transformers` and `torch` to requirements.txt. Like OpenNyAI, make IndicNER optional.

2. In `backend/nlp_engine.py`, add:

   - A function `load_legal_ner()` that attempts to load the `en_legal_ner_trf` model via `spacy.load("en_legal_ner_trf")`. Wrap the import in a try/except: if the model is not installed, print a warning message ("OpenNyAI Legal NER not installed — skipping. Install with: pip install <URL>") and return None.

   - A function `load_indic_ner()` that attempts to load the IndicNER model from Hugging Face using `transformers.pipeline("ner", model="ai4bharat/IndicNER")`. Wrap in try/except: if transformers or the model is not available, print a warning and return None.

   - A function `detect_with_legal_ner(text: str, legal_nlp) -> list[dict]` that runs the OpenNyAI model on the text and returns detected entities in the same format as `detect_names_and_locations()`. Map OpenNyAI entity labels to PII categories as follows: PETITIONER, RESPONDENT, JUDGE, LAWYER, WITNESS, OTHER_PERSON -> "INDIVIDUAL". COURT -> "ENTITY". GPE -> "LOCATION". All other labels (STATUTE, PROVISION, PRECEDENT, DATE, CASE_NUMBER, ORG) -> skip (do not redact these, as they are typically not PII).

   - A function `detect_with_indic_ner(text: str, indic_pipeline) -> list[dict]` that runs the IndicNER pipeline on the text and returns detected entities. Map labels: PER -> "INDIVIDUAL". LOC -> "LOCATION". ORG -> "ENTITY".

   - A function `run_second_pass(text: str, tracker: PIITracker, legal_nlp, indic_pipeline, context: str) -> str` that: (a) runs `detect_with_legal_ner()` if legal_nlp is not None, (b) runs `detect_with_indic_ner()` if indic_pipeline is not None, (c) for each detected entity that is not already inside a `[REDACTED_...]` placeholder (use `_is_inside_placeholder()`), calls `tracker.placeholder()` to redact it, (d) returns the modified text. Entities must be replaced in reverse order of their position (highest offset first) to avoid shifting character positions.

3. In `backend/pii_engine.py`, modify `redact_text()`:

   - After the existing NLP name pass (from Milestone 1) and before the user always-redact pass, add a call to `nlp_engine.run_second_pass()`.

   - The pipeline order in `redact_text()` after both milestones is now:
     (a) Protect never-redact terms.
     (b) Regex for structured IDs (`_redact_pre_address_ids`).
     (c) Address detection (`_redact_addresses`).
     (d) Entity/company detection (`_redact_entities`).
     (e) Regex PIN codes (`_redact_post_address_ids`).
     (f) spaCy NER + EntityRuler for names and locations (Milestone 1).
     (g) OpenNyAI Legal NER second pass (Milestone 2, if model installed).
     (h) IndicNER second pass (Milestone 2, if model installed).
     (i) User always-redact list.
     (j) Unprotect never-redact terms.

4. Update the backend server startup to also call `load_legal_ner()` and `load_indic_ner()` and store the results. Pass them to `redact_text()` or store them as module-level variables in `nlp_engine.py`.

5. Do NOT modify any code from Milestone 1. The second-pass models are purely additive.

Validation for Milestone 2: Run the basic test from Milestone 1 — it must still pass (regression check). Then run:

    cd backend
    python -c "
    from nlp_engine import load_legal_ner, load_indic_ner
    legal = load_legal_ner()
    indic = load_indic_ner()
    if legal is None:
        print('OpenNyAI Legal NER not installed (OK — it is optional)')
    else:
        print('OpenNyAI Legal NER loaded successfully')
    if indic is None:
        print('IndicNER not installed (OK — it is optional)')
    else:
        print('IndicNER loaded successfully')
    print('Milestone 2 test PASSED')
    "

If the optional models are installed, also test with a legal text sample:

    cd backend
    python -c "
    from pii_engine import PIITracker, redact_text
    tracker = PIITracker()
    sample = 'The petitioner Smt. Kamala Devi filed a case against respondent Shri T.R. Ajayan in the High Court of Kerala at Ernakulam.'
    result = redact_text(sample, tracker)
    print(result)
    print('Stats:', tracker.stats)
    print('Milestone 2 legal text test PASSED')
    "


### Milestone 3: Large Indian Name Datasets in EntityRuler

This milestone downloads publicly available Indian name datasets and loads them into the spaCy EntityRuler created in Milestone 1, expanding the name dictionary from roughly 550 names to 28,000+ names. This dramatically improves recall for uncommon Indian names that neither the spaCy statistical model nor the OpenNyAI model would catch.

The changes are:

1. Download the following datasets and save them in a new directory `backend/name_data/`:

   - Indian male names (roughly 14,000 names): from the GitHub Gist at https://gist.github.com/mbejda/7f86ca901fe41bc14a63 — save as `backend/name_data/indian_male_names.csv`.
   - Indian female names (roughly 14,000 names): from the corresponding GitHub Gist by the same author (search for "Indian-Female-Names.csv" by mbejda) — save as `backend/name_data/indian_female_names.csv`.
   - Indian surnames: from https://github.com/merishnaSuwal/indian_surnames_data — save the CSV as `backend/name_data/indian_surnames.csv`.

   If any of these URLs are unavailable at the time of implementation, search for alternative Indian name datasets on GitHub or Kaggle and document the substitution in the Decision Log.

2. Create `backend/name_data/load_names.py` with:

   - A function `load_all_indian_names() -> tuple[set[str], set[str]]` that: (a) reads all three CSV files, (b) extracts name columns (the CSV format is typically: name, gender, race — extract only the name column), (c) cleans names: strip whitespace, title-case each name, remove entries shorter than 3 characters (to avoid noise), remove entries that are common English words (maintain a small stoplist: "The", "And", "For", "New", "Old", "East", "West", "North", "South", etc.), (d) merges the male and female names into a single `first_names` set, (e) returns `(first_names, surnames)`.

   - A function `merge_with_existing(new_firsts: set[str], new_surnames: set[str]) -> tuple[set[str], set[str]]` that: (a) imports `INDIAN_FIRST_NAMES` and `INDIAN_SURNAMES` from `indian_pii_data.py`, (b) unions the existing sets with the new sets, (c) returns the merged sets.

3. In `backend/nlp_engine.py`, modify `load_nlp_pipeline()`:

   - After loading the existing names from `indian_pii_data.py` into the EntityRuler (Milestone 1 step 2c), also call `load_names.load_all_indian_names()` and `merge_with_existing()` to get the expanded name sets, and add the additional names as PERSON patterns to the EntityRuler.

   - Log the count of patterns loaded: "EntityRuler loaded with {N} first name patterns and {M} surname patterns."

4. Do NOT modify `indian_pii_data.py`. The original sets remain as-is. The new data is additive.

5. Do NOT modify any regex patterns or any code from Milestones 1 or 2. The only change is to the `load_nlp_pipeline()` function in `nlp_engine.py`, which now loads more patterns into the EntityRuler.

Validation for Milestone 3: Run the Milestone 1 basic test — it must still pass. Then run:

    cd backend
    python -c "
    from nlp_engine import load_nlp_pipeline
    nlp = load_nlp_pipeline()
    # Test with uncommon Indian names not in the original 550-name dictionary
    doc = nlp('Brijesh Kacholia met with Thekkethalackal Varghese at the cafe.')
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    print('Detected entities:', entities)
    print('Milestone 3 test PASSED')
    "


### Milestone 4: Hosting and End-to-End Testing

This milestone sets up the easiest, lowest-friction way to run and test the entire application. The recommended approach is a Docker Compose configuration that starts both backend and frontend with a single command. As a fallback for users who do not want Docker, a simple startup script for Windows is also provided.

The changes are:

1. Create `Dockerfile.backend` in the repository root:

       FROM python:3.11-slim
       WORKDIR /app
       COPY backend/ ./backend/
       COPY backend/requirements.txt ./
       RUN pip install --no-cache-dir -r requirements.txt
       RUN python -m spacy download en_core_web_sm
       WORKDIR /app/backend
       # The CMD must match the actual server file — examine the backend directory to determine the correct command.
       # It will be one of: CMD ["python", "app.py"] or CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
       EXPOSE 8000

2. Create `Dockerfile.frontend` in the repository root:

       FROM node:18-slim
       WORKDIR /app
       COPY frontend/ ./
       RUN npm install
       EXPOSE 3000
       CMD ["npm", "start"]

3. Create `docker-compose.yml` in the repository root:

       version: '3.8'
       services:
         backend:
           build:
             context: .
             dockerfile: Dockerfile.backend
           ports:
             - "8000:8000"
         frontend:
           build:
             context: .
             dockerfile: Dockerfile.frontend
           ports:
             - "3000:3000"
           depends_on:
             - backend

   Adjust ports to match what the backend and frontend actually use (examine their configuration files to determine the correct ports).

4. Create `start_windows.bat` in the repository root as a fallback for users without Docker:

       @echo off
       echo === PII Redactor Startup ===
       echo.
       echo Starting backend...
       start "PII-Backend" cmd /k "cd backend && pip install -r requirements.txt && python -m spacy download en_core_web_sm && python app.py"
       echo Waiting 15 seconds for backend to start...
       timeout /t 15 /nobreak
       echo.
       echo Starting frontend...
       start "PII-Frontend" cmd /k "cd frontend && npm install && npm start"
       echo.
       echo === Both services starting. Check the two new terminal windows. ===
       echo === Frontend will be at http://localhost:3000 (or similar) ===
       pause

   Adjust the `python app.py` command to match the actual backend server file.

5. Create `backend/test_full_pipeline.py` — a comprehensive end-to-end test script:

       """End-to-end test for the full PII redaction pipeline."""
       from pii_engine import PIITracker, redact_text

       test_cases = [
           {
               "name": "Aadhaar detection (regex)",
               "input": "My Aadhaar number is 2345 6789 0123",
               "must_contain": "[REDACTED_AADHAAR_NUMBER",
               "must_not_contain": "2345",
           },
           {
               "name": "PAN detection (regex)",
               "input": "PAN: ABCDE1234F",
               "must_contain": "[REDACTED_PAN_NUMBER",
               "must_not_contain": "ABCDE1234F",
           },
           {
               "name": "Name detection (NLP)",
               "input": "Mr. Rajesh Sharma attended the meeting",
               "must_contain": "[REDACTED_INDIVIDUAL",
               "must_not_contain": None,
           },
           {
               "name": "Location detection (NLP)",
               "input": "The office is located in Bangalore, Karnataka",
               "must_contain": "[REDACTED_LOCATION",
               "must_not_contain": None,
           },
           {
               "name": "Email detection (regex)",
               "input": "Contact me at test.user@example.com",
               "must_contain": "[REDACTED_EMAIL",
               "must_not_contain": "test.user@example.com",
           },
           {
               "name": "Phone detection (regex)",
               "input": "Call me at +91 98765 43210",
               "must_contain": "[REDACTED_PHONE_NUMBER",
               "must_not_contain": "98765",
           },
       ]

       passed = 0
       failed = 0
       for tc in test_cases:
           tracker = PIITracker()
           result = redact_text(tc["input"], tracker)
           ok = True
           if tc["must_contain"] and tc["must_contain"] not in result:
               print(f"FAIL: {tc['name']} — expected '{tc['must_contain']}' in result")
               print(f"  Got: {result}")
               ok = False
           if tc["must_not_contain"] and tc["must_not_contain"] in result:
               print(f"FAIL: {tc['name']} — did not expect '{tc['must_not_contain']}' in result")
               print(f"  Got: {result}")
               ok = False
           if ok:
               print(f"PASS: {tc['name']}")
               passed += 1
           else:
               failed += 1

       print(f"\n{passed} passed, {failed} failed out of {len(test_cases)} tests.")

   Run this test with:

       cd backend
       python test_full_pipeline.py

   Expected output: all tests pass. If name/location tests fail, it indicates the spaCy integration from Milestone 1 is not working correctly.

6. Add a `README.md` section (or update the existing README.md) documenting:
   - How to install and run with Docker: `docker-compose up --build`
   - How to install and run without Docker: double-click `start_windows.bat`
   - How to install the optional OpenNyAI and IndicNER models
   - How to edit the always-redact and never-redact lists
   - How to run the test suite

Validation for Milestone 4: Run `docker-compose up --build` (if Docker is available) or `start_windows.bat` and verify: (a) the backend starts without errors, (b) the frontend loads in a browser, (c) pasting sample text with Indian PII produces redacted output, (d) `python test_full_pipeline.py` passes all tests.


## Concrete Steps

(These correspond to the milestones above. Update this section with exact commands and outputs as work proceeds.)

Step 1: Create a git checkpoint before starting.

    git checkout Adding-Spacy-and-Indian-NER

Step 2: Examine the backend directory to identify the server file and understand the current structure.

    ls backend/

Step 3: Implement Milestone 1. Commit.

    git add -A && git commit -m "Milestone 1: spaCy NER integration with EntityRuler, user lists, and allowlist"

Step 4: Implement Milestone 2. Commit.

    git add -A && git commit -m "Milestone 2: OpenNyAI Legal NER and IndicNER as optional second-pass models"

Step 5: Implement Milestone 3. Commit.

    git add -A && git commit -m "Milestone 3: Large Indian name datasets loaded into EntityRuler"

Step 6: Implement Milestone 4. Commit.

    git add -A && git commit -m "Milestone 4: Docker setup, Windows startup script, and end-to-end tests"

Step 7: Run the full test suite and verify everything works.

    cd backend
    python test_full_pipeline.py


## Validation and Acceptance

The migration is complete when all of the following are true:

1. The full test suite (`backend/test_full_pipeline.py`) passes all tests.
2. Regex-based ID detection (Aadhaar, PAN, GST, IFSC, phone, email, UPI, bank account, driving licence, passport, voter ID, vehicle registration, PIN code) continues to work identically to before.
3. Name detection catches names that were in the original dictionary AND names that were not (demonstrating that NLP generalisation works).
4. The application starts and runs via either Docker or the Windows startup script.
5. The frontend sends text and receives redacted output without any frontend code changes.
6. The user_redact_list.txt and user_allow_list.txt files are functional (adding a name to user_redact_list.txt causes it to be redacted; adding a term to user_allow_list.txt prevents it from being redacted).


## Idempotence and Recovery

Each milestone can be retried by reverting to the git checkpoint created at the start of that milestone. The milestones are cumulative but each commit is a safe rollback point. The `feature/nlp-migration` branch preserves the original `Post-Emergent-2nd-Pass` branch untouched.

If `pip install` or `npm install` fails partway, they can be re-run safely — both are idempotent.

If a spaCy model download fails (`python -m spacy download en_core_web_sm`), it can be re-run safely.


## Artifacts and Notes

(To be updated with transcripts, diffs, or snippets as work proceeds.)


## Interfaces and Dependencies

Libraries to install:

- `spacy` (version >= 3.3) — core NLP library. Install via: `pip install spacy`
- `en_core_web_sm` — spaCy's small English model. Install via: `python -m spacy download en_core_web_sm`
- `en_legal_ner_trf` (optional) — OpenNyAI Legal NER. Install via: `pip install https://huggingface.co/opennyaiorg/en_legal_ner_trf/resolve/main/en_legal_ner_trf-any-py3-none-any.whl`
- `transformers` (optional) — Hugging Face transformers library, needed for IndicNER. Install via: `pip install transformers`
- `torch` (optional) — PyTorch, needed by both `en_legal_ner_trf` and IndicNER. Install via: `pip install torch`

Files created by this plan:

- `backend/nlp_engine.py` — New module containing all NLP detection logic.
- `backend/user_redact_list.txt` — User-editable always-redact list.
- `backend/user_allow_list.txt` — User-editable never-redact list.
- `backend/name_data/indian_male_names.csv` — Downloaded dataset.
- `backend/name_data/indian_female_names.csv` — Downloaded dataset.
- `backend/name_data/indian_surnames.csv` — Downloaded dataset.
- `backend/name_data/load_names.py` — Dataset loading and cleaning module.
- `backend/test_full_pipeline.py` — End-to-end test script.
- `Dockerfile.backend` — Backend Docker configuration.
- `Dockerfile.frontend` — Frontend Docker configuration.
- `docker-compose.yml` — Multi-service Docker configuration.
- `start_windows.bat` — Windows startup script (no Docker required).

Files modified by this plan:

- `backend/pii_engine.py` — Modified: `_redact_names()` refactored to call `nlp_engine`, `_redact_locations()` simplified or removed, `redact_text()` updated with new pipeline order including second-pass models and user lists.
- `backend/requirements.txt` — Modified or created: added spacy and optional dependencies.
- `README.md` — Updated with new installation and usage instructions.

Files NOT modified by this plan:

- `backend/indian_pii_data.py` — Unchanged. Regex patterns, name sets, city sets, and state sets remain as-is.
- All frontend files — Unchanged.
- `backend_test.py` — Unchanged (though it should still pass).

Key function signatures that must exist at the end of the plan:

In `backend/nlp_engine.py`:

    def load_nlp_pipeline() -> spacy.language.Language
    def detect_names_and_locations(text: str, nlp) -> list[dict]
    def load_user_list(filepath: str) -> set[str]
    def apply_user_always_redact(text: str, always_redact: set[str], tracker, context: str) -> str
    def protect_never_redact_terms(text: str, never_redact: set[str]) -> tuple[str, dict]
    def unprotect_never_redact_terms(text: str, protection_map: dict) -> str
    def load_legal_ner() -> Optional[spacy.language.Language]
    def load_indic_ner() -> Optional[Any]
    def detect_with_legal_ner(text: str, legal_nlp) -> list[dict]
    def detect_with_indic_ner(text: str, indic_pipeline) -> list[dict]
    def run_second_pass(text: str, tracker, legal_nlp, indic_pipeline, context: str) -> str

In `backend/name_data/load_names.py`:

    def load_all_indian_names() -> tuple[set[str], set[str]]
    def merge_with_existing(new_firsts: set[str], new_surnames: set[str]) -> tuple[set[str], set[str]]
