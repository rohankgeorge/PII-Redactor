# Implementation Plan: LangExtract + RLM Integration Branch

Branch name: `feature/langextract-integration`

Base repo: `github.com/rohankgeorge/RLM-Legal-Implementation`

## Purpose

Integrate Google LangExtract as a structured extraction layer into the existing RLM Legal Document Query Tool, enabling grounded entity extraction at ingestion time and citation-aware query responses for both open-ended and closed-ended legal queries across heterogeneous document sets.

---

## Constraints and Dependencies

### Library capabilities to account for

**alexzhang13/rlm (v1.0.0, used by this repo)**

- RLM operates in a persistent Python REPL where the LLM writes and executes code.
- The local REPL (`LocalREPL`) shares the host process virtual environment; any installed package is importable.
- Sub-LLM calls are supported natively via `other_backends` and `other_backend_kwargs` parameters.
- `RLM.completion(prompt, root_prompt)` is the query interface. `prompt` holds the context; `root_prompt` holds the user query.
- The `RLMLogger` produces `.jsonl` files with per-iteration traces including `model_response`, `code_blocks`, `sub_llm_calls`, and `final_answer`.
- REPL output is truncated to ~8,192 characters per iteration by default; large LangExtract outputs will need summarisation before printing.
- Supports OpenAI, Anthropic, Gemini, OpenRouter, Portkey, LiteLLM, vLLM backends.

**google/langextract (v1.1.1)**

- Core function: `lx.extract(text_or_documents, prompt_description, examples, model_id, ...)`.
- Returns annotated documents with `Extraction` objects containing `extraction_class`, `extraction_text`, `attributes`, and `char_interval` (start, end character offsets).
- Few-shot examples are defined via `lx.data.ExampleData` with `lx.data.Extraction` objects. The schema is enforced by controlled generation (Gemini) or fence output (OpenAI).
- Supports Gemini (recommended, controlled generation), OpenAI (requires `fence_output=True`, `use_schema_constraints=False`), and Ollama (local).
- Long document handling: configurable `max_char_buffer` (chunk size), `extraction_passes` (multi-pass for recall), `max_workers` (parallel processing).
- Output saved via `lx.io.save_annotated_documents()` as `.jsonl`; visualisation via `lx.visualize()` producing self-contained HTML.
- API key: uses `LANGEXTRACT_API_KEY` environment variable, or `api_key` parameter, or Vertex AI service accounts.
- Apache 2.0 license (compatible with MIT).

**ysz/recursive-llm (reference only, not a dependency)**

- Uses LiteLLM for universal provider support and RestrictedPython for safe code execution.
- Simpler API: `RLM(model=...).completion(query, context)`.
- Useful reference for the two-model cost optimisation pattern (`model` for root, `recursive_model` for sub-calls) and the `FINAL(answer)` parsing pattern.
- Not published on PyPI; install from source only. 39 stars, 3 commits. Use for ideas, not as a dependency.

### Existing repo structure to preserve

The current repo has a clean separation: `app.py` (GUI wiring), `workers.py` (background threads), `query.py` (CLI), `chat_frame.py` (UI), `config_frame.py` (settings), `file_frame.py` (file selection), `constants.py` (theme/config), `log_viewer.py` (execution traces). All new code should respect this separation and avoid modifying existing interfaces unless necessary.

---

## Phase 1: LangExtract extraction layer

### Goal

Add a LangExtract-based extraction step that runs at ingestion time (before the RLM session starts), producing a structured extraction index stored alongside the raw document text.

### Tasks

#### 1.1 Add langextract dependency

File: `pyproject.toml`

- Add `langextract` to project dependencies.
- Add `google-generativeai` or confirm it is pulled in transitively.
- Note: if the user wants to use OpenAI as the LangExtract backend, `langextract[openai]` is needed.

#### 1.2 Create legal extraction schemas

New file: `rlm_legal_docs/extraction_schemas.py`

Define reusable `lx.data.ExampleData` sets for common legal document types. Each schema should include:

