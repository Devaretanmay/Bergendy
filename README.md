<div align="center">

# Bergendy

**Runtime schemas, drafted from your live traffic.**

[![PyPI version](https://img.shields.io/pypi/v/bergendy)](https://pypi.org/project/bergendy/)
[![Rust](https://img.shields.io/badge/Rust-000000?logo=rust)](https://www.rust-lang.org/)
[![Python](https://img.shields.io/badge/Python-3776AB?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue)](LICENSE)
[![CI](https://github.com/Devaretanmay/Bergendy/actions/workflows/ci.yml/badge.svg)](https://github.com/Devaretanmay/Bergendy/actions)

AI coding tools write code 10x faster, but they skip runtime validation.
When OpenAI or Anthropic changes their API schema, your AI-generated wrapper crashes in production.

Bergendy watches live LLM API traffic, drafts typed schemas, patches your code via AST rewriting,
and verifies the result in a kernel-isolated sandbox.

**No API key required. Works offline. AI enhances, deterministic guarantees the baseline.**

[Quick Start](#-quick-start) • [How It Works](#-how-it-works) • [Architecture](#-architecture) • [Examples](#-examples)

</div>

---

## 🎬 Demo

<!-- REPLACE WITH ACTUAL DEMO GIF -->
<!-- Record a 60-second terminal GIF showing: bergendy see → bergendy fix → bergendy prove -->
![Bergendy Demo](assets/demo.gif)

---

## 🚀 Quick Start

```bash
# Install
pip install bergendy

# Initialize in your project
bergendy init

# Find unvalidated external API calls
bergendy see

# Draft schemas, patch callsites, verify in sandbox — one command
bergendy fix

# Keep it clean on main (pre-commit hook)
bergendy watch --install
```

**That's it.** Bergendy works fully offline. No API keys, no servers, no data leaves your machine.

---

## 💡 The Problem

Every modern application calls external APIs — payment gateways, AI providers, third-party services. When those APIs change, your app breaks:

| Failure Mode | What Happens | Real Cost |
| :--- | :--- | :--- |
| **Unvalidated Boundaries** | `fetch()` calls cast JSON to `any` or unchecked structs | Crash at downstream access points |
| **Schema Drift** | API changes a field name, adds nullability | Silent data corruption |
| **AI-Generated Code** | AI writes "happy path" code, skips defensive validation | Production crashes at 3am |

**Bergendy catches all three before they ship.**

---

## 🔧 How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BERGENDY HYBRID PIPELINE                         │
└─────────────────────────────────────────────────────────────────────┘

[1] AST ANALYSIS (Deterministic)
    Tree-sitter parsing → Repo map → Precise context extraction
    Traffic aggregation (isolated response_body only)
         ↓
[2] AI GENERATION (Agentic, Optional)
    Structured prompt with precise context (~800 tokens)
    AI generates: schema + patch + import
    Falls back to deterministic synthesizer if offline
         ↓
[3] AST VERIFICATION (Deterministic Safety Gate)
    6-point verification: syntactic validity, schema wired,
    no silent catch, blast radius clean, imports correct, naming valid
         ↓
[4] SANDBOX VERIFICATION (Behavioral Proof)
    Ghost Proxy replays captured traffic locally
    Blocks all outbound network (Seatbelt/Landlock)
    Runs your test suite — zero real API calls
         ↓
[5] ROLLBACK (Instant Undo)
    BLAKE3 snapshots → 2ms instant rollback on failure
```

**AI is completely optional.** If no LLM client is available, Bergendy uses its native Rust and Python deterministic engines to synthesize schemas and patch code with zero API calls.

---

## 📊 Supported Ecosystems

| Language | Client Libraries | Generated Schema Type | Validation Target |
| :--- | :--- | :--- | :--- |
| **TypeScript / JS** | `fetch`, `axios`, `openai`, `@anthropic-ai/sdk` | `z.object({...})` | Zod |
| **Python** | `requests`, `httpx`, `openai`, `anthropic` | `class Schema(BaseModel):` | Pydantic v2 |
| **Go** | `net/http`, `http.Client` | `type Schema struct` with JSON tags | Standard Library |

---

## 🛡️ Safety Guarantees

Bergendy never modifies your code without proof. Every patch is:

1. **AST-verified** — 6 deterministic checks before any code is written
2. **Sandbox-tested** — Runs in kernel isolation with zero real network
3. **Instantly reversible** — BLAKE3 snapshots enable 2ms rollback
4. **No silent failures** — Rejects patches that swallow errors in try/catch

---

## 📦 Examples

### Example 1: Unvalidated Stripe Call → Patched

**Before:**
```typescript
// src/services/stripe.ts
export async function getPaymentIntent(id: string) {
  const response = await fetch(`https://api.stripe.com/v1/payment_intents/${id}`);
  const data = await response.json(); // ← Unvalidated! Crashes when Stripe changes schema
  return data;
}
```

**After `bergendy fix`:**
```typescript
// src/services/stripe.ts
import { StripePaymentIntentSchema } from './schemas/stripe_payment_intent';

export async function getPaymentIntent(id: string) {
  const response = await fetch(`https://api.stripe.com/v1/payment_intents/${id}`);
  const data = StripePaymentIntentSchema.parse(await response.json());
  return data;
}
```

**Generated Schema (`src/schemas/stripe_payment_intent.ts`):**
```typescript
import { z } from 'zod';

export const StripePaymentIntentSchema = z.object({
  id: z.string().startsWith('pi_'),
  amount: z.number().int(),
  currency: z.string(),
  status: z.enum(['succeeded', 'processing', 'failed']),
  created: z.number().int(),
});

export type StripePaymentIntent = z.infer<typeof StripePaymentIntentSchema>;
```

### Example 2: Unvalidated OpenAI Call → Patched

**Before:**
```python
# src/ai/agent.py
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}],
)
data = response.json()  # ← Unvalidated! Crashes when OpenAI changes response format
```

**After `bergendy fix`:**
```python
# src/ai/agent.py
from src.schemas.openai_chat_response import OpenAIChatResponseSchema

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}],
)
data = OpenAIChatResponseSchema.model_validate_json(response.text)
```

---

## 🏗️ Architecture

```
Bergendy
├── src/ (Rust Core)
│   ├── ast/                  # Polyglot AST analysis & call-site locators
│   ├── contracts/            # Contract synthesis and schema diff engines
│   ├── engines/              # Dependency graphs, AST rewriter, verifier
│   ├── ghost_proxy/          # Axum-based local mock HTTP server
│   ├── sandbox/              # Seatbelt (macOS) & Landlock (Linux) isolation
│   └── py_bindings.rs        # PyO3 C FFI bridge
│
├── python/bergendy/ (Python Orchestrator)
│   ├── cli/                  # CLI commands (see, fix, prove, watch)
│   ├── hunt.py               # Autonomous repair loop with retry
│   ├── prompts/              # Structured AI prompt templates
│   └── sandbox/              # Process sandboxing, snapshot rollback
│
├── sdk/ (Language SDKs)
│   ├── nextjs/               # Next.js App Router & Edge telemetry
│   └── typescript/           # Node.js fetch/axios instrumentation
│
└── tests/ (599 passing tests)
    ├── boundary/             # Sandbox & isolation tests
    └── test_e2e_golden_run.py # End-to-end integration tests
```

---

## 🧪 Running Tests

```bash
# Run all tests
./scripts/run_all_tests.py

# Run Rust tests only
cargo test --lib --features oxc_flow

# Run Python tests only
pytest tests/

# Run linter
ruff check python/ tests/
```

**Current status:** 599 tests passing (125 Rust + 474 Python), CI green.

---

## 🤝 Contributing

We welcome contributions! Here's how:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run the test suite (`./scripts/run_all_tests.py`)
5. Commit and push (`git commit -m 'feat: add amazing feature'`)
6. Open a Pull Request

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📜 License

Bergendy is licensed under the [Apache License 2.0](LICENSE).

---

## 🙏 Acknowledgments

- [tree-sitter](https://tree-sitter.github.io/) for polyglot AST parsing
- [axum](https://github.com/tokio-rs/axum) for the Ghost Proxy server
- [pyo3](https://github.com/PyO3/pyo3) for Rust-Python bindings
- The AI coding community for highlighting the schema drift problem

---

<div align="center">

**Made with 🍷 by developers, for developers.**

[Report Bug](https://github.com/Devaretanmay/Bergendy/issues) • [Request Feature](https://github.com/Devaretanmay/Bergendy/issues) • [Discussions](https://github.com/Devaretanmay/Bergendy/discussions)

</div>
