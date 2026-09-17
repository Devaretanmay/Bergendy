# Bergendy CLI Reference

Bergendy provides static callsite analysis, automated schema synthesis, and sandboxed replay verification for external network requests.

---

## Command Overview

```text
The Four Verbs:
  bergendy see [path]               See what external calls return (unvalidated callsites)
  bergendy fix [path]               Draft typed schemas + patch callsites + prove in sandbox
  bergendy prove [path]             Replay recorded traffic in Ghost Proxy sandbox
  bergendy watch [path]             Pre-commit & CI gate to keep main clean

Workflow & Utilities:
  bergendy init [path]              Initialize .boundary metadata in current repository
  bergendy status                   Show workspace and repository connection status
  bergendy auth                     Configure BYOK AI provider (OpenAI, Anthropic, Groq)
  bergendy doctor                   Verify setup, AI provider, and test runner readiness
```

---

## 1. Authentication and Environment Setup

### `bergendy auth`
Configures credentials for your AI provider (BYOK: Bring Your Own Key).

```bash
# Interactive setup
bergendy auth

# Check status or clear credentials
bergendy auth --status
bergendy auth --clear
```

Supported environment variables:
- `GROQ_API_KEY`: Groq API Key
- `OPENAI_API_KEY`: OpenAI API Key
- `ANTHROPIC_API_KEY`: Anthropic API Key

Credentials are saved with `0600` file permissions in `~/.boundary/credentials.json`.

---

### `bergendy doctor`
Checks operating system environment, compilers, and credential configuration.

```bash
bergendy doctor
```

Verification checks:
- Kernel sandbox support (macOS `sandbox-exec` or Linux `landlock`).
- AI provider connectivity and token validity.
- Local compilers and runtimes (`python3`, `node`, `go`).
- Mock proxy port availability (`127.0.0.1:54321`).

---

## 2. Core Verbs & Workflow

### `bergendy see [path]` (aliases: `check`, `scan`)
Performs AST analysis to identify external network requests lacking runtime schema validation:

```bash
# See open calls in repository root
bergendy see

# See open calls in a target directory
bergendy see ./src
```

Supported callsites:
- **TypeScript / JavaScript**: `fetch()`, `axios.get()`, `axios.post()`, unvalidated promises, and `any` casts.
- **Python**: `requests.get()`, `httpx.get()`, `aiohttp`, and unmodeled `.json()` access.
- **Go**: `http.Get()`, `http.Post()`, `client.Do()`, and unchecked JSON unmarshaling.

---

### `bergendy fix [path]`
Single guided command: drafts typed runtime schemas from live telemetry, patches callsites losslessly, and proves changes in the sandbox.

```bash
# Guided interactive fix across codebase
bergendy fix

# Automatically apply and prove
bergendy fix -y
```

### `bergendy patch [path] [--target <file>]` (alias: `resolve`)
Drafts rigid schemas from recorded traffic and patches callsites using native AST rewrites:

```bash
# Patch all open calls
bergendy patch

# Patch a specific file
bergendy patch --target src/resend.ts
```

Behavior:
- **AST Context Extraction**: Extracts function signature, callsite coordinates, data flow, and error handling pattern.
- **Payload Isolation**: Extracts only `response_body` from telemetry exchanges, discarding transport metadata (`request_method`, `request_headers`).
- **6-Point AST Verification**: Rejects patches that violate syntactic balance, fail to wire the schema, suppress errors silently (No-Swallow Rule), exceed blast radius, corrupt imports, or violate resource naming conventions.
- **Self-Repair Retry Loop**: In case of verification failure, feeds deterministic compiler diagnostics back into the AI model for up to 3 reflection attempts before falling back to the zero-token deterministic rewriter.
- **Resource Naming**: Emits `snake_case` file schemas (`stripe_payment_intent.ts`) exporting `PascalCase` types (`StripePaymentIntentSchema`).

---

### `bergendy watch` (aliases: `gate`, `guard`)
Pre-commit hook and CI gate that ensures zero open external calls in staged code:

```bash
# Install hook to .git/hooks/pre-commit
bergendy watch --install

# Run check on currently staged files
bergendy watch

# Run check on specific files (used by pre-commit framework or CI)
bergendy watch --files src/api.ts src/client.py --ci
```

---

### `bergendy prove [path]` (alias: `verify`)
Executes the native test suite inside a network-isolated sandbox with Ghost Proxy replay:

```bash
bergendy prove
```

- Public internet access is blocked at the OS kernel level.
- Recorded exchanges are replayed locally via `127.0.0.1:54321`.
- Unmocked requests receive `404 Unmocked Boundary`.
- Tests pass only when synthesized schemas parse recorded payload bytes without error.