1. **Contract schema**: parties, effective date, expiry/termination date, governing law, dispute resolution, indemnity cap, liability limitation, confidentiality period, notice period, renewal terms, assignment restrictions, force majeure.

2. **Correspondence schema**: sender, recipient, date, subject matter, commitments made, deadlines referenced, action items, legal references (statutes, case names, contract names).

3. **Corporate/governance schema**: entity name, board resolution date, resolution subject, authorised signatories, share capital, registered address, compliance deadlines.

4. **General catch-all schema**: dates, monetary amounts, person names, organisation names, legal references, obligations, conditions, deadlines.

Each schema consists of:
- A `prompt_description` string describing the extraction task.
- A list of `lx.data.ExampleData` objects with representative text and extractions.

Implementation notes:
- LangExtract's `extraction_class` values must be consistent strings (e.g., `"party"`, `"effective_date"`, `"indemnity_cap"`). Define these as constants.
- Attributes should include contextual metadata where useful (e.g., `{"role": "buyer"}` for a party extraction).
- Keep example texts short and representative. Two to three examples per schema is sufficient for Gemini.

#### 1.3 Create the extraction engine module

New file: `rlm_legal_docs/extraction.py`

This module wraps LangExtract and manages the extraction pipeline.

Functions:

```
run_extraction(
    text: str,
    doc_name: str,
    schema_name: str | None = None,
    model_id: str = "gemini-2.5-flash",
    api_key: str | None = None,
    max_char_buffer: int = 2000,
    extraction_passes: int = 2,
    max_workers: int = 5,
) -> ExtractionResult
```

- If `schema_name` is None, use the general catch-all schema.
- Returns an `ExtractionResult` dataclass containing:
  - `doc_name: str`
  - `extractions: list[dict]` (each with `extraction_class`, `extraction_text`, `char_start`, `char_end`, `attributes`)
  - `raw_jsonl_path: str | None` (path to saved .jsonl if persisted)

```
run_batch_extraction(
    docs: list[dict[str, str]],  # [{"name": ..., "text": ...}]
    schema_name: str | None = None,
    ...
) -> list[ExtractionResult]
```

- Iterates over documents, calling `run_extraction` for each.
- Returns a list of `ExtractionResult` objects.

```
format_extraction_index(results: list[ExtractionResult]) -> str
```

- Produces the plain-text extraction index to prepend to the RLM context.
- Format:

```
===== EXTRACTION INDEX =====
Pre-extracted structured data with source document and character offsets.

[Document: filename.pdf]
  - party: "Reliance Industries Limited" (chars 142-171)
  - effective_date: "1 April 2024" (chars 312-324)
  ...

[Document: another_file.docx]
  ...
```

```
build_enriched_context(
    docs: list[dict[str, str]],
    extraction_results: list[ExtractionResult]
) -> str
```

- Combines the extraction index and the raw document text into a single context string.
- Calls `format_extraction_index()` for the header, then appends the existing `build_structured_context()` output for the raw documents.

Error handling:
- If LangExtract fails for a document (API error, timeout, unsupported content), log the error, skip that document's extraction, and continue. The raw text is still included in the context. Surface the warning to the user via the existing `errors` list pattern in `IngestWorker`.

#### 1.4 Create the extraction index store

New file: `rlm_legal_docs/extraction_store.py`

A lightweight persistence layer for extraction results so they do not need to be regenerated on every session.

Class: `ExtractionStore`

- Stores extraction results as JSON files in a configurable directory (default: `~/.rlm_extractions/`).
- Key: hash of (file path + file modification time + schema name).
- Methods:
  - `get(file_path, schema_name) -> ExtractionResult | None` (cache hit)
  - `put(file_path, schema_name, result: ExtractionResult)` (cache write)
  - `invalidate(file_path)` (clear stale entries)
  - `clear()` (wipe all)

This avoids re-running LangExtract on unchanged documents across sessions. For the 5-person team scenario with thousands of documents, this is essential for cost and latency control.

#### 1.5 Integrate extraction into the ingestion pipeline

