# Bergendy Virtual Agent Lanes & Integration Architecture

Bergendy introduces **Virtual Agent Lanes**-the developer workspace abstraction for AI agents.

```text
BERGENDY WORKSPACE
   │
   ├── Agent Sessions & Virtual Lanes
   │   ├── Lane: auth-fix  (Claude Code)  -> Changes: [src/auth.py]
   │   ├── Lane: logging   (OpenCode)     -> Changes: [src/logger.py]
   │   └── Lane: tests     (Codex)        -> Changes: [tests/test_auth.py]
   │
   ├── Integration Engine
   │   ├── bergendy integrate create auth-fix logging
   │   ├── bergendy integrate preview
   │   └── bergendy integrate apply
   │
   └── Kernel Execution Isolation
       ├── Landlock (Linux) / Seatbelt (macOS) Process Sandboxing
       ├── Deny-by-default credential protection (~/.ssh, ~/.aws)
       └── BLAKE3 File Diff Snapshots
```

---

## Invariants

- `1 AgentSession -> 1 Agent`
- `1 AgentSession -> 1 Lane`
- `1 Lane -> 1 Compartment execution boundary`
- `1 Workspace -> Many Lanes`
- `1 Workspace -> Many Sessions`
- `1 Lane -> Many Checkpoints`
- `1 Session -> Many Changes`
- *Ownership rule*: A lane owns identity, agent session, compartment execution boundary, filesystem diff tree, changes, checkpoints, and lifecycle.

---

## CLI Usage Guide

### 1. Running Concurrent Agent Lanes
```bash
# Agent 1 (Claude Code) in 'auth-fix' lane
bergendy wrap --agent "Claude Code" --task "Fix authentication bug" --lane auth-fix -- claude

# Agent 2 (OpenCode) in 'logging' lane concurrently
bergendy wrap --agent "OpenCode" --task "Add structured logging" --lane logging -- opencode
```

### 2. Inspecting Workspace Lanes
```bash
bergendy lanes
bergendy lane inspect auth-fix
```

### 3. Combining & Integrating Lanes
```bash
# Create integration candidate combining auth-fix and logging
bergendy integrate create auth-fix logging

# Preview candidate diffs and conflict status
bergendy integrate preview

# Apply cleanly to workspace
bergendy integrate apply
```

---

## Reviewing, Applying & Recovering Agent Changes

Every governed execution records a **change set** (BLAKE3 file diffs attributed to its Execution ID). The Git-like commands manage those change sets:

```bash
# Review what agents changed (filter by execution, or --unapplied for pending work)
bergendy diff
bergendy diff --execution exec_1723635840000
bergendy diff --unapplied

# Promote a change set into the workspace baseline.
# Overlapping changes from other un-applied executions surface as conflicts;
# --force applies anyway.
bergendy apply
bergendy apply --execution exec_1723635840000

# Reverse the last apply operation (or a specific one)
bergendy undo
bergendy undo --execution exec_1723635840000

# Restore the workspace from a session's pre-execution snapshot checkpoint
bergendy restore sess_1723635840000

# Roll back a session (restores its snapshot and marks it ROLLED_BACK)
bergendy session rollback sess_1723635840000
```

**Semantics:**

- `apply` / `undo` operate on the change-set ledger - they approve/reject an execution's changes without touching files.
- `restore` / `session rollback` are content operations - they restore the worktree to a session's pre-execution snapshot (modified files revert, files created during the session are removed).
- `diff` is the review surface: execution ID, agent, compartment, status, and the per-file change list (`ADDED` / `MODIFIED` / `DELETED`).
