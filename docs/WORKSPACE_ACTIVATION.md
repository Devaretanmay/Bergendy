# Boundary Workspace Initialization & Agent Execution

## 1. What It Is

When you run `boundary init`, Boundary turns your project directory into a **managed agent workspace**. You launch your favorite agent directly inside an isolated kernel sandbox.

---

## 2. How It Works

```text
boundary init
└── creates .boundary/
    ├── config.yaml    <- workspace compartment policy
    ├── state/         <- runtime state
    ├── snapshots/     <- BLAKE3 worktree diff snapshots
    └── executions/    <- execution records

Direct Execution:
  $ boundary claude      -> Launches Claude Code in kernel sandbox
  $ boundary opencode    -> Launches OpenCode in kernel sandbox
  $ boundary codex       -> Launches Codex in kernel sandbox
  $ boundary cursor      -> Launches Cursor in kernel sandbox
  $ boundary aider       -> Launches Aider in kernel sandbox
```

---

## 3. Running Interactive Coding Agents

```bash
boundary claude
boundary opencode
boundary codex
boundary cursor
boundary aider
```

Each interactive agent runs with:
- Full native TUI support (colors, alternate screen, Ctrl+C, Ctrl+D, window resize).
- Hard OS-level kernel isolation (Seatbelt on macOS / Landlock on Linux).
- Deny-by-default credential protection (`~/.ssh`, `~/.aws`, `~/.config/gcloud` blocked).
- Automatic BLAKE3 pre-execution snapshots for physical instant rollback (`boundary undo`).

---

## 4. Checking Workspace Health

```bash
boundary status
```

```text
================================================================================
                              BOUNDARY STATUS
================================================================================

GitHub:             CONNECTED (Devaretanmay)
AI:                 CONNECTED (groq)
Active repo:        acme/checkout-service
Repositories:       3
Repository Key:     kyp_da1358315f6c9d1ad8791cbf8cb9
Howl:               AVAILABLE
Hunt:               AVAILABLE
Status:             READY

================================================================================
```

---

## 5. Running Multi-Agent Workflows

Run a declared workflow DAG:

```bash
boundary --run invoice-pipeline
```

Or run standalone Python agent scripts:

```bash
boundary exec --compartment research -- python3 scraper.py
```