Modified file: `rlm_legal_docs/workers.py`

Modify `IngestWorker._run()`:

1. After text extraction (existing logic), check the `ExtractionStore` for cached results.
2. For documents without cached extractions, run `run_extraction()`.
3. Store new results in the `ExtractionStore`.
4. Call `build_enriched_context()` instead of `build_structured_context()` to produce the combined context.
5. Pass both the extraction results and the context to the result queue.

The result dict should include a new key: `extraction_results: list[ExtractionResult]`.

Import note: `workers.py` currently imports `build_structured_context` from `docx_rlm_query` (line 7). This import path appears to be a legacy reference. It should import from `rlm_legal_docs.query` instead (where the function actually lives). Fix this as part of the change.

Modified file: `rlm_legal_docs/app.py`

- Store `self._extraction_results` alongside `self._context` in `_handle_ingest_done`.
- Pass extraction results to the `QueryWorker` (needed for the citation mechanism in Phase 3).

#### 1.6 Add extraction configuration to the GUI

Modified file: `rlm_legal_docs/config_frame.py`

Add a new "Extraction Settings" section in the sidebar (below Execution Settings):

- Checkbox: "Enable LangExtract preprocessing" (default: on).
- Dropdown: Schema selection (Contract, Correspondence, Corporate, General, Auto-detect). Auto-detect attempts to classify each document and apply the appropriate schema.
- Entry: LangExtract model ID (default: `gemini-2.5-flash`).
- Entry: LangExtract API key (or use `LANGEXTRACT_API_KEY` env var). Save to the same `~/.rlm_gui_config.json` file.
- Spinbox: Extraction passes (default: 2, range 1-5).

Update `get_config()` to include extraction settings in the returned dict.

#### 1.7 Add extraction to the CLI

Modified file: `rlm_legal_docs/query.py`

Add CLI arguments:
- `--extract / --no-extract` (default: `--extract`)
- `--extract-model` (default: `gemini-2.5-flash`)
- `--extract-schema` (default: `general`)
- `--extract-api-key` (default: env var)
- `--extract-passes` (default: 2)

Modify `main()` to run extraction between document ingestion (step 1) and RLM session creation (step 2).

---

## Phase 2: RLM system prompt and REPL integration

### Goal

Configure the RLM to understand the extraction index, use it for planning, and invoke LangExtract at query time for on-demand extraction when the pre-built index does not cover a query.

### Tasks

#### 2.1 Create the enriched system prompt

New file: `rlm_legal_docs/prompts.py`

Define a system prompt addendum that is prepended to whatever custom instructions the user provides:

```
CONTEXT STRUCTURE
=================
The context variable contains two sections:

1. EXTRACTION INDEX: Pre-extracted structured data from the document corpus.
   Each entry includes the document name, extraction class, extracted text,
   and character offsets (char_start-char_end) in the source document.
   Use this section to plan your analysis and locate specific facts quickly.

2. RAW DOCUMENTS: Full text of each document, delimited by
   ===== DOCUMENT N: <filename> =====
   Use this section when you need to read surrounding context, verify
   extractions, or find information not covered by the extraction index.

CITATION REQUIREMENTS
=====================
When making factual claims, include inline citations using this format:
  [Source: document_name, chars start-end]

For claims derived from the extraction index, use the character offsets
provided. For claims found by reading the raw text, determine the
approximate character offset.

For analytical or inferential statements (comparisons, risk assessments,
recommendations), prefix with [Analysis] to distinguish from grounded facts.

AVAILABLE TOOLS
===============
The `langextract` library is available in this REPL (import langextract as lx).
If the user's query requires extraction of entity types not present in the
extraction index, you can run on-demand extraction using lx.extract().
Predefined schemas are available via:
  from rlm_legal_docs.extraction_schemas import get_schema
  schema = get_schema("contract")  # or "correspondence", "corporate", "general"
```

#### 2.2 Wire the system prompt into RLM creation

Modified file: `rlm_legal_docs/app.py`

