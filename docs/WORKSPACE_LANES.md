# Boundary Virtual Agent Lanes & Integration Architecture

Boundary introduces **Virtual Agent Lanes**-the developer workspace abstraction for AI agents.

```text
BOUNDARY WORKSPACE
   │
   ├── Agent Sessions & Virtual Lanes
   │   ├── Lane: auth-fix  (Claude Code)  -> Changes: [src/auth.py]
   │   ├── Lane: logging   (OpenCode)     -> Changes: [src/logger.py]
   │   └── Lane: tests     (Codex)        -> Changes: [tests/test_auth.py]
   │
   ├── Integration Engine
   │   ├── boundary integrate create auth-fix logging
   │   ├── boundary integrate preview
   │   └── boundary integrate apply
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
boundary wrap --agent "Claude Code" --task "Fix authentication bug" --lane auth-fix -- claude

# Agent 2 (OpenCode) in 'logging' lane concurrently
boundary wrap --agent "OpenCode" --task "Add structured logging" --lane logging -- opencode
```

### 2. Inspecting Workspace Lanes
```bash
boundary lanes
boundary lane inspect auth-fix
```

### 3. Combining & Integrating Lanes
```bash
# Create integration candidate combining auth-fix and logging
boundary integrate create auth-fix logging

# Preview candidate diffs and conflict status
boundary integrate preview

# Apply cleanly to workspace
boundary integrate apply
```

---

## Reviewing, Applying & Recovering Agent Changes

Every governed execution records a **change set** (BLAKE3 file diffs attributed to its Execution ID). The Git-like commands manage those change sets:

```bash
# Review what agents changed (filter by execution, or --unapplied for pending work)
boundary diff
boundary diff --execution exec_1723635840000
boundary diff --unapplied

# Promote a change set into the workspace baseline.
# Overlapping changes from other un-applied executions surface as conflicts;
# --force applies anyway.
boundary apply
boundary apply --execution exec_1723635840000

# Reverse the last apply operation (or a specific one)
boundary undo
boundary undo --execution exec_1723635840000

# Restore the workspace from a session's pre-execution snapshot checkpoint
boundary restore sess_1723635840000

# Roll back a session (restores its snapshot and marks it ROLLED_BACK)
boundary session rollback sess_1723635840000
```

**Semantics:**

- `apply` / `undo` operate on the change-set ledger - they approve/reject an execution's changes without touching files.
- `restore` / `session rollback` are content operations - they restore the worktree to a session's pre-execution snapshot (modified files revert, files created during the session are removed).
- `diff` is the review surface: execution ID, agent, compartment, status, and the per-file change list (`ADDED` / `MODIFIED` / `DELETED`).
