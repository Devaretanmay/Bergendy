# Y Combinator Application Draft: Bergendy

## Company Information
* **Company Name:** Bergendy
* **Company URL:** https://github.com/Devaretanmay/Bergendy
* **PyPI Package:** https://pypi.org/project/bergendy/

---

## 1. What does your company do? (50 characters or less)
Bergendy prevents LLM wrapper code from breaking.

---

## 2. What is your company going to make? (Detailed description)
Bergendy is an autonomous runtime-schema tool for AI-generated codebases and LLM wrappers.

When developers use AI coding tools (Cursor, Copilot, Devin) to build apps on top of OpenAI, Anthropic, or external REST APIs, the tools generate "happy path" code — raw `fetch()`, `requests.get()`, or SDK calls that cast JSON payloads to `any` or unchecked dictionaries. When upstream providers change their function calling definitions, return union types, or alter payload nullability, production apps crash at downstream access points.

Bergendy watches what an application actually receives over the wire, drafts rigid runtime schemas (Zod for TypeScript, Pydantic v2 for Python, typed structs for Go), rewrites callsites at the AST level to inject `.parse()` validation, and proves the result in a kernel-isolated Ghost Proxy sandbox with zero real network egress.

---

## 3. What problem are you solving?
AI coding assistants are generating vast amounts of unvalidated code. While compilers check internal static types, network boundaries remain completely untyped at runtime:
1. **Open Calls**: Raw JSON responses are trusted blindly. When LLM providers drift (e.g. function-call arguments formatting, newly added fields, token usage structures), wrapper code fails silently or crashes in production.
2. **Context Leakage**: Naive schema generators incorporate transport metadata (HTTP headers, status codes) into data models rather than the pure response payload.
3. **Silent Error Swallowing**: Automated AI fixes often wrap calls in `try/catch` or `except: pass` blocks that mask defects instead of surfacing validation errors.

---

## 4. How does it work? (Architecture)
1. **Inspection (`bergendy see`)**: A polyglot AST scanner discovers unvalidated external HTTP callsites and SDK invocations across TypeScript, Python, and Go.
2. **Telemetry Ingestion**: OpenTelemetry SDK shims capture live HTTP exchanges into `.boundary/knowledge/exchanges.jsonl`.
3. **Payload Isolation**: The engine extracts pure `response_body` payloads, stripping all HTTP transport envelopes and deduplicating clusters.
4. **Schema Synthesis**: Generates strict, resource-named schemas (`snake_case` files exporting `PascalCase` schemas, e.g. `PaymentIntentsSchema`). Zero-token deterministic synthesis fallback guarantees offline execution without API keys.
5. **AST Callsite Rewriting (`src/engines/rewriter.rs`)**: A native Rust rewriter injects schema imports and validation calls (`Schema.parse(await res.json())`). It strictly enforces the No-Swallow rule, rejecting any patch that suppresses errors silently.
6. **Hermetic Replay Proof (`bergendy prove`)**: Executes the repository's native test suite inside an OS kernel sandbox (macOS Seatbelt / Linux Landlock). Outbound internet access is blocked; all requests are served by the local Rust Ghost Proxy (`127.0.0.1:54321`) from recorded traffic.

---

## 5. Traction
* **Self-Serve Distribution:** Released on PyPI (`pip install bergendy`). Fully self-contained local binary requiring zero cloud backend and zero repository access permissions.
* **Cold-Start Validation:** Self-serve scan (`bergendy see`) allows any developer to inspect their own codebase locally in 10 seconds.
* **Verified Traction Metrics:**
  * *[To be populated with verifiable numbers from the self-serve launch]*:
    * Total self-serve scans executed: `[X]`
    * Total unvalidated LLM/API boundaries detected: `[Y]`
    * Teams testing `bergendy watch` in CI: `[Z]`
  * Full test suite: 599 automated tests passing (125 Rust core + 474 Python + Ruff lint).

---

## 6. Why did you choose to build this? (Founder-Market Fit)
I built Bergendy because I was repeatedly fixing production outages caused by unvalidated AI-generated code. As coding agents accelerate development velocity, they write code without runtime boundary defense. Manually authoring Zod schemas and Pydantic models for dozens of third-party endpoints is tedious and often neglected until an API drifts and breaks production. I wanted a compiler-adjacent tool that observes real traffic, drafts the exact schemas, patches callsites cleanly, and proves the result without touching live APIs.

---

## 7. How will you make money?
* **Open Source Core:** Local CLI (`see`, `fix`, `prove`, `watch`) is freely available for individual developers and local projects.
* **Enterprise / Team Tier:**
  * Hosted GitHub App with automatic PR review and drift detection.
  * Centralized schema registry and team-wide contract drift alerts.
  * Enterprise CI compliance enforcement with SOC2 audit trails for AI-generated code provenance.
