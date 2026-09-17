# Bergendy Workspace Initialization & Agent Execution

## 1. What It Is

When you run `bergendy init`, Bergendy turns your project directory into a **managed agent workspace**. You launch your favorite agent directly inside an isolated kernel sandbox.

---

## 2. How It Works

```text
bergendy init
└── creates .boundary/
    ├── config.yaml    <- workspace compartment policy
    ├── state/         <- runtime state
    ├── snapshots/     <- BLAKE3 worktree diff snapshots
    └── executions/    <- execution records

Direct Execution:
  $ bergendy claude      -> Launches Claude Code in kernel sandbox
  $ bergendy opencode    -> Launches OpenCode in kernel sandbox
  $ bergendy codex       -> Launches Codex in kernel sandbox
  $ bergendy cursor      -> Launches Cursor in kernel sandbox
  $ bergendy aider       -> Launches Aider in kernel sandbox
```

---

## 3. Running Interactive Coding Agents

```bash
bergendy claude
bergendy opencode
bergendy codex
bergendy cursor
bergendy aider
```

Each interactive agent runs with:
- Full native TUI support (colors, alternate screen, Ctrl+C, Ctrl+D, window resize).
- Hard OS-level kernel isolation (Seatbelt on macOS / Landlock on Linux).
- Deny-by-default credential protection (`~/.ssh`, `~/.aws`, `~/.config/gcloud` blocked).
- Automatic BLAKE3 pre-execution snapshots for physical instant rollback (`bergendy undo`).

---

## 4. Checking Workspace Health

```bash
bergendy status
```

```text
================================================================================
                               BERGENDY STATUS
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
bergendy --run invoice-pipeline
```

Or run standalone Python agent scripts:

```bash
bergendy exec --compartment research -- python3 scraper.py
```
