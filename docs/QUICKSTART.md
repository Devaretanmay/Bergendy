# Boundary Quickstart Guide

Get up and running with Boundary runtime boundary defense in under two minutes.

---

## 1. Installation

Install Boundary from PyPI:

```bash
pip install boundary
```

Or build from source:

```bash
git clone https://github.com/Devaretanmay/Boundary.git
cd Boundary
maturin develop --release
```

---

## 2. Authentication (BYOK)

Configure your preferred AI provider (Groq, OpenAI, or Anthropic):

```bash
# Interactive setup
boundary auth

# Or set via environment variables:
export GROQ_API_KEY="your-api-key"
# or
export OPENAI_API_KEY="your-api-key"
```

Verify your environment:

```bash
boundary doctor
```

Example output:
```text
System Readiness Check
  [OK] Sandbox environment: macOS sandbox-exec supported
  [OK] AI provider: Groq (openai/gpt-oss-120b)
  [OK] Mock Proxy: Ready (127.0.0.1:54321)
  [OK] Compilers detected: python3, node, go
```

---

## 3. Step-by-Step Workflow

### Step 1: Scan for Unvalidated Boundaries
Scan your repository for external HTTP callsites lacking runtime schema validation:

```bash
boundary scan
```

Example output:
```text
Scanning runtime boundaries in .
  [EXPOSED] src/resend.ts:116 -> https://api.resend.com/emails (no schema validation)
  [EXPOSED] weather.py:12 -> https://api.weatherapi.com/v1/current.json (untyped dict access)
  [EXPOSED] tools/auth/gitee.go:106 -> https://gitee.com/api/v5/emails (unchecked struct unmarshal)

Scan Summary:
  Files Scanned:          42
  Exposed Boundaries:     3
  Auto-Resolvable:        3
```

---

### Step 2: Resolve Unvalidated Boundaries
Synthesize rigid schemas from captured runtime traffic and patch callsites:

```bash
# Resolve all detected boundaries:
boundary resolve

# Or target a specific file:
boundary resolve --target src/resend.ts
```

What Boundary does:
1. **Extracts traffic telemetry**: Reads captured HTTP spans from `.boundary/knowledge/exchanges.jsonl`.
2. **Isolates payload context**: Extracts solely `response_body`, stripping transport wrappers (`request_method`, `request_headers`).
3. **Synthesizes typed schema**:
   - TypeScript: Strict **Zod** schema (`z.object({...})`).
   - Python: Strict **Pydantic** model (`class Schema(BaseModel):`).
   - Go: Typed **Go struct** with json tags.
4. **Patches callsite**: Injects validation (`.parse()`, `model_validate()`) verified with the **No-Swallow Rule** (rejects silent `try/catch` or `except: pass` error suppressors).
5. **Replays against Mock Proxy**: Verifies the patched code inside an isolated sandbox.

---

### Step 3: Verify in Hermetic Sandbox
Run verification tests inside a network-blocked sandbox where external calls are replayed locally:

```bash
boundary verify
```

Output:
```text
Verification Environment (Sandbox)
  ├─ Network:   Isolated (Mock Proxy active on 127.0.0.1:54321)
  ├─ Replaying: 3 captured HTTP exchanges
  └─ Executing: `npm test`

  [PASS] verification tests passed

Resolution Complete
  ├─ Schemas generated: 1
  ├─ Files patched:     1
  └─ Sandboxed verify:  Passed
```

---

### Step 4: Pre-Commit Guard
Add Boundary to your pre-commit workflow:

```bash
# Install git hook
boundary guard --install

# Test manually
boundary guard
```

If any staged file contains an unchecked external HTTP call, Boundary halts the commit and points directly to the exposed line.
