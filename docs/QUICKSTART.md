# Bergendy Quickstart Guide

Get up and running with Bergendy runtime schema synthesis and sandboxed proof in under two minutes.

---

## 1. Installation

Install Bergendy from PyPI:

```bash
pip install bergendy
```

Or build from source:

```bash
git clone https://github.com/Devaretanmay/Boundary.git
cd Boundary
maturin develop --release
```

---

## 2. Authentication (BYOK)

Configure your preferred AI provider (OpenAI, Anthropic, or Groq):

```bash
# Interactive setup
bergendy auth

# Or set via environment variables:
export ANTHROPIC_API_KEY="your-api-key"
# or
export OPENAI_API_KEY="your-api-key"
```

Verify your environment:

```bash
bergendy doctor
```

Example output:
```text
System Readiness Check
  [OK] Sandbox environment: macOS sandbox-exec supported
  [OK] AI provider: Anthropic (claude-3-5-sonnet-20241022)
  [OK] Ghost Proxy: Ready (127.0.0.1:54321)
  [OK] Compilers detected: python3, node, go
```

---

## 3. The Four Verbs Workflow

### 1. See: Find Open External Calls
Scan your repository for external HTTP requests lacking runtime schema validation:

```bash
bergendy see
```

Example output:
```text
Open Calls (Unvalidated External Requests)
  src/resend.ts:116:1
  ├─ Endpoint: https://api.resend.com/emails
  ├─ Status:   Unvalidated response payload
  └─ Action:   Run `bergendy fix --target src/resend.ts`

  weather.py:12:1
  ├─ Endpoint: https://api.weatherapi.com/v1/current.json
  ├─ Status:   Unvalidated response payload
  └─ Action:   Run `bergendy fix --target weather.py`
```

---

### 2. Fix: Draft Schemas and Patch Callsites
Run the guided interactive flow to draft schemas from captured traffic, patch callsites losslessly, and prove changes:

```bash
# Guided single command:
bergendy fix
```

What Bergendy does:
1. **Extracts traffic telemetry**: Reads captured HTTP spans from `.boundary/knowledge/exchanges.jsonl`.
2. **Isolates payload context**: Extracts solely `response_body`, stripping transport wrappers (`request_method`, `request_headers`).
3. **Drafts typed schema**:
   - TypeScript: Strict **Zod** schema (`z.object({...})`). Named by resource: `snake_case` file (`resend_email.ts`) exporting PascalCase (`ResendEmailSchema`).
   - Python: Strict **Pydantic** model (`class ResendEmailSchema(BaseModel):`).
   - Go: Typed **Go struct** with json tags.
4. **Patches callsite**: Injects validation (`.parse()`, `model_validate()`) verified with the **No-Swallow Rule** (rejects silent `try/catch` or `except: pass` error suppressors).
5. **Proves against Ghost Proxy**: Replays the captured traffic inside an isolated sandbox.

---

### 3. Prove: Replay in Ghost Proxy Sandbox
Run verification tests inside a network-blocked sandbox where external calls are replayed locally:

```bash
bergendy prove
```

Output:
```text
Running Sandbox Replay (Ghost Proxy)...
   [OK] Ghost Proxy active on 127.0.0.1:54321
   [OK] Outbound network traffic restricted
   [OK] Replaying 3 captured API exchanges
   [OK] Test suite passed: `npm test`

Proof Complete.
   Zero blast radius. All schemas parse verified replay payloads.
   Changes ready in working tree.
```

---

### 4. Watch: Pre-Commit & CI Gate
Enforce that zero open external calls enter your git history:

```bash
# Install git hook
bergendy watch --install

# Test staged changes manually
bergendy watch
```

If any staged file contains an unchecked external HTTP call, Bergendy halts the commit and points directly to the open callsite.
