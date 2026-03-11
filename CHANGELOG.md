# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-03-10

### Added

- `update` command (alias: `set`) for partial session updates — change `--dir`, `--full-auto`, `--no-full-auto`, `--model`, `--sandbox` without re-registering
- `rm` command (aliases: `remove`, `del`) to delete sessions — stops tmux if running, cleans up messages, alerts, and task assignments
- Auto-trust directories in `~/.codex/config.toml` on `register` to prevent the codex trust prompt from blocking sessions
- `tmux_new_session` now passes `-c <cwd>` so sessions start in the correct directory
- `cmd_attach` pre-checks tmux session existence with a helpful error message

### Fixed

- Watchdog restart now passes `cwd` to `tmux_new_session` for consistency
- Sessions no longer silently die due to codex trust prompt in untrusted directories

## [0.1.0] - 2026-03-10

### Added

- Single-file `codexmux` executable — CLI, REST API, web dashboard, and watchdog
- Session management: `register`, `start`, `stop`, `attach`, `peek`, `send`, `exec`, `ls`
- Self-healing watchdog: auto-restart exited agents with `resume --last`, auto-accept in full-auto mode, stuck detection
- SQLite-backed task board with atomic claiming (CAS): `board add`, `board claim`, `board done`
- Web dashboard with session cards, live peek modal, kanban board, and alerts feed
- REST API for sessions, tasks, shared memory, and inter-agent messaging
- `--full-auto`, `--model`, `--worktree` flags for session configuration
- Prefix matching for session names
- Auto-generated TLS (mkcert or self-signed fallback)
- One-line install via `install.sh` or direct `curl`
- GitHub Actions CI: ruff lint/format, shellcheck, pre-commit, pytest (Python 3.9 + 3.12)
- Pre-commit hooks: yaml/json check, trailing whitespace, ruff, gitleaks, commitlint, shellcheck
- EditorConfig and ruff.toml for consistent formatting
- Tests covering database, sessions, task board, memory, messages, status detection, tmux, and alerts
- Commitlint config enforcing conventional commits
- MIT license

### Fixed

- Use `codex` binary with `--no-alt-screen` for tmux compatibility
- Pass tmux commands as single shell string via `shlex.quote`

[Unreleased]: https://github.com/mamercad/codexmux/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/mamercad/codexmux/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/mamercad/codexmux/releases/tag/v0.1.0
