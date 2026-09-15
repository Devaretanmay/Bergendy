# Boundary CLI Reference & Command Guide

Boundary is autonomous software maintenance and runtime boundary defense for systems that change.

> **“APIs drift. Upstream payloads change. Boundary detects unguarded boundaries, synthesizes rigid schemas, and verifies them in hermetic sandboxes.”**

---

## Command Overview

```text
Core Boundary Commands:
  boundary auth                     Connect & configure BYOK AI provider (Groq, OpenAI, Anthropic)
  boundary doctor                   Verify sandbox, AI provider, compilers, and test runner readiness
  boundary scan [path]              Scan repository for exposed, unvalidated HTTP/API boundaries
  boundary resolve [path]           Synthesize schemas from traffic and patch callsites
  boundary guard                    Pre-commit hook enforcing that no unvalidated boundaries are committed
  boundary verify [path]            Run hermetic test suite with Ghost Proxy replaying canned exchanges

Advanced & Diagnostic Commands:
  boundary check [path]             Audit external dependency graph and contract drift
  boundary graph [path]             Inspect external dependency callsites and manifest linkages
  boundary init [path]              Initialize .boundary workspace metadata in current repository
  boundary app serve                Run autonomous GitHub App webhook daemon
```

---

## 1. Authentication & System Diagnostics

### `boundary auth`
Configures credentials for your preferred AI provider (BYOK). Boundary never locks you to a proprietary model.

```bash
# Interactive setup
boundary auth

# View or reset stored credentials
boundary auth --status
boundary auth --clear
```

Supported environment variables:
- `GROQ_API_KEY`: Groq API Key (recommended: fast inference for schema synthesis)
- `OPENAI_API_KEY`: OpenAI API Key
- `ANTHROPIC_API_KEY`: Anthropic API Key

Credentials are saved with `0600` permissions in `~/.boundary/credentials.json`.

---

### `boundary doctor`
Validates that your operating system environment, compilers, and AI credentials are fully operational.

```bash
boundary doctor
```

Checks performed:
- Sandbox availability (macOS `sandbox-exec` or Linux `landlock`).
- AI provider reachability and token validity.
- Local compilers and runtimes (`python3`, `node`, `go`).
- Rust Ghost Proxy socket readiness.

---

## 2. Runtime Boundary Defense Suite

### `boundary scan [path]`
Performs an AST analysis across the codebase, identifying all network boundaries where external data enters the application without strict schema validation.

```bash
# Scan current repository
boundary scan

# Scan a specific directory
boundary scan ./src
```

Supported callsites:
- **TypeScript / JavaScript**: `fetch()`, `axios.get()`, `axios.post()`, unvalidated promises, and `any` casts.
- **Python**: `requests.get()`, `httpx.get()`, `aiohttp`, and unmodeled `.json()` access.
- **Go**: `http.Get()`, `http.Post()`, `client.Do()`, and unchecked JSON unmarshaling.

---

### `boundary resolve [path] [--target <file>]`
The core automated repair command. Extracts captured HTTP response payloads, isolates the response body, prompts the AI to synthesize a strict schema, and patches the callsite.

```bash
# Resolve all unvalidated boundaries across the codebase:
boundary resolve

# Resolve a specific file:
boundary resolve --target src/resend.ts
```

Key features:
- **Payload Isolation**: Extracts only `response_body` from telemetry exchanges, completely eliminating wrapper hallucinations (`request_method`, `request_headers`).
- **No-Swallow AST Verification**: The AST patcher strictly rejects any patch that catches validation errors in silent blocks (`catch { return null }` or `except: pass`). Errors must bubble to application error handlers.
- **Polyglot Output**:
  - TypeScript: Synthesizes `z.object({...})` using Zod.
  - Python: Synthesizes `BaseModel` classes using Pydantic.
  - Go: Synthesizes typed structs with `json:"..."` tags.

---

### `boundary guard`
A lightweight, fast check designed for git pre-commit hooks or local developer workflows.

```bash
boundary guard
```

- Scans staged files for newly added unvalidated API calls.
- Exits with non-zero code if an unvalidated boundary is found.

---

### `boundary verify [path]`
Validates application code in a completely network-blocked sandbox while replaying recorded traffic through the **Ghost Proxy** (`127.0.0.1:54321`).

```bash
boundary verify
```

- Outbound public internet access is dropped.
- Requests matching recorded `HttpExchange` logs are returned by the local Axum proxy with their recorded status codes and bodies.
- Unmocked requests receive a `404 Unmocked Boundary` response.
- Verifies that newly generated schemas parse the real-world payload responses.
