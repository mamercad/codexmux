# codexmux — Codex CLI Multiplexer

Run parallel `codex` TUI sessions with a self-healing watchdog, shared task board, and web dashboard. Single file. No external dependencies beyond Python 3 + tmux.

```bash
git clone https://github.com/mamercad/codexmux && cd codexmux && ./install.sh
codexmux register myproject --dir ~/myproject --full-auto
codexmux start myproject
codexmux serve   # → https://localhost:8844
```

---

## Why codexmux?

| Problem | codexmux's solution |
|---------|---------------------|
| Can't run multiple codex agents at once | **tmux-backed sessions** — each agent in its own pane |
| Agent crashes or exits mid-task | **Self-healing watchdog** — auto-restarts with `resume --last` |
| Agents duplicate work | **Task board** — SQLite-backed atomic claiming |
| No visibility across sessions | **Web dashboard** — live status, peek, send |
| Agents can't coordinate | **REST API** — shared memory, messaging, task delegation |

---

## Example: Parallel Feature Development

Spin up two agents — one for the API, one for the frontend — with a shared task board so they don't step on each other.

```bash
# Register agents pointed at the same repo
codexmux register api      --dir ~/myapp --full-auto --model o3
codexmux register frontend --dir ~/myapp --full-auto --model o3

# Seed the task board
codexmux board add --title "Build POST /auth/login endpoint"   --project API
codexmux board add --title "Build POST /auth/register endpoint" --project API
codexmux board add --title "Create login page component"       --project UI
codexmux board add --title "Create signup page component"      --project UI

# Launch both agents
codexmux start api
codexmux start frontend

# Open the dashboard to watch them work
codexmux serve
```

From the dashboard (or CLI), each agent claims tasks atomically — no duplicated work. Peek into either session live, send follow-up prompts, and let the watchdog handle crashes.

```bash
# Check on progress
codexmux peek api
codexmux peek frontend

# Send a directive to the api agent
codexmux send api "use bcrypt for password hashing, not argon2"

# See what's been claimed
codexmux board list
```

---

## Features

- **Parallel agents** — register and run many `codex` sessions, each in tmux
- **Watchdog** — detects exited/stuck agents, auto-restarts, auto-accepts confirmations
- **Task board** — SQLite-backed kanban with atomic task claiming (CAS)
- **Web dashboard** — session cards, live peek, send bar, task board, alerts
- **REST API** — full CRUD for sessions, tasks, memory, messages
- **Worktree isolation** — `--worktree` flag for per-agent branch isolation
- **Prefix matching** — `codexmux attach my` resolves to `myproject`
- **Zero external deps** — Python 3 stdlib only (sqlite3, http.server, ssl, threading)
- **Single file** — one executable, edit it, extend it

## Requirements

- Python 3.8+
- tmux
- [Codex CLI](https://github.com/openai/codex) (`codex`)

## Install

```bash
git clone https://github.com/mamercad/codexmux && cd codexmux && ./install.sh
```

Or directly:

```bash
curl -fsSL https://raw.githubusercontent.com/mamercad/codexmux/main/codexmux -o /usr/local/bin/codexmux
chmod +x /usr/local/bin/codexmux
```

## Quick Start

```bash
# Register agents pointing at a git repo
codexmux register api --dir ~/myproject --full-auto --model o4-mini
codexmux register frontend --dir ~/myproject --full-auto --worktree

# Launch them
codexmux start api
codexmux start frontend

# Attach to a session's TUI
codexmux attach api

# Or monitor everything from the browser
codexmux serve   # → https://localhost:8844
```

## CLI

```bash
codexmux register <name> --dir <path> [--full-auto] [--model o4-mini] [--worktree]
codexmux start <name>
codexmux stop <name>
codexmux attach <name>          # attach to tmux session (detach: Ctrl-b d)
codexmux peek <name>            # view output without attaching
codexmux send <name> <text>     # send text to a session
codexmux exec <name> --dir <path> [--full-auto] -- <prompt>
codexmux ls [--format json]     # list sessions
codexmux board list             # show task board
codexmux board add --title "..." [--project PRJ]
codexmux board claim TASK-ID --agent <name>
codexmux board done TASK-ID
codexmux serve [--port 8844]    # web dashboard + watchdog
```

Session names support prefix matching — `codexmux peek my` resolves to `myproject` if unambiguous.

## Watchdog

When `codexmux serve` is running, the watchdog checks all sessions every 15 seconds:

| Condition | Action |
|-----------|--------|
| Agent exited to shell prompt (full-auto mode) | Auto-restarts with `resume --last` |
| Agent waiting for confirmation (full-auto mode) | Auto-accepts after 30s |
| Agent idle for 10+ minutes | Pushes a `stuck` alert |

## REST API

All endpoints available at `https://localhost:8844/api/`.

### Sessions

```bash
# List sessions
curl -sk https://localhost:8844/api/sessions

# Peek at output
curl -sk https://localhost:8844/api/sessions/myproject/peek?lines=50

# Send text to a session
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"text":"implement the auth endpoint"}' \
  https://localhost:8844/api/sessions/myproject/send

# Start / stop
curl -sk -X POST https://localhost:8844/api/sessions/myproject/start
curl -sk -X POST https://localhost:8844/api/sessions/myproject/stop
```

### Task Board

```bash
# Create a task
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"title":"Add login endpoint","project":"API"}' \
  https://localhost:8844/api/tasks

# Claim a task (atomic — only one agent wins)
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"agent":"api"}' \
  https://localhost:8844/api/tasks/API-A1B2C3/claim

# Complete a task
curl -sk -X POST https://localhost:8844/api/tasks/API-A1B2C3/done
```

### Shared Memory & Messaging

```bash
# Write shared context
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"key":"db_schema","value":"users(id,email,hash)"}' \
  https://localhost:8844/api/memory

# Read shared context
curl -sk https://localhost:8844/api/memory?key=db_schema

# Send a message between agents
curl -sk -X POST -H 'Content-Type: application/json' \
  -d '{"sender":"api","recipient":"frontend","body":"auth schema changed"}' \
  https://localhost:8844/api/messages

# Read messages for an agent
curl -sk https://localhost:8844/api/messages?recipient=frontend
```

## Data

All state lives in `~/.codexmux/`:

```
~/.codexmux/
├── codexmux.db   # SQLite WAL (sessions, tasks, messages, memory, alerts)
├── tls/          # Auto-generated TLS certs
└── logs/         # Session logs
```

## Acknowledgments

Heavily inspired by [amux](https://github.com/mixpeek/amux) — the original Claude Code multiplexer. codexmux adapts the same patterns (tmux wrapping, self-healing watchdog, SQLite task board, single-file architecture) for the `codex` CLI. Props to the [Mixpeek](https://github.com/mixpeek) team for proving the pattern. 🙏

Sibling project: [curmux](https://github.com/mamercad/curmux) — the same concept for the `cursor-agent` TUI.

## License

MIT

---

<p align="center">
  Made with ❤️ and ☕ in the Great Lakes State of Michigan 🏔️🌊
</p>
