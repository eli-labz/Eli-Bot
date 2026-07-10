# Microsoft Word WINWORD.EXE Agent Actions

This integration adds supervised Microsoft Word desktop actions as bounded HumanActionToken events.

## Safety and Governance

- No keylogging.
- No full document scraping by default.
- No external document transmission.
- No macro execution by default.
- No external sharing actions by default.
- No destructive or high-impact action without policy gate and explicit approval.
- Every action requires preconditions and expected_outcome.
- Every action emits audit events.
- Every executed action is verified.
- Low-confidence actions are blocked and escalated.

## Action Lifecycle

1. Observe Word state using `WordObservationAdapter`.
2. Build `HumanActionToken` via `WordActionRegistry`.
3. Evaluate policy in `WordPolicyGate`.
4. Execute approved action with `WordActionExecutor`.
5. Verify outcome in `WordOutcomeVerifier`.
6. Write audit events via `WordTraceWriter`.
7. Persist reusable memory for successful/blocked outcomes.
8. Return outcome tokens and final status.

## Supported Verbs

- OPEN_WORD
- OPEN_DOCUMENT
- CREATE_DOCUMENT
- TYPE_TEXT
- FIND_TEXT
- REPLACE_TEXT
- APPLY_STYLE
- APPLY_FORMATTING
- INSERT_TABLE
- INSERT_PAGE_BREAK
- SAVE_DOCUMENT
- SAVE_AS
- EXPORT_PDF
- CLOSE_DOCUMENT
- CLOSE_WORD
- GET_WORD_STATE
- VERIFY_DOCUMENT_STATE
- ESCALATE_TO_HUMAN

## Prompt Routing

Explicit user prompts starting with `word ` or `winword ` are routed into the Word workflow engine.

Examples:

- `word get state`
- `word open C:\\Approved\\input.docx`
- `word type Quarterly summary draft`
- `word replace old phrase -> new phrase`
- `word export pdf C:\\ApprovedOutput\\report.pdf`