In `_create_rlm()`, prepend the enriched system prompt (from `prompts.py`) before the user's custom instructions and the default `RLM_SYSTEM_PROMPT`.

Order: enriched prompt -> user custom instructions -> RLM_SYSTEM_PROMPT.

#### 2.3 Expose extraction schemas in the REPL namespace

The RLM's `LocalREPL` runs code via `exec()` with configurable namespaces. Investigate whether `alexzhang13/rlm` exposes a way to inject additional globals or modules into the REPL namespace.

If it does: inject `langextract`, `extraction_schemas`, and a pre-built `extraction_index` variable (a Python dict of the parsed extraction results) so the RLM can reference them directly in code.

If it does not: rely on the fact that `LocalREPL` shares the host virtual environment. The RLM can `import langextract as lx` and `from rlm_legal_docs.extraction_schemas import get_schema` in its generated code. Test that this works. If the REPL's restricted globals block it, file this as a limitation and document a workaround (e.g., injecting a helper function via the custom system prompt as a string that the RLM can `exec()`).

#### 2.4 Add a query-time extraction helper

New function in `rlm_legal_docs/extraction.py`:

```
def on_demand_extract(
    text: str,
    prompt_description: str,
    extraction_classes: list[str],
    model_id: str = "gemini-2.5-flash",
    api_key: str | None = None,
) -> list[dict]
```

This is a simplified wrapper for the RLM to call from within the REPL when it needs extraction not covered by the pre-built index. It constructs a minimal `ExampleData` from the `extraction_classes` list and runs `lx.extract()`.

The system prompt in 2.1 should instruct the RLM to use this function when needed, providing an example call.

---

## Phase 3: Citation mechanism

### Goal

Ensure that factual claims in the RLM's output are traced back to specific source locations, and that the distinction between grounded facts and analytical reasoning is visible to the user.

### Tasks

#### 3.1 Create the citation enrichment module

New file: `rlm_legal_docs/citations.py`

Class: `CitationEnricher`

Constructor takes:
- `extraction_results: list[ExtractionResult]` (the pre-built extraction index)

Method: `enrich(response_text: str) -> EnrichedResponse`

`EnrichedResponse` dataclass:
- `text: str` (the response with inline citation markers)
- `citations: list[Citation]` (structured citation objects)
- `ungrounded_claims: list[str]` (analytical statements without source grounding)

Logic:

1. Parse the RLM response for inline citations already present (the RLM was instructed to include `[Source: ...]` markers). Extract and validate them against the extraction index. If the cited character offsets exist in the index, mark as verified. If they do not, mark as unverified.

2. For any factual-looking text that lacks a citation (dates, monetary amounts, party names, percentages), attempt fuzzy matching against the extraction index. Use the following matching strategy:
   - Exact string match of `extraction_text` within the response.
   - Normalised match (strip currency symbols, normalise date formats, case-insensitive) for near-matches.
   - If a match is found, insert a citation marker after the claim.

3. For analytical statements prefixed with `[Analysis]` by the RLM, preserve the marker.

4. For statements that appear factual but cannot be matched to the extraction index and were not cited by the RLM, flag them in the `ungrounded_claims` list.

Implementation notes:
- This is a best-effort mechanism. It will not catch every grounded or ungrounded claim. The goal is to provide useful traceability for the majority of factual assertions, not perfection.
- Fuzzy matching should be conservative. False positive citations (citing the wrong source) are worse than missing citations. If the match confidence is low, do not insert a citation.
- Consider using a lightweight regex-based approach for date and amount detection, not a full NLP pipeline. Keep the dependency footprint small.

#### 3.2 Integrate citation enrichment into the query pipeline

Modified file: `rlm_legal_docs/workers.py`

In `QueryWorker._run()`, after receiving the RLM response:

1. Instantiate `CitationEnricher` with the extraction results.
2. Call `enrich(response)`.
3. Include the enriched response and citation metadata in the result queue message.

Modified file: `rlm_legal_docs/app.py`

In `_handle_query_done()`, pass citation metadata to the chat frame.

