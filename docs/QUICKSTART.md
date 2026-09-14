# Boundary Quickstart Guide

Get up and running with Boundary in under 2 minutes.

> **“Boundary understands the changes the outside world makes to software — and repairs them.”**

---

## 1. Installation

```bash
pip install boundary
```

---

## 2. Onboarding (in under 10 seconds)

```bash
cd my-project

boundary init              # Detects repo, checks GitHub & AI, runs AST evidence scan
boundary auth              # Connect your BYOK AI provider (Anthropic, OpenAI, Ollama)
```

Outputs your repository readiness:

```text
[OK] GitHub connected (account: Devaretanmay)
[OK] Repository detected: acme/payments
[OK] Repository indexed (3 providers detected, 14 callsites mapped)
[OK] AI provider: Anthropic (claude-3-5-sonnet)
[OK] Maintenance memory initialized (.boundary/knowledge/)

READY

Boundary can now:
  Consult — find and explain maintenance issues (boundary consult)
  Work    — repair, verify, and open PRs (boundary work)
```

---

## 3. Day-0 Dependency Check & Risk Register

Immediately scan your codebase for breaking upstream changes, deprecated callsites, and auto-repairable integrations. Read-only — works with no AI credentials configured:

```bash
# Run terminal risk register:
boundary check .

# Export as GitHub Issue markdown:
boundary check . --format=github-issue

# Inspect the External-Change Dependency Graph:
boundary graph .
```

---

## 4. Consult First, Then Work (Howl & Hunt)

New teams start in Consult (Howl): same AI reasoning, zero code changes, findings filed
as a GitHub Issue. Graduate to Work (Hunt) when the reasoning earns it.

```bash
boundary consult . --repo owner/repo   # Assess only, files an Issue (Howl)
boundary check .                       # note the finding ID, e.g. stripe-3a9c79
boundary hunt stripe-3a9c79            # Repair, verify, report (Hunt)
```

See [GitHub App behavior](GITHUB_APP.md) for modes, triggers, and bot config.

## 5. Autonomous Continuous Maintenance

Run autonomous maintenance on external providers (e.g. Stripe, OpenAI, Anthropic, Clerk, AWS).
Boundary's AI reasons about the change against your repository and authors verified repairs —
there is no engine flag to choose. Unsafe repairs refuse loudly with zero files touched:

```bash
# Auto-detect provider and repair:
boundary work .

# Targeted migration and open PR:
boundary work . --provider stripe
boundary work . --provider openai --from v3.28.0 --to v4.0.0 --create-pr --repo owner/repo
```

---

## 6. Interactive Coding Agents & Sandboxed Governance (advanced)

Run terminal coding agents inside a kernel-enforced sandbox with full native TUI fidelity:

```bash
# Launch Claude Code, OpenCode, Codex, Cursor, or Aider directly:
boundary claude

# When the agent finishes:
boundary diff    # Review what the agent changed
boundary undo    # Instantly restore files if the agent made a mistake
boundary commit  # Commit to Git with verified provenance trailers
```

---

## 7. Key Guarantees

- **External Intelligence**: Full-codebase AST mapping of providers, contracts, wrappers, and callsites.
- **Continuous Maintenance**: AI-authored repairs with sandbox verification and automated Developer Trust PRs (verified repairs only; refusals are loud and empty-handed).
- **Kernel Enforcement**: Built on native OS isolation (macOS Seatbelt / Linux Landlock).
- **Credential Protection**: `~/.ssh`, `~/.aws`, `~/.config/gcloud`, git credentials, and keychains are denied by default.
- **Instant Rollback**: Hash-based BLAKE3 file snapshots allow physical restoration of modified and deleted files in 2ms.
- **Zero Infrastructure**: No Docker, no daemon, no cloud account required.
