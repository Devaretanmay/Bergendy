# Boundary: Project Status & Execution Masterplan

## 1. STATE MATRIX: What We've Decided vs. What Needs Inventing

| Subsystem | What We've Decided & Built | What Needs Inventing / Hardening |
| :--- | :--- | :--- |
| **Rust Core (Execution)** | Keep Kernel-level sandboxing (Seatbelt/Landlock) and BLAKE3 instant rollbacks. | Handling asynchronous sandbox timeouts without blocking the main event loop. |
| **Rust Core (AST & Data Flow)** | Integrated `oxc` for exact data flow tracking, identifying `fetch()` calls that skip `.parse()` validation. | Expanding CFG (Control Flow Graph) across module boundaries and imports (hard). |
| **Telemetry (Network-to-Static)** | Built local OpenTelemetry gRPC/HTTP collector (`0.0.0.0:4317`) in Rust to capture dynamic JSON shapes. | JSON schema inference from sparse/variable network samples over time. |
| **Python Orchestrator (AI)** | Gutted npm/PyPI registry scrapers. Replaced with `TrafficDriftSource` and updated `hunt.py` for Matt Pocock Zod/Pydantic generation. | Diff-aware prompt optimization to prevent the AI from hallucinating types outside the network trace. |
| **Verification Loop** | Injected `boundary verify` (Contract Tests) prior to standard tests inside the isolated sandbox. | Handling non-deterministic API states and authentication in isolated replay tests. |
| **SDK (Instrumentation)** | Thin TypeScript wrappers around OpenTelemetry auto-instrumentation shipping spans to the local Rust core. | Monkey-patching Edge runtimes (Cloudflare/Next.js) where standard Node OTEL fails. |

---

## 2. REFACTORING CHECKLIST: Code-Level Mapping

### `src/` (Rust Core)
- **[KEEP]** `src/sandbox/`: Core isolation logic (Seatbelt/Landlock). Critical IP.
- **[KEEP]** `src/engines/tree_sitter/`: Baseline syntax mapping and struct extraction.
- **[KEEP]** `src/runtime/ccr.yaml`: Cache and concurrency limits for the sandbox.
- **[NEW]** `src/engines/oxc_flow/`: The `oxc` semantic analyzer that traces `fetch` responses to validate Zod parsing.
- **[NEW]** `src/otel_collector/`: Axum server to ingest OTLP JSON traces and dump `http.response.body` to `.boundary/knowledge/`.
- **[DELETE]** `src/engines/package_locks/` (or equivalent): Kill anything doing static registry analysis.

### `python/boundary/` (AI Orchestrator)
- **[KEEP]** `sandbox.py` / execution wrappers: Required for calling the Rust sandbox safely.
- **[KEEP]** `git_ops.py` / PR generation logic: Foundational for the autonomous PR loops.
- **[NEW]** `traffic_drift.py`: Replaces the legacy source-tracking abstractions with dynamic telemetry ingestion.
- **[NEW]** `mcp_server.py`: Added `boundary_read_captured_traffic` tool so the AI can pull runtime schemas directly.
- **[REWRITE]** `hunt.py`: Prompts completely rewritten to enforce "parse, don't validate." Sandboxing now strictly executes `boundary verify` *before* `npm run test`.
- **[DELETE]** `change_source.py`: Obliterated. No more npm/PyPI scraping.

### `sdk/` (Telemetry Wrappers)
- **[NEW]** `sdk/typescript/instrument.js`: Injects `@opentelemetry/instrumentation-fetch` and `@opentelemetry/instrumentation-http` globally, exporting to `localhost:4317`.
- **[DELETE]** Any dependency/lockfile parsers. We only care about runtime now.

---

## 3. 4-WEEK SPRINT PLAN

### Week 1: Core Engine Pivot (Completed / Hardening)
- **Goal:** Establish the Rust/Python pipeline for dynamic traffic ingestion.
- **Tasks:** Hardening the `oxc_flow` data tracer. Hardening the Rust Axum OTEL collector. Ensure `.boundary/knowledge/` correctly logs payload graphs without overwhelming the disk.

### Week 2: Edge-Case SDK Instrumentation
- **Goal:** Guarantee telemetry extraction from hostile environments.
- **Tasks:** Standard Node.js `fetch` is instrumented, but Next.js Edge and Cloudflare Workers strip standard Node globals. Build custom `globalThis.fetch` proxy wrappers for Edge environments that batch and flush OTLP via `waitUntil`.

### Week 3: AI Schema Inference & Contract Tests
- **Goal:** The AI must reliably turn raw JSON dumps into rigorous Zod schemas and verify them.
- **Tasks:** Build the schema inference engine in the Rust core (compressing 1000s of payloads into a single AST shape). Tune the `hunt.py` LLM calls to map the schema exactly to the AST without rewriting unrelated code. Stabilize the `boundary verify` replay mechanism.

### Week 4: Launch Polish & YC Self-Maintaining API RFS
- **Goal:** Ship the open-core CLI for the YC Fall 2026 application.
- **Tasks:** Polish the CLI UX (`boundary dev` wrapping local dev servers). Write the `README.md` positioning Boundary as the ultimate dynamic-to-static bridge. Produce a demo video showing a Stripe API breaking change automatically getting caught and patched with a Zod schema locally.

---

## 4. ARCHITECTURAL LANDMINES

### Landmine 1: Data Flow Analysis Across Modules
**The Reality:** Tracing a variable from `const res = await fetch(...)` to `res.json()` to `schema.parse(data)` is easy in one file. It's nearly impossible if `fetch` happens in `api.ts`, returns an object, gets passed to `utils.ts`, and parsed in `component.tsx`.
**Staff Recommendation:** Don't build a global static analyzer. `oxc` will fail at scale. Instead, rely on the runtime. Tag the OTEL spans with the exact stack trace and file/line number of the `fetch`. Give the LLM the exact callsite context from the trace, and let the AI deduce the variable scope locally.

### Landmine 2: Next.js Edge & Serverless Runtime Environments
**The Reality:** Standard `@opentelemetry/sdk-node` relies on `async_hooks`, which do not exist in Next.js Edge Runtime or Cloudflare Workers. Monkey-patching `fetch` there often breaks the framework's native caching or streaming responses.
**Staff Recommendation:** Ship a Next.js specific wrapper (`@boundary/sdk/next`) that hooks into `next.config.js` or uses Next 15's native `instrumentation.ts` specifically designed for OTEL. For Cloudflare, we must write a pure JS proxy wrapper that flushes spans via `ctx.waitUntil()` to avoid blocking the worker response.

### Landmine 3: Contract Test Flakiness (Authentication & State)
**The Reality:** `boundary verify` replays captured traffic against the new schema. But if the live traffic contained authenticated tokens or temporal data (timestamps, UUIDs), the replay might fail for structural reasons, not schema reasons.
**Staff Recommendation:** Contract Tests shouldn't make real network calls. The Rust core must act as a transparent proxy during the test phase. When `boundary verify` runs, it intercepts the outbound request, matches it to the captured OTLP trace, and returns the exact captured JSON payload. We are testing the *schema validation logic*, not the upstream server.
