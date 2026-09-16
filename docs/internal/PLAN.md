# Boundary Pivot: Dynamic Telemetry & Data Flow

## 1. Rust Core `src/`
- Integrate `oxc` for Control Flow Graph and semantic data flow.
- Track `fetch` -> `Response` -> `.json()` -> `.parse()` (Zod) validation logic.
- Flag "Unvalidated Boundary" if the chain breaks.
- Add OpenTelemetry gRPC/HTTP collector (`src/otel_collector/`) to ingest traces and response bodies.
- Gut the old `ChangeSource` registry logic (if present in Rust `manifest_lockfile` or similar).

## 2. Python Orchestrator `python/boundary/`
- Gut `change_source.py` and replace with `traffic_drift.py` (`TrafficDriftSource`).
- Replace the AST/registry trigger with the Dynamic Network Telemetry trigger.
- Add `read_captured_traffic` tool for the AI Hunt loop.
- Rewrite `prompts/` to focus on type theory (Zod, Pydantic, discriminated unions).
- Introduce Contract Tests: Run `boundary verify` inside the sandbox before `npm run test`, replaying captured traffic against the generated Zod schemas.

## 3. SDKs `sdk/`
- Build thin OTEL auto-instrumentation wrappers for TS/JS and Python, pointing to `localhost:4317`.
- Gut old package lock parsing logic from SDKs.
