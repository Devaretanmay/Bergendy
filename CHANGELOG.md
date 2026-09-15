# Changelog

All notable changes to Boundary are documented here.

## [1.1.3] - 2026-09-15

### Added
- **Autonomous Polyglot Runtime Boundaries**:
  - `boundary resolve`: LLM-driven contract synthesis supporting TypeScript/JavaScript (Zod), Python (Pydantic), and Go (`struct` with JSON tags).
  - Context & Payload Isolation: strictly extracts and models `response_body` telemetry, preventing wrapper hallucination.
  - "No-Swallow" AST Verification: rejects patches that wrap validation checks in silent error-suppressing blocks.
  - Polyglot AST Rewriter (`src/engines/rewriter.rs`): injects `.parse(data)` and `Schema.parse(await res.json())` directly at client callsites.
- **Hermetic Sandbox Replay (Ghost Proxy)**:
  - Rust axum-based mock proxy (`src/ghost_proxy/`) running on localhost:54321 for offline, deterministic replaying of captured network telemetry.
- **Enterprise Command Suite**:
  - `boundary scan`: locates unvalidated external network callsites across polyglot repositories.
  - `boundary guard` & `boundary verify`: pre-commit and CI verification gates.
  - `boundary auth`: BYOK provider authentication (Groq, OpenAI, Anthropic).

### Changed
- Pruned dead legacy compression engines, framework hook adapters, and unneeded dependencies.
- Standardized CLI output format.

## [1.1.0] - 2026-09-01

### Added
- **Core Rust Engine (`boundary-core`)**:
  - High-performance AST analysis and external-change dependency graph (`src/engines/graph/`).
  - OpenAPI and JSON schema diffing engine (`src/engines/schema/`).
  - Operating system sandbox isolation: macOS `sandbox-exec` profile generator and Linux `landlock` enforcement.
  - Instant worktree snapshotting and content-addressed cache (`src/runtime/`).
- **BYOK AI Credentials**:
  - Secure credential storage in `~/.boundary/credentials.json`.
- **Telemetry Capture**:
  - Outbound HTTP interception and structured `HttpExchange` logging.

## [1.0.0] - 2026-08-15

### Added
- Initial release of Boundary: Autonomous External-Change Intelligence & Controlled Execution.
