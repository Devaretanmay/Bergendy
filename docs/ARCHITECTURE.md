# Boundary System Architecture

> **Boundary keeps software working when the outside world changes.**

Boundary bridges the gap between dynamic external API traffic and rigid, typed codebase boundaries. It automates runtime contract synthesis, callsite patching, and hermetic sandbox verification.

---

## 1. System Pipeline

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Telemetry Capture Layer                                                  │
│    - OpenTelemetry Collector / Next.js SDK / Fetch Shim                     │
│    - Captures raw HttpExchange (method, path, status, response_body)        │
│    - Persisted to .boundary/knowledge/exchanges.jsonl                       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. Static AST Scanner (Rust & Python)                                       │
│    - Scans AST across TS/JS, Python, Go for unvalidated external callsites  │
│    - Identifies endpoints, methods, and unmarshaled variables               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. Context & Payload Isolation                                              │
│    - Extracts ONLY response_body from captured telemetry clusters           │
│    - Drops telemetry metadata (request_method, request_headers)             │
│    - Unwraps root objects to prevent double-array/slice hallucinations      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. Polyglot Schema Synthesizer (BYOK AI Provider)                           │
│    - TypeScript: Zod schema (import { z } from 'zod')                       │
│    - Python: Pydantic BaseModel (import { BaseModel } from 'pydantic')      │
│    - Go: Struct definitions with json struct tags                           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. Polyglot AST Rewriter & Verifier                                         │
│    - Injects Schema.parse(data) or model_validate() at callsites            │
│    - No-Swallow Rule: Rejects patches with silent try/catch blocks          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6. Hermetic Sandbox & Ghost Proxy Replay                                    │
│    - macOS sandbox-exec / Linux Landlock drops outbound network             │
│    - Rust Ghost Proxy (Axum on 127.0.0.1:54321) serves recorded exchanges   │
│    - Replays canned status codes & response bodies to local test suite      │
│    - Passes ONLY if new schemas successfully validate mock traffic          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Components

### A. The Ghost Proxy (`src/ghost_proxy/`)
Built with native Rust and Tokio/Axum:
* Loads recorded `HttpExchange` structs into memory.
* Operates on a dynamic or static loopback port (`127.0.0.1:54321`).
* Matches incoming requests against method and target path (`x-boundary-original-url` or raw path).
* Serves the isolated `response_body` bytes with recorded `response_headers`.
* Returns `404 Unmocked Boundary` if an unmocked network request is attempted, guaranteeing that tests run strictly offline.

### B. Payload Isolation Engine (`python/boundary/hunt.py`)
Prevents **Context Leakage**:
* Telemetry logging wraps HTTP events in metadata envelopes.
* If the full envelope is provided to the LLM, the model creates schemas for the logger rather than the API.
* The isolation engine extracts only `exchange.response_body`, unwraps single-sample payloads, and prompts the AI with strict boundary validation directives.

### C. The Polyglot AST Rewriter (`src/engines/rewriter.rs`)
Directly manipulates source code ASTs:
* Injects schema imports at the file header.
* Rewrites raw `.then(r => r.json())` into `.then(r => r.json()).then(data => Schema.parse(data))`.
* Rewrites `const data = await res.json()` into `const data = Schema.parse(await res.json())`.
* Validates that the patch contains no error-suppressing `catch { return null; }` blocks.

### D. Multi-Ecosystem Test Runner (`python/boundary/test_runner.py`)
Auto-detects test runners across polyglot projects:
* **Go**: `go build .`, `go vet .`, `go test ./...`
* **Python**: `pytest`, `python -m unittest`, `python -m py_compile`
* **Node.js**: `npm test`, `node --check`

---

## 3. Directory Layout on Disk

```text
.boundary/
  knowledge/
    exchanges.jsonl       Captured runtime HTTP telemetry spans
  contracts/              Synthesized schemas
  graph.json              Static dependency callsite map
```
