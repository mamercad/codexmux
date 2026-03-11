# codexmux

Single-file Codex CLI multiplexer. Everything lives in the `codexmux` executable (Python 3 + stdlib).

## Structure

- `codexmux` — CLI, server, watchdog, and inline web dashboard (single file)
- `install.sh` — copies `codexmux` to `/usr/local/bin`

## Data

All runtime state in `~/.codexmux/codexmux.db` (SQLite WAL mode). Tables: `sessions`, `tasks`, `messages`, `memory`, `alerts`.

## Workflow

- **Lifecycle**: `register` → `update` (partial changes) → `start` → `stop` → `rm` (delete)
- **Test changes**: `./codexmux --help`, `./codexmux ls`, `./codexmux serve --no-tls --port 9999`
- **Validate syntax**: `python3 -c "import ast; ast.parse(open('codexmux').read())"`
- **Commit after every completed task.** Don't batch unrelated changes.

## Architecture

The CLI and web server share the same SQLite database. The watchdog runs as a background thread when `codexmux serve` is active, polling tmux sessions every 15 seconds.

Key patterns:
- Sessions run `codex` with `--no-alt-screen` inside tmux
- `tmux_capture()` reads pane output for status detection
- `_detect_status()` pattern-matches against known codex CLI states
- `tmux_new_session()` passes the command as a single shell string via `shlex.quote` and sets `-c <cwd>`
- `register` auto-trusts directories in `~/.codex/config.toml` to prevent the codex trust prompt
- Watchdog auto-restarts exited agents with `resume --last` and auto-accepts confirmations in full-auto mode
- REST API serves both the web dashboard and agent-to-agent coordination
- All HTML/CSS/JS is inlined in the `DASHBOARD_HTML` constant

## Agent coordination

Codex agents coordinate via the REST API (available when `codexmux serve` is running):
- Claim tasks atomically: `POST /api/tasks/{id}/claim`
- Share context: `POST /api/memory` with `{key, value}`
- Send messages: `POST /api/messages` with `{sender, recipient, body}`
- Check peer status: `GET /api/sessions/{name}/status`
