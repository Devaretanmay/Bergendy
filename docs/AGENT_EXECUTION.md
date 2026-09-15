# Boundary Agent Execution & Terminal TUI Supervision

Boundary enables developers to run interactive terminal coding agents (Claude Code, OpenCode, Codex, Cursor, Aider) inside an OS kernel sandbox with zero configuration.

---

## 1. Direct Agent Execution

Launch your agent directly inside an isolated sandbox:

```bash
boundary claude
boundary opencode
boundary codex
boundary cursor
boundary aider
```

Boundary automatically:
1. Detects the genuine binary on system `PATH`.
2. Allocates a pseudo-terminal master/slave pair (`PtySupervisor`).
3. Takes a pre-execution BLAKE3 workspace snapshot.
4. Applies OS kernel sandboxing (Seatbelt on macOS / Landlock on Linux) in the child process.
5. Bridges terminal I/O so the native agent TUI displays with full fidelity.

---

## 2. PTY Supervision & Native Terminal Fidelity

Interactive agents rely on advanced terminal features that standard process pipes break:
- **Alternate Screen Buffer** (full-screen rendering)
- **ANSI 256 / TrueColor Support**
- **Window Resize Events** (`TIOCGWINSZ` / `SIGWINCH`)
- **Signal Forwarding** (Ctrl+C for cancellation, Ctrl+D for EOF)
- **Raw Input Mode** (instant keystroke response without enter buffering)

Boundary's `PtySupervisor` bridges these capabilities directly so the agent runs identically to a bare-metal session.

---

## 3. Sandboxing & Credential Boundaries

When the agent runs, the OS kernel strictly restricts process syscalls:

| Resource | Default Policy | Enforced Behavior |
| :--- | :--- | :--- |
| **Workspace Tree** | Read & Write | Agent can read codebase files and apply edits freely. |
| **Host SSH Keys** | Blocked | Any read to `~/.ssh` or `id_rsa` fails with `PermissionError`. |
| **Cloud Configs** | Blocked | Access to `~/.aws`, `~/.config/gcloud`, `~/.azure` denied. |
| **System Paths** | Read-Only | `/usr`, `/lib`, `/bin` are read-only; writes to root are rejected. |
| **External Network** | Governed | Outbound sockets restricted unless granted by compartment policy. |

---

## 4. Review & Rollback Lifecycle

After the agent completes its task:

```bash
# 1. Review file changes attributed by execution
boundary diff

# 2. Promote changes to workspace baseline
boundary apply

# 3. Commit with provenance trailers
boundary commit -m "feat(auth): add OAuth provider"

# 4. If the agent made a mistake, rollback instantly
boundary undo
```
