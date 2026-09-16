# Boundary CLI Reference

Boundary provides static boundary analysis, automated schema synthesis, and sandboxed replay verification for external network callsites.

---

## Command Overview

```text
Core Commands:
  boundary auth                     Configure BYOK AI provider credentials (Groq, OpenAI, Anthropic)
  boundary doctor                   Check environment, sandbox, compiler, and credential readiness
  boundary scan [path]              Scan codebase for unvalidated external HTTP callsites
  boundary resolve [path]           Synthesize schemas from recorded traffic and patch callsites
  boundary guard                    Pre-commit hook blocking unvalidated external network callsites
  boundary verify [path]            Run test suite in network-isolated sandbox replaying mock traffic

Diagnostic and Maintenance Commands:
  boundary check [path]             Audit external dependency graph and contract drift
  boundary graph [path]             Inspect external dependency callsites and manifest linkages
  boundary init [path]              Initialize .boundary workspace metadata in current repository
  boundary app serve                Run GitHub App webhook daemon
```

---

## 1. Authentication and Environment Setup

### `boundary auth`
Configures credentials for your AI provider (BYOK: Bring Your Own Key).

```bash
# Interactive setup
boundary auth

# Check status or clear credentials
boundary auth --status
boundary auth --clear
```

Supported environment variables:
- `GROQ_API_KEY`: Groq API Key
- `OPENAI_API_KEY`: OpenAI API Key
- `ANTHROPIC_API_KEY`: Anthropic API Key

Credentials are saved with `0600` file permissions in `~/.boundary/credentials.json`.

---

### `boundary doctor`
Checks operating system environment, compilers, and credential configuration.

```bash
boundary doctor
```

Verification checks:
- Kernel sandbox support (macOS `sandbox-exec` or Linux `landlock`).
- AI provider connectivity and token validity.
- Local compilers and runtimes (`python3`, `node`, `go`).
- Mock proxy port availability (`127.0.0.1:54321`).

---

## 2. Boundary Defense Commands

### `boundary scan [path]`
Performs AST analysis to identify external network boundaries lacking runtime schema validation:

```bash
# Scan repository root
boundary scan

# Scan a target directory
boundary scan ./src
```

Supported callsites:
- **TypeScript / JavaScript**: `fetch()`, `axios.get()`, `axios.post()`, unvalidated promises, and `any` casts.
- **Python**: `requests.get()`, `httpx.get()`, `aiohttp`, and unmodeled `.json()` access.
- **Go**: `http.Get()`, `http.Post()`, `client.Do()`, and unchecked JSON unmarshaling.

---

### `boundary resolve [path] [--target <file>]`
Synthesizes rigid schemas from recorded traffic and patches callsites using native AST rewrites:

```bash
# Resolve all unvalidated boundaries
boundary resolve

# Resolve a specific file
boundary resolve --target src/resend.ts
```

Behavior:
- **Payload Isolation**: Extracts only `response_body` from telemetry exchanges, discarding transport metadata (`request_method`, `request_headers`).
- **No-Swallow Verification**: Rejects patches that suppress validation errors silently (`catch { return null }` or `except: pass`). Errors must bubble to application error handlers.
- **Output Targets**:
  - TypeScript: `z.object({...})` via Zod.
  - Python: `BaseModel` classes via Pydantic v2.
  - Go: Struct definitions with `json:"..."` tags.

---

### `boundary guard`
Pre-commit hook and CI gate that validates staged files:

```bash
# Install hook to .git/hooks/pre-commit
boundary guard --install

# Run check on currently staged files
boundary guard

# Run check on specific files (used by pre-commit framework or CI)
boundary guard --files src/api.ts src/client.py --ci
```

#### Pre-commit Framework Configuration (`.pre-commit-config.yaml`)
```yaml
repos:
  - repo: https://github.com/Devaretanmay/Boundary
    rev: v1.1.3
    hooks:
      - id: boundary-guard
```

#### GitHub Actions Workflow Example (`.github/workflows/boundary.yml`)
```yaml
name: boundary-guard
on:
  pull_request:
  push:
    branches: [main]

jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Devaretanmay/Boundary@main
        with:
          command: guard
```

- Blocks commits and PRs that introduce unvalidated external HTTP callsites across TypeScript, Python, and Go.
- Exits 0 when all staged network calls pass validation.

---

### `boundary verify [path]`
Executes the native test suite inside a network-isolated sandbox with mock proxy replay:

```bash
boundary verify
```

- Public internet access is blocked at the OS kernel level.
- Recorded exchanges are replayed locally via `127.0.0.1:54321`.
- Unmocked requests receive `404 Unmocked Boundary`.
- Tests pass only when synthesized schemas parse recorded payload bytes without error.
