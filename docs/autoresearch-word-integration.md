# Autoresearch Word Integration

## Purpose

This integration adds an opt-in bridge so Eli Bot can use AutoResearch planning output while keeping Microsoft Word execution behind a controlled boundary.

Flow:

Eli Bot prompt -> AutoresearchWordBridge -> AutoresearchWordService -> WordActionRequest -> WordDocumentController -> Word action execution -> verification -> trace -> Eli Bot response

## Architecture

- `core/edge_actions/autoresearch_word/bridge.py`
  - Entry point for explicit prompts: `word research ...` and `winword research ...`
- `core/edge_actions/autoresearch_word/service.py`
  - Reads AutoResearch context from `core/third_party/autoresearch-master`
  - Produces bounded text output and request payloads
- `core/edge_actions/autoresearch_word/word_document_controller.py`
  - Detects existing `core/office/word/WordDocument` project availability
  - Uses the existing Word workflow engine for controlled action execution
- `core/edge_actions/autoresearch_word/policy.py`
  - Safety checks and path allowlist gates
- `core/edge_actions/autoresearch_word/verifier.py`
  - Result verification marker
- `core/edge_actions/autoresearch_word/trace.py`
  - Structured per-action trace output

## Feature Flag

Default is disabled.

- `ENABLE_AUTORESEARCH_WORD=false`

When disabled:

- Existing Eli Bot behavior is unchanged.
- Bridge stays inactive.
- Missing AutoResearch files do not crash startup.

When enabled:

- Explicit `word research ...` commands use the bridge.

## Supported Actions

- detect WordDocument availability
- create new document
- open approved `.docx`
- insert text
- append research output
- apply heading (safe placeholder action)
- save document
- save as approved path
- export PDF only with approval
- close document safely

## Safety Gates

- Block unsupported extensions (`open_document` requires `.docx`, `export_pdf` requires `.pdf`)
- Block paths outside approved directories unless explicitly allowed
- Block overwrite without approval
- Block export without approval
- Block close unsaved document without approval
- Block macro execution by default
- Block silent external sharing
- Trace every request/result

## Test Commands

Run only the integration tests:

```powershell
.\.venv312\Scripts\python.exe -m unittest tests.edge_actions.test_autoresearch_word_bridge -v
```

Run Word integration + bridge tests:

```powershell
.\.venv312\Scripts\python.exe -m unittest tests.edge_actions.test_word_integration tests.edge_actions.test_autoresearch_word_bridge -v
```

## Rollback

1. Set `ENABLE_AUTORESEARCH_WORD=false`
2. Remove the `core/edge_actions/autoresearch_word/` package and its tests/docs
3. Remove the small hook in `core/assistant.py` (`_try_autoresearch_word_actions`)

After rollback, existing Eli Bot and Word behavior remains as before.
