# Boundary Quickstart Guide

Get up and running with Boundary runtime boundary defense in under 2 minutes.

> **“APIs drift. Upstream payloads change. Boundary detects unguarded boundaries, synthesizes rigid schemas, and verifies them in hermetic sandboxes.”**

---

## 1. Installation

Install Boundary from PyPI:

```bash
pip install boundary
```

Or build from source with the native Rust engine:

```bash
git clone https://github.com/Devaretanmay/Boundary.git
cd Boundary
maturin develop --release
```

---

## 2. Authentication (BYOK)

Configure your AI provider API key (Groq, OpenAI, or Anthropic):

```bash
# Interactive setup:
boundary auth

# Or export via environment variable:
export GROQ_API_KEY="your-api-key"
# or
export OPENAI_API_KEY="your-api-key"
```

Verify your environment readiness:

```bash
boundary doctor
```

Outputs:
```text
System Readiness Check
  [OK] Sandbox environment: macOS sandbox-exec supported
  [OK] AI provider: Groq (openai/gpt-oss-120b)
  [OK] Ghost Proxy: Ready (127.0.0.1:54321)
  [OK] Compilers detected: python3, node, go
```

---

## 3. Step-by-Step Workflow

### Step 1: Scan for Unvalidated Boundaries
Scan your repository for external HTTP callsites that lack runtime schema validation or use unsafe casts:

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
Synthesize rigid schemas from captured runtime traffic and patch the callsites:

```bash
# Resolve all detected boundaries:
boundary resolve

# Or resolve a specific file:
boundary resolve --target src/resend.ts
```

What Boundary does:
1. **Extracts traffic telemetry**: Loads captured HTTP spans.
2. **Isolates payload context**: Extracts only `response_body` (ensuring zero wrapper fields like `request_method` or `request_headers` pollute the schema).
3. **Synthesizes typed schema**:
   - TypeScript: Strict **Zod** schema (`z.object({...})`).
   - Python: Strict **Pydantic** model (`class Schema(BaseModel):`).
   - Go: Typed **Go struct** with json tags.
4. **Patches callsite**: Rewrites code to call `.parse()`, `model_validate()`, or typed unmarshaling, verified with the **No-Swallow AST Rule** (no silent error suppression).
5. **Replays against Ghost Proxy**: Validates the newly patched code in an isolated sandbox.

---

### Step 3: Verify in Hermetic Sandbox
Run verification tests inside a network-blocked sandbox where external calls are replayed locally by the Rust Ghost Proxy:

```bash
boundary verify
```

Output:
```text
Verification Environment (Sandbox)
  ├─ Network:   Isolated (Ghost Proxy active on 127.0.0.1:54321)
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
Add Boundary to your pre-commit workflow to prevent unvalidated API calls from ever reaching production:

```bash
boundary guard
```

If any staged file contains an unchecked external HTTP call, Boundary halts the commit and points directly to the exposed line.
