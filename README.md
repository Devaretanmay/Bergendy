<div align="center">

# Boundary

### Autonomous Runtime Boundary Defense & Polyglot Schema Synthesis

![version](https://img.shields.io/badge/version-1.1.3-blue) ![license](https://img.shields.io/badge/license-Apache--2.0-green) ![python](https://img.shields.io/badge/python-3.10%2B-yellow) ![platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey)

**APIs drift. Upstream payloads change. Boundary detects unguarded boundaries, synthesizes rigid schemas, and verifies them in hermetic sandboxes.**

```bash
pip install boundary

# 1. Scan for unvalidated runtime boundaries (Python, TypeScript/JavaScript, Go)
boundary scan

# 2. Synthesize rigid schemas from traffic and patch callsites
boundary resolve --target src/api_client.ts

# 3. Guard pre-commit boundaries and verify in sandbox
boundary guard
boundary verify
```

[Quickstart](docs/QUICKSTART.md) | [CLI Reference](docs/CLI.md) | [Architecture](docs/ARCHITECTURE.md) | [Ghost Proxy](docs/GHOST_PROXY.md)

</div>

---

## Why Boundary?

Every modern software application calls out to external systems — third-party APIs, SaaS microservices, and AI providers. When external APIs change or drift, applications crash in production:

1. **Unvalidated Boundaries**: Calls to `fetch()`, `requests.get()`, or `http.Get()` cast JSON responses to `any`, untyped dictionaries, or unchecked structs.
2. **Context Leakage & Schema Hallucination**: AI code generators often model HTTP telemetry wrappers (`request_method`, `request_headers`) rather than the actual API response payload.
3. **Silent Error Swallowing**: Fixes that wrap validation inside silent `try/catch` or `except: pass` blocks pass tests in dev but silently drop critical data in production.

**Boundary fixes this at the runtime layer:**
- Detects unvalidated network calls across your repository AST.
- Extracts and isolates captured HTTP response payloads (`response_body`).
- Synthesizes rigid, typed runtime contracts (**Zod** for TS/JS, **Pydantic** for Python, **Go structs** for Go).
- Rewrites callsites using native AST injection with **No-Swallow verification**.
- Verifies repairs inside an isolated kernel sandbox with the **Rust Ghost Proxy**.

---

## Core Capabilities

```text
               LIVE RUNTIME TRAFFIC (OpenTelemetry / Capture SDK)
                                      ↓
                     UNVALIDATED CALLSITE SCANNER (AST Engine)
                    [Python: requests/httpx | TS: fetch/axios | Go: http]
                                      ↓
                     PAYLOAD CONTEXT ISOLATION
                   [Extracts pure response_body; drops wrappers]
                                      ↓
                     LLM SCHEMA SYNTHESIZER (BYOK: Groq / OpenAI / Anthropic)
                   [TypeScript: Zod | Python: Pydantic | Go: Structs]
                                      ↓
                     AST CALLSITE REWRITER (Polyglot)
                   [Injects .parse(data) with No-Swallow verifier]
                                      ↓
                     GHOST PROXY SANDBOX REPLAY
                   [Hermetic 127.0.0.1:54321 mock replay; network blocked]
```

### 1. Multi-Language Boundary Scanning (`boundary scan`)
Scans repository source trees for external HTTP callsites that lack runtime validation schemas or rely on loose `any` casts:
- **TypeScript / JavaScript**: unvalidated `fetch()`, `axios.get()`, `axios.post()`, or `as any` casts.
- **Python**: unvalidated `requests.get()`, `httpx.get()`, and unmodeled `.json()` access.
- **Go**: unvalidated `http.Get()`, `http.Post()`, `client.Do()`, and unchecked `json.Unmarshal`.

```bash
boundary scan
```

### 2. Autonomous Schema Synthesis & AST Rewriting (`boundary resolve`)
Synthesizes rigid schemas from observed traffic samples and injects validation logic directly into the source code:
- Isolates the HTTP response payload — guarantees zero telemetry wrapper fields (`request_method`, `request_headers`, `response_status`) in generated models.
- Unwraps single samples cleanly to generate native root objects.
- Injects `.parse()` and `model_validate()` callsites with strict **No-Swallow AST Verification** (rejecting silent `try/catch` or `except Exception: pass` blocks).

```bash
# Resolve all unvalidated boundaries
boundary resolve

# Target a specific source file
boundary resolve --target src/resend.ts
```

### 3. Hermetic Sandbox Replay with Ghost Proxy (`boundary verify`)
Executes the project's native test suite inside a network-isolated sandbox (using macOS `sandbox-exec` or Linux `landlock`):
- All outbound internet access is strictly blocked.
- The **Rust Ghost Proxy** (`src/ghost_proxy/`) replays captured `HttpExchange` logs locally on `127.0.0.1:54321`.
- Tests pass only if the newly synthesized schemas correctly parse the exact mock responses returned by the proxy.

```bash
boundary verify
```

### 4. Continuous Pre-Commit Guard (`boundary guard`)
Enforces boundary safety before code enters version control:
- Scans staged files for newly added unvalidated API calls.
- Blocks commits that introduce unchecked external boundaries.

```bash
boundary guard
```

---

## Enterprise CLI Workflow

```bash
# Authenticate your BYOK AI provider (Groq, OpenAI, Anthropic)
boundary auth

# Check system readiness (sandbox, compilers, AI provider)
boundary doctor

# Scan repository for unguarded boundary callsites
boundary scan

# Synthesize schemas and patch callsites
boundary resolve

# Verify repairs inside the hermetic Ghost Proxy sandbox
boundary verify
```

---

## Supported Ecosystems

| Language | Client Libraries | Generated Schema Type | Validation Engine |
| :--- | :--- | :--- | :--- |
| **TypeScript / JS** | `fetch`, `axios`, `@boundary/nextjs` | `z.object({...})` | [Zod](https://zod.dev) |
| **Python** | `requests`, `httpx`, `aiohttp` | `class Schema(BaseModel):` | [Pydantic v2](https://docs.pydantic.dev) |
| **Go** | `net/http`, `http.Client` | `type Schema struct` with JSON tags | Standard Library |

---

## Architecture

Boundary combines a native Rust engine for performance-critical tasks and Python for high-level agentic orchestration:

* **`src/ghost_proxy/`**: High-performance Axum-based local mock HTTP server that loads `HttpExchange` records and serves canned API payloads during sandboxed test execution.
* **`src/engines/rewriter.rs`**: Regex and AST-driven callsite rewriter injecting schema imports and `.parse()` validation.
* **`src/engines/graph/`**: Dependency graph mapping external providers, manifests, and AST callsites.
* **`src/sandbox/`**: OS-level network isolation enforcement (macOS `sandbox-exec`, Linux `landlock`).
* **`python/boundary/hunt.py`**: Intelligent synthesis loop with payload isolation and No-Swallow AST verifier.
* **`sdk/nextjs/`**: Edge runtime and App Router telemetry integration for Vercel/Next.js applications.

---

## License

Boundary is licensed under the [Apache License, Version 2.0](LICENSE).
