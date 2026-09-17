# Changelog

All notable changes to Bergendy are documented here.

## [1.1.5] - 2026-09-17

### Added
- Rename release to **Bergendy** (`bergendy` on PyPI).
- **Hybrid AST + AI Architecture**:
  - Rust AST Context Extractor (`src/engines/context_extractor.rs`) capturing precise function signatures, callsite coordinates, data-flow nodes, error handling patterns, and existing imports.
  - Rust 6-Point AST Verifier (`src/engines/ast_verifier.rs`) executing deterministic safety checks (syntactic balance, schema wiring, No-Swallow rule, blast radius preservation, import correctness, naming conventions).
  - Structured 3-block transformation prompt format (`python/bergendy/prompts/transformation.txt`).
  - Reflection retry loop with AST feedback in `python/bergendy/hunt.py` (`ai_generate_patch`).
- Zero-token deterministic schema synthesis fallback when offline or lacking LLM API keys.
- Next.js auto-instrumentation injection on `bergendy init`.
- Root `--version` flag (`bergendy --version`).
- Clean `bergendy fix` interactive guided flow with Ghost Proxy verification.

## [1.1.4] - 2026-09-17

### Added
- Next.js auto-instrumentation detection.
- `--version` CLI argument.

## [1.1.3] - 2026-09-15

### Added
- **Autonomous Polyglot Runtime Boundaries**:
  - `boundary resolve`: LLM-driven contract synthesis supporting TypeScript/JavaScript (Zod), Python (Pydantic), and Go (`struct` with JSON tags).
  - Context & Payload Isolation: strictly extracts and models `response_body` telemetry, preventing wrapper hallucination.
  - "No-Swallow" AST Verification: rejects patches that wrap validation checks in silent error-suppressing blocks.
  - Polyglot AST Rewriter (`src/engines/rewriter.rs`): injects `.parse(data)` and `Schema.parse(await res.json())` directly at client callsites.
- **BYOK AI Credentials**:
  - `boundary auth`: provider authentication (Groq, OpenAI, Anthropic); credentials in `~/.boundary/credentials.json` (0600).
- **Enterprise Command Suite**:
  - `boundary scan`: alias of `boundary check`; locates external API drift and unvalidated boundaries.
  - `boundary score`: 0-100 repo health score (SDK drift + unvalidated runtime calls).
  - `boundary scout`: read-only audit — maps boundaries, warns, touches nothing.
  - `boundary shield`: pre-commit enforcement + schema generation (`--on/--off/--fix/--status`).
  - `boundary dev`: run your app with live traffic capture into `.boundary/contracts.db`.
- **Hermetic Sandbox Replay (Ghost Proxy)**:
  - Rust mock proxy infrastructure for offline, deterministic replaying of captured network telemetry during sandboxed verification (reachable at `127.0.0.1:54321`).
- **MCP Server**:
  - `boundary mcp`: Model Context Protocol server for AI assistants.

### Changed
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
- Initial release of Bergendy: Autonomous External-Change Intelligence & Controlled Execution.