#### 3.3 Display citations in the GUI

Modified file: `rlm_legal_docs/chat_frame.py`

In `MessageBubble`, detect citation markers (`[Source: ...]`) and render them differently from body text:
- Apply a distinct text colour (use `COLORS["accent"]` for citations).
- If the user clicks on a citation (or right-clicks and selects "View Source"), open a small popup or tooltip showing the relevant excerpt from the source document with surrounding context (e.g., 200 characters either side of the cited span).

For `[Analysis]` markers, render in the existing `COLORS["warning"]` colour to visually distinguish analytical claims from grounded facts.

For ungrounded claims (if the enricher flags them), consider a subtle underline or no special treatment initially. Aggressive flagging of ungrounded claims can be noisy and confusing. Start with citation highlighting only and add ungrounded-claim warnings in a later iteration if users request it.

#### 3.4 Add a citation summary footer

After the RLM response message in the chat, add a collapsible "Sources" section listing all citations with their document names and character offsets. This gives the user a quick reference without cluttering the main response.

---

## Phase 4: LangExtract visualisation integration

### Goal

Leverage LangExtract's built-in HTML visualisation to give users an interactive view of all extractions from their document set.

### Tasks

#### 4.1 Generate the visualisation at ingestion time

Modified file: `rlm_legal_docs/extraction.py`

After running batch extraction, call `lx.io.save_annotated_documents()` and `lx.visualize()` to produce:
- A `.jsonl` file of all extractions.
- A self-contained `.html` visualisation file.

Store both in the extraction cache directory.

#### 4.2 Add a "View Extractions" button to the GUI

Modified file: `rlm_legal_docs/app.py` and `rlm_legal_docs/config_frame.py`

Add a button in the sidebar (visible after session start) labelled "View Extractions". On click, open the HTML visualisation in the system default browser using `webbrowser.open()`.

---

## Phase 5: Testing

### Tasks

#### 5.1 Unit tests for extraction module

New file: `tests/test_extraction.py`

- Test `format_extraction_index()` with known inputs and verify output format.
- Test `build_enriched_context()` produces output containing both the extraction index and raw documents.
- Test `ExtractionStore` cache hit/miss/invalidation logic.
- Mock `lx.extract()` to avoid API calls in unit tests.

#### 5.2 Unit tests for citation module

New file: `tests/test_citations.py`

- Test exact string matching of extraction text in responses.
- Test normalised matching (date formats, currency formats).
- Test that `[Source: ...]` markers already present in responses are parsed correctly.
- Test that `[Analysis]` markers are preserved.
- Test edge cases: empty response, response with no matchable content, response where all claims are already cited.

#### 5.3 Integration test with sample documents

New file: `tests/test_integration.py`

- Use a small set of sample legal documents (include 2-3 short sample contracts and a correspondence email as test fixtures).
- Run the full pipeline: ingest -> extract -> build context -> RLM query -> citation enrichment.
- Verify that the extraction index is present in the context.
- Verify that the RLM receives the enriched system prompt.
- This test will require API keys and should be marked as a slow/integration test (skip in CI unless keys are provided).

#### 5.4 Schema validation tests

New file: `tests/test_schemas.py`

- Verify that each schema in `extraction_schemas.py` produces valid `lx.data.ExampleData` objects.
- Run each schema against a short sample text and verify that LangExtract returns results without errors.

---

## File change summary

### New files

| File | Purpose |
|---|---|
| `rlm_legal_docs/extraction_schemas.py` | Predefined legal extraction schemas (few-shot examples) |
| `rlm_legal_docs/extraction.py` | LangExtract wrapper, batch extraction, context builder |
| `rlm_legal_docs/extraction_store.py` | Cache layer for extraction results |
| `rlm_legal_docs/prompts.py` | Enriched system prompt for extraction-aware RLM |
| `rlm_legal_docs/citations.py` | Post-processing citation enrichment |
| `tests/test_extraction.py` | Unit tests for extraction module |
| `tests/test_citations.py` | Unit tests for citation module |
| `tests/test_schemas.py` | Schema validation tests |
| `tests/test_integration.py` | End-to-end integration test |
| `tests/fixtures/` | Sample legal documents for testing |

