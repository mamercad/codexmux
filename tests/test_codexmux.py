"""Tests for codexmux — Codex CLI Multiplexer."""

import ast
import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture()
def codexmux():
    """Import codexmux as a module from the single-file executable."""
    codexmux_path = Path(__file__).parent.parent / "codexmux"
    loader = importlib.machinery.SourceFileLoader("codexmux", str(codexmux_path))
    spec = importlib.util.spec_from_loader("codexmux", loader, origin=str(codexmux_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def tmp_data_dir(tmp_path, codexmux, monkeypatch):
    """Redirect codexmux data to a temp directory."""
    monkeypatch.setattr(codexmux, "DATA_DIR", tmp_path)
    monkeypatch.setattr(codexmux, "DB_PATH", tmp_path / "codexmux.db")
    if hasattr(codexmux._local, "conn"):
        del codexmux._local.conn
    codexmux._db()
    return tmp_path


# ── Syntax ───────────────────────────────────────────────────────────────


class TestSyntax:
    def test_valid_python(self):
        src = (Path(__file__).parent.parent / "codexmux").read_text()
        ast.parse(src)

    def test_executable_help(self):
        r = subprocess.run(
            [str(Path(__file__).parent.parent / "codexmux"), "--help"],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
        assert "Codex CLI Multiplexer" in r.stdout

    def test_version(self):
        r = subprocess.run(
            [str(Path(__file__).parent.parent / "codexmux"), "--version"],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
        assert "codexmux" in r.stdout


# ── Database ─────────────────────────────────────────────────────────────


class TestDatabase:
    def test_init_creates_tables(self, codexmux, tmp_data_dir):
        conn = codexmux._db()
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert {"sessions", "tasks", "messages", "memory", "alerts"}.issubset(tables)

    def test_wal_mode(self, codexmux, tmp_data_dir):
        conn = codexmux._db()
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"


# ── Session management ───────────────────────────────────────────────────


class TestSessions:
    def test_register_and_list(self, codexmux, tmp_data_dir, tmp_path):
        conn = codexmux._db()
        project_dir = str(tmp_path / "project")
        os.makedirs(project_dir)
        now = codexmux._now()
        conn.execute(
            "INSERT INTO sessions (name, directory, full_auto, model, sandbox, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("test-session", project_dir, 1, "o3", "workspace-write", "stopped", now, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM sessions WHERE name=?", ("test-session",)).fetchone()
        assert row is not None
        assert row["directory"] == project_dir
        assert row["full_auto"] == 1
        assert row["model"] == "o3"

    def test_resolve_name_exact(self, codexmux, tmp_data_dir, tmp_path):
        conn = codexmux._db()
        project_dir = str(tmp_path / "project")
        os.makedirs(project_dir)
        now = codexmux._now()
        conn.execute(
            "INSERT INTO sessions (name, directory, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("myproject", project_dir, "stopped", now, now),
        )
        conn.commit()
        assert codexmux.resolve_name("myproject") == "myproject"

    def test_resolve_name_prefix(self, codexmux, tmp_data_dir, tmp_path):
        conn = codexmux._db()
        project_dir = str(tmp_path / "project")
        os.makedirs(project_dir)
        now = codexmux._now()
        conn.execute(
            "INSERT INTO sessions (name, directory, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("myproject", project_dir, "stopped", now, now),
        )
        conn.commit()
        assert codexmux.resolve_name("myp") == "myproject"

    def test_resolve_name_ambiguous(self, codexmux, tmp_data_dir, tmp_path):
        conn = codexmux._db()
        project_dir = str(tmp_path / "project")
        os.makedirs(project_dir)
        now = codexmux._now()
        conn.execute(
            "INSERT INTO sessions (name, directory, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("myproject", project_dir, "stopped", now, now),
        )
        conn.execute(
            "INSERT INTO sessions (name, directory, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("myother", project_dir, "stopped", now, now),
        )
        conn.commit()
        with pytest.raises(SystemExit):
            codexmux.resolve_name("my")

    def test_resolve_name_not_found(self, codexmux, tmp_data_dir):
        with pytest.raises(SystemExit):
            codexmux.resolve_name("nonexistent")


# ── Task board ───────────────────────────────────────────────────────────


class TestTaskBoard:
    def test_create_task(self, codexmux, tmp_data_dir):
        conn = codexmux._db()
        task_id = f"TEST-{codexmux._short_id()}"
        now = codexmux._now()
        conn.execute(
            "INSERT INTO tasks (id, title, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (task_id, "Build feature", "todo", now, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert row["title"] == "Build feature"
        assert row["status"] == "todo"

    def test_claim_task_atomic(self, codexmux, tmp_data_dir):
        conn = codexmux._db()
        task_id = f"TEST-{codexmux._short_id()}"
        now = codexmux._now()
        conn.execute(
            "INSERT INTO tasks (id, title, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (task_id, "Claimable", "todo", now, now),
        )
        conn.commit()

        row = conn.execute(
            "UPDATE tasks SET status='claimed', assignee=?, updated_at=? WHERE id=? AND status='todo' RETURNING *",
            ("agent-1", now, task_id),
        ).fetchone()
        conn.commit()
        assert row is not None
        assert row["assignee"] == "agent-1"

        row2 = conn.execute(
            "UPDATE tasks SET status='claimed', assignee=?, updated_at=? WHERE id=? AND status='todo' RETURNING *",
            ("agent-2", now, task_id),
        ).fetchone()
        assert row2 is None

    def test_complete_task(self, codexmux, tmp_data_dir):
        conn = codexmux._db()
        task_id = f"TEST-{codexmux._short_id()}"
        now = codexmux._now()
        conn.execute(
            "INSERT INTO tasks (id, title, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (task_id, "Done task", "claimed", now, now),
        )
        conn.commit()
        conn.execute("UPDATE tasks SET status='done', updated_at=? WHERE id=?", (now, task_id))
        conn.commit()
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        assert row["status"] == "done"


# ── Memory ───────────────────────────────────────────────────────────────


class TestMemory:
    def test_write_and_read(self, codexmux, tmp_data_dir):
        conn = codexmux._db()
        now = codexmux._now()
        conn.execute(
            "INSERT OR REPLACE INTO memory (key, value, updated_at) VALUES (?, ?, ?)",
            ("schema", "users(id,email)", now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM memory WHERE key=?", ("schema",)).fetchone()
        assert row["value"] == "users(id,email)"

    def test_upsert(self, codexmux, tmp_data_dir):
        conn = codexmux._db()
        now = codexmux._now()
        conn.execute("INSERT OR REPLACE INTO memory (key, value, updated_at) VALUES (?, ?, ?)", ("k", "v1", now))
        conn.commit()
        conn.execute("INSERT OR REPLACE INTO memory (key, value, updated_at) VALUES (?, ?, ?)", ("k", "v2", now))
        conn.commit()
        row = conn.execute("SELECT * FROM memory WHERE key=?", ("k",)).fetchone()
        assert row["value"] == "v2"


# ── Messages ─────────────────────────────────────────────────────────────


class TestMessages:
    def test_send_and_receive(self, codexmux, tmp_data_dir):
        conn = codexmux._db()
        now = codexmux._now()
        conn.execute(
            "INSERT INTO messages (session, role, content, created_at) VALUES (?, ?, ?, ?)",
            ("api", "user", "schema changed", now),
        )
        conn.commit()
        rows = conn.execute("SELECT * FROM messages WHERE session=?", ("api",)).fetchall()
        assert len(rows) == 1
        assert rows[0]["content"] == "schema changed"
        assert rows[0]["role"] == "user"


# ── Status detection ─────────────────────────────────────────────────────


class TestStatusDetection:
    def test_empty_output(self, codexmux):
        assert codexmux._detect_status("") == "unknown"
        assert codexmux._detect_status(None) == "unknown"

    def test_shell_prompt_detected(self, codexmux):
        assert codexmux._at_shell_prompt("mark@raven:~/project$ ") is True

    def test_no_shell_prompt(self, codexmux):
        assert codexmux._at_shell_prompt("Working on something...") is False

    def test_exited_status(self, codexmux):
        output = "some agent output\nmark@raven:~/project$ "
        assert codexmux._detect_status(output) == "exited"

    def test_working_status(self, codexmux):
        output = "Processing request\nthinking about the problem\nGenerating code"
        assert codexmux._detect_status(output) == "working"

    def test_error_status(self, codexmux):
        output = "Running tests\nTraceback (most recent call last):\n  File error:"
        assert codexmux._detect_status(output) == "error"


# ── Tmux helpers ─────────────────────────────────────────────────────────


class TestTmux:
    def test_session_name_prefix(self, codexmux):
        assert codexmux.tmux_session_name("myproject") == "codexmux-myproject"

    @pytest.mark.skipif(not shutil.which("tmux"), reason="tmux not installed")
    def test_has_session_false(self, codexmux):
        assert codexmux.tmux_has_session("nonexistent-session-12345") is False

    @pytest.mark.skipif(not shutil.which("tmux"), reason="tmux not installed")
    def test_new_and_kill_session(self, codexmux, tmp_path):
        name = f"test-{os.getpid()}"
        codexmux.tmux_new_session(name, ["sleep", "300"])
        try:
            assert codexmux.tmux_has_session(name) is True
            output = codexmux.tmux_capture(name, 10)
            assert isinstance(output, str)
        finally:
            codexmux.tmux_kill_session(name)
        assert codexmux.tmux_has_session(name) is False


# ── Alerts ───────────────────────────────────────────────────────────────


class TestAlerts:
    def test_push_alert(self, codexmux, tmp_data_dir):
        codexmux._push_alert("test_alert", "Something happened", "test-session")
        conn = codexmux._db()
        rows = conn.execute("SELECT * FROM alerts").fetchall()
        assert len(rows) == 1
        assert rows[0]["type"] == "test_alert"
        assert rows[0]["session"] == "test-session"

    def test_short_id_uniqueness(self, codexmux):
        ids = {codexmux._short_id() for _ in range(100)}
        assert len(ids) == 100
