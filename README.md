# Bergendy

Runtime schemas, drafted from your live LLM API traffic.

OpenAI changes their function calling schema. Anthropic updates their response format. Your AI-generated wrapper code crashes in production.

Bergendy watches what your app actually receives, drafts Zod / Pydantic / Go schemas for it, patches your callsites via AST rewriting, and proves the result in a sandboxed replay. Zero real network. Zero side effects.

```bash
pip install bergendy

bergendy init
bergendy see          # find open LLM and external API calls
bergendy fix          # draft + patch + prove, in one command
bergendy watch        # keep it clean on main
```

## Built for LLM wrapper teams

If your code calls OpenAI, Anthropic, Groq, Mistral, or Cohere, Bergendy catches unvalidated API boundaries before the provider changes their schema and breaks your wrapper.

### Run a free scan on your own codebase

No signup. No cloud backend. No repo access needed. Just run:

```bash
pip install bergendy
cd your-project
bergendy see
```

It will show you every unvalidated external API call in your codebase. If it finds LLM API calls (OpenAI, Anthropic, etc.), you'll see exactly where they are.

Share your results with us: post a screenshot on X and tag `@bergendy`.

---

## Four verbs. That's the product.

- **See** — every external call and the real payload it returns.
- **Draft** — typed schemas, named after the resource, not the URL.
- **Patch** — rewrite callsites cleanly. AST-driven, no reformatting.
- **Prove** — replay captured traffic inside a Ghost Proxy sandbox.

Plus one passive mode: **Watch** — keep unguarded calls off `main`.

---

## The Problem

AI coding tools (Cursor, Copilot, Devin) write LLM wrapper code fast, but they leave network boundaries open: raw `fetch()`, `requests.get()`, or SDK calls casting responses to `any` or unchecked dicts. Three failure modes recur across codebases:

1. **Open Calls**: Unvalidated JSON payloads. When an upstream LLM provider or API modifies a key, adds union types, or changes nullability, code crashes at downstream access points.
2. **Context Leakage**: Generating schemas from raw telemetry envelopes causes models to hallucinate transport metadata (`request_method`, `request_headers`) rather than the actual API response object.
3. **Silent Error Swallowing**: Automated patches that wrap calls in silent `try/catch` or `except: pass` blocks pass tests in development but discard critical runtime errors in production.

Bergendy addresses all three through static AST inspection, pure payload isolation, and sandboxed replay.

---

## How It Works

```mermaid
flowchart TD
    A["Observed HTTP Traffic<br/>(.boundary/knowledge/exchanges.jsonl)"] --> B["AST Scanner<br/>(TS/JS, Python, Go)"]
    B --> C["Payload Isolation<br/>(Extracts response_body, strips envelopes)"]
    C --> D["Schema Synthesis<br/>(Zod / Pydantic / Go structs)"]
    D --> E["AST Callsite Rewriter<br/>(No-Swallow verification)"]
    E --> F["Hermetic Sandbox Replay<br/>(Kernel network block + Ghost Proxy)"]
```

### 1. See Open Calls (`bergendy see`)

Scans repository source trees across TypeScript, JavaScript, Python, and Go for external HTTP callsites lacking runtime validation:

- **TypeScript / JavaScript**: Unchecked `fetch()`, `axios.get()`, `axios.post()`, or `as any` casts.
- **Python**: Unvalidated `requests.get()`, `httpx.get()`, `aiohttp`, and unmodeled `.json()` access.
- **Go**: Unvalidated `http.Get()`, `http.Post()`, `client.Do()`, and unchecked JSON unmarshaling.

```bash
bergendy see
```

### 2. Draft and Patch Callsites (`bergendy fix`)

Extracts observed payloads and generates typed schemas without transport noise:

- **Resource-Based Naming**: Files use clean `snake_case` naming and exports use `PascalCase` ending in `Schema` (e.g. `stripe_payment_intent.ts` exports `StripePaymentIntentSchema`), never URL slugs.
- **Pure Payload Isolation**: Isolates response bodies from telemetry clusters. Transport wrappers like headers and status codes are discarded.
- **No-Swallow Verification**: Injects validation (`.parse()`, `model_validate()`) directly at the callsite. The AST rewriter rejects patches that catch validation errors silently.

```bash
# Fix all open calls in a guided workflow
bergendy fix

# Target a specific file
bergendy fix --target src/resend.ts
```

### 3. Prove with Ghost Proxy (`bergendy prove`)

Runs your existing test suite inside an isolated sandbox using macOS `sandbox-exec` or Linux `landlock`:

- Outbound socket connections to the public internet are blocked at the OS kernel level.
- Outbound requests are intercepted via the local Ghost Proxy (`127.0.0.1:54321`), serving recorded exchanges.
- Tests pass only when newly synthesized schemas parse recorded payloads with zero unhandled exceptions.

```bash
bergendy prove
```

### 4. Watch Main (`bergendy watch`)

Runs as a pre-commit hook to prevent unguarded network calls from entering source control:

```bash
# Install hook
bergendy watch --install

# Execute check against staged files
bergendy watch
```

---

## Supported Ecosystems

| Language | Client Libraries | Generated Schema Type | Validation Target |
| :--- | :--- | :--- | :--- |
| **TypeScript / JS** | `fetch`, `axios`, `openai`, `@anthropic-ai/sdk` | `z.object({...})` | [Zod](https://zod.dev) |
| **Python** | `requests`, `httpx`, `aiohttp`, `openai`, `anthropic` | `class Schema(BaseModel):` | [Pydantic v2](https://docs.pydantic.dev) |
| **Go** | `net/http`, `http.Client` | `type Schema struct` with JSON tags | Standard Library |

---

## Architecture

Bergendy combines a high-performance native Rust engine for AST transformations and kernel sandboxing with Python for orchestration and schema synthesis:

- **`src/engines/context_extractor.rs`**: AST-driven callsite context extractor (function signature, enclosing body, data flow, error handling pattern, existing imports).
- **`src/engines/ast_verifier.rs`**: 6-point deterministic AST safety verifier (syntactic balance, schema wiring, No-Swallow rule, blast radius clean, imports correct, naming conventions).
- **`src/engines/rewriter.rs`**: Polyglot AST-driven callsite rewriter injecting schema imports and validation calls.
- **`src/engines/graph/`**: Dependency graph mapping external providers, manifests, and AST callsites.
- **`src/sandbox/`**: OS-level network and filesystem isolation (macOS Seatbelt, Linux Landlock).
- **`src/ghost_proxy/server.rs`**: Local Axum-based mock HTTP server serving recorded exchanges in hermetic sandboxes.
- **`python/bergendy/hunt.py`**: Schema synthesis loop with payload isolation, AI reflection retry loop, and deterministic fallback.
- **`sdk/typescript/instrument.js`**: Node.js and fetch shim redirecting sandboxed traffic to the mock proxy.

---

## License

Bergendy is licensed under the [Apache License, Version 2.0](LICENSE).

