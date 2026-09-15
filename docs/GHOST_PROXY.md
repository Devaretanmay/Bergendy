# Ghost Proxy: Hermetic Mock Server & Sandbox Replay

The **Ghost Proxy** (`src/ghost_proxy/`) is Boundary's native Rust HTTP mock server built on Axum and Tokio. It enables deterministic, offline verification of runtime schemas during sandboxed test runs.

---

## 1. Why Ghost Proxy?

When Boundary generates a new runtime validation schema (such as a Zod schema or Pydantic model) and patches your source code, it must prove that the code actually compiles and parses the real API payloads without crashing.

Running live tests against real external APIs (e.g. Stripe, OpenAI, Resend) during CI or automated repair is problematic:
1. Real API keys might not be available or could incur financial cost.
2. External services may rate-limit or fail unpredictably.
3. Tests should be deterministic and zero-blast-radius.

The Ghost Proxy solves this by replaying captured **HttpExchange** telemetry in memory inside a hermetic sandbox.

---

## 2. Architecture

```text
[Sandboxed Test Runner]
        │
        │ HTTP Request (e.g., GET https://api.resend.com/emails)
        ▼
[HTTP Client Forwarder / SDK Shim]
   - Sets header: x-boundary-original-url: https://api.resend.com/emails
   - Connects to: http://127.0.0.1:54321
        │
        ▼
[Rust Ghost Proxy (src/ghost_proxy/server.rs)]
   - Matches: method ("GET") and target_path ("/emails" or full URL)
   - Locates: recorded HttpExchange in state
   - Returns: Status (200 OK), Headers, and Response Body
        │
        ▼
[Sandboxed Application]
   - Receives exact recorded response bytes
   - Validates payload against generated Schema.parse(data)
   - Passes test cleanly without ever touching the public internet
```

---

## 3. Payload Isolation & Hermetic Guarantee

The Ghost Proxy guarantees:
* **Zero Network Leakage**: In combination with macOS `sandbox-exec` or Linux `landlock`, all outbound sockets to the public internet are blocked.
* **Payload Fidelity**: Serves strictly `exchange.response_body` bytes, matching the exact format the external API returned in production.
* **Fail-Closed on Unmocked Calls**: If the application tries to access an unrecorded endpoint, the proxy returns `404 Unmocked Boundary`, preventing unexpected network access.
