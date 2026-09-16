# Evidence Capture & Context Management

When executing test suites, build runs, or compiler verifications, output can span thousands of lines of terminal text. Boundary enforces strict context boundaries to keep prompts signal-rich, prevent context blowup, and keep verification reliable.

---

## 1. High-Signal Log Capture

Boundary captures execution output and isolates the deciding lines:
* **Stack Trace Extraction**: Isolates tracebacks, syntax errors, and failing assertion lines from long build logs.
* **Deterministic Bounding**: Raw captures are capped at high-signal limits (e.g. 8KB) to fit cleanly within LLM context windows without loss of semantic errors.
* **Exit Code Integrity**: Exit codes (`0` for pass, non-zero for fail) are strictly preserved and never synthesized or assumed.

---

## 2. Telemetry Exchange Bounding

For HTTP traffic telemetry stored in `.boundary/knowledge/exchanges.jsonl`:
* Payloads are bounded to prevent single massive JSON dumps (e.g. 50MB database exports) from exhausting token budgets.
* Repetitive identical requests are clustered, deduplicating variation samples before feeding them to the schema synthesizer.