### Modified files

| File | Changes |
|---|---|
| `pyproject.toml` | Add `langextract` dependency |
| `rlm_legal_docs/workers.py` | Integrate extraction into ingestion; citation enrichment in query pipeline; fix import path |
| `rlm_legal_docs/app.py` | Store extraction results; wire enriched system prompt; pass citations to chat frame; add View Extractions button |
| `rlm_legal_docs/config_frame.py` | Add extraction settings section; add View Extractions button |
| `rlm_legal_docs/chat_frame.py` | Render citation markers with distinct styling; add Sources footer |
| `rlm_legal_docs/query.py` | Add extraction CLI arguments; integrate extraction into CLI pipeline |
| `rlm_legal_docs/constants.py` | Add extraction-related constants (cache directory, default schema, etc.) |

### Unchanged files

| File | Reason |
|---|---|
| `rlm_legal_docs/file_frame.py` | No changes needed; file selection is independent of extraction |
| `rlm_legal_docs/log_viewer.py` | No changes needed; log viewing is independent of extraction |
| `rlm_legal_docs/cli.py` | No changes needed; entry points are unchanged |
| `rlm_legal_docs/__init__.py` | May need version bump only |

---

## Implementation order

The phases should be implemented sequentially because each depends on the previous.

1. Phase 1 (extraction layer) is the foundation. Without it, nothing else works.
2. Phase 2 (RLM integration) depends on Phase 1's output format.
3. Phase 3 (citations) depends on both Phase 1 (extraction index for matching) and Phase 2 (RLM output to enrich).
4. Phase 4 (visualisation) depends on Phase 1 but is independent of Phases 2 and 3. It can be done in parallel with Phase 3 if needed.
5. Phase 5 (testing) should be done incrementally alongside each phase, but the integration test requires all phases complete.

Within Phase 1, the order should be: 1.1 (dependency) -> 1.2 (schemas) -> 1.3 (extraction engine) -> 1.4 (store) -> 1.5 (pipeline integration) -> 1.6 (GUI) -> 1.7 (CLI).

---

## Known risks and mitigations

| Risk | Mitigation |
|---|---|
| LangExtract API costs for large document sets | Extraction store cache (task 1.4) ensures each document is extracted only once. Use `gemini-2.5-flash` (cheapest viable model). Make extraction optional via GUI toggle. |
| LangExtract extraction quality varies by document type | Multiple schemas (task 1.2) tailored to legal subtypes. Multi-pass extraction (`extraction_passes=2`) improves recall. |
| RLM REPL may restrict imports of langextract | Test early (task 2.3). Fallback: inject a helper function via the system prompt. |
| Citation enrichment false positives | Conservative fuzzy matching with high confidence threshold (task 3.1). Start with exact and normalised matching only. |
| REPL output truncation hides LangExtract output | Instruct the RLM to summarise LangExtract output before printing (task 2.1 system prompt). Wrap the on-demand extraction helper to return concise summaries. |
| workers.py has a broken import (`from docx_rlm_query import ...`) | Fix as part of task 1.5. This is an existing bug that will cause import errors in the GUI. |

---

## Assumptions

1. The primary RLM backend remains `alexzhang13/rlm`. The `ysz/recursive-llm` repo is referenced for design ideas (two-model pattern, RestrictedPython sandboxing) but is not added as a dependency.
2. LangExtract's Gemini backend is the default for extraction. Users who prefer OpenAI or Ollama can configure this via the GUI or CLI.
3. The extraction step runs synchronously during ingestion (blocking the GUI with a progress indicator). For very large document sets, a future iteration could make this asynchronous with per-document progress updates.
4. The citation mechanism is best-effort. It improves traceability but does not guarantee complete source grounding for every claim.
5. Document classification (auto-detecting which schema to use) is deferred to a later iteration. Initially, users select the schema manually or use the general catch-all.
