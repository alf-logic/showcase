"""SQLite database layer for pipeline state tracking."""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

DB_PATH: Path = Path(__file__).parent / "pipeline.db"

FUNCTION_STATUSES: list[str] = [
    "pending",
    "l1_in_progress",
    "l1_done",
    "l2_in_progress",
    "l2_done",
    "l2_rejected",
    "l3_in_progress",
    "l3_done",
    "l3_failed",
    "covered",
    "bug_suspect",
    "needs_refactor",
    "test_failed",
]

SCHEMA: str = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id TEXT PRIMARY KEY,
    repo_url TEXT NOT NULL,
    clone_path TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    budget_limit_usd REAL NOT NULL DEFAULT 2.0,
    budget_used_usd REAL NOT NULL DEFAULT 0.0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS functions (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES pipeline_runs(id),
    name TEXT NOT NULL,
    file TEXT NOT NULL,
    line INTEGER NOT NULL,
    args TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'pending',
    status_reason TEXT,
    spec_text TEXT,
    test_code TEXT,
    test_output TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_logs (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES pipeline_runs(id),
    function_id TEXT NOT NULL REFERENCES functions(id),
    layer TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    model TEXT,
    tokens_used INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0.0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS git_operations (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES pipeline_runs(id),
    function_id TEXT REFERENCES functions(id),
    operation TEXT NOT NULL,
    branch_name TEXT,
    commit_sha TEXT,
    commit_message TEXT,
    diff TEXT,
    parent_sha TEXT,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_functions_run_id ON functions(run_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_function_id ON agent_logs(function_id);
CREATE INDEX IF NOT EXISTS idx_git_operations_run_id ON git_operations(run_id);
"""


def gen_id() -> str:
    return uuid.uuid4().hex[:12]


def now() -> float:
    return time.time()


class DB:
    """Synchronous SQLite wrapper for pipeline state."""

    def __init__(self, db_path: Path | str = DB_PATH) -> None:
        self.db_path: Path = Path(db_path)
        self.conn: sqlite3.Connection = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # -- Pipeline runs --

    def create_run(self, repo_url: str, clone_path: str, budget_limit: float = 2.0) -> str:
        run_id: str = gen_id()
        self.conn.execute(
            "INSERT INTO pipeline_runs (id, repo_url, clone_path, status, budget_limit_usd, created_at) VALUES (?, ?, ?, 'pending', ?, ?)",
            (run_id, repo_url, clone_path, budget_limit, now()),
        )
        self.conn.commit()
        return run_id

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM pipeline_runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else None

    def update_run_status(self, run_id: str, status: str) -> None:
        self.conn.execute("UPDATE pipeline_runs SET status = ? WHERE id = ?", (status, run_id))
        self.conn.commit()

    def update_run_budget(self, run_id: str, cost: float) -> None:
        self.conn.execute(
            "UPDATE pipeline_runs SET budget_used_usd = budget_used_usd + ? WHERE id = ?",
            (cost, run_id),
        )
        self.conn.commit()

    def get_remaining_budget(self, run_id: str) -> float:
        row = self.conn.execute(
            "SELECT budget_limit_usd - budget_used_usd AS remaining FROM pipeline_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        return float(row["remaining"]) if row else 0.0

    # -- Functions --

    def create_function(self, run_id: str, name: str, file: str, line: int, args: str = "[]") -> str:
        fn_id: str = gen_id()
        ts: float = now()
        self.conn.execute(
            "INSERT INTO functions (id, run_id, name, file, line, args, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)",
            (fn_id, run_id, name, file, line, args, ts, ts),
        )
        self.conn.commit()
        return fn_id

    def get_function(self, fn_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM functions WHERE id = ?", (fn_id,)).fetchone()
        return dict(row) if row else None

    def get_functions_for_run(self, run_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM functions WHERE run_id = ? ORDER BY file, line", (run_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def update_function_status(self, fn_id: str, status: str, reason: str | None = None) -> None:
        self.conn.execute(
            "UPDATE functions SET status = ?, status_reason = ?, updated_at = ? WHERE id = ?",
            (status, reason, now(), fn_id),
        )
        self.conn.commit()

    def update_function_spec(self, fn_id: str, spec_text: str) -> None:
        self.conn.execute(
            "UPDATE functions SET spec_text = ?, updated_at = ? WHERE id = ?",
            (spec_text, now(), fn_id),
        )
        self.conn.commit()

    def update_function_tests(self, fn_id: str, test_code: str, test_output: str) -> None:
        self.conn.execute(
            "UPDATE functions SET test_code = ?, test_output = ?, updated_at = ? WHERE id = ?",
            (test_code, test_output, now(), fn_id),
        )
        self.conn.commit()

    # -- Agent logs --

    def add_agent_log(
        self,
        run_id: str,
        function_id: str,
        layer: str,
        role: str,
        content: str,
        model: str | None = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
    ) -> str:
        log_id: str = gen_id()
        self.conn.execute(
            "INSERT INTO agent_logs (id, run_id, function_id, layer, role, content, model, tokens_used, cost_usd, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (log_id, run_id, function_id, layer, role, content, model, tokens_used, cost_usd, now()),
        )
        self.conn.commit()
        return log_id

    def get_agent_logs(self, function_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM agent_logs WHERE function_id = ? ORDER BY created_at", (function_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_agent_logs(self, run_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM agent_logs WHERE run_id = ? ORDER BY created_at", (run_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # -- Git operations --

    def add_git_operation(
        self,
        run_id: str,
        function_id: str | None,
        operation: str,
        branch_name: str | None = None,
        commit_sha: str | None = None,
        commit_message: str | None = None,
        diff: str | None = None,
        parent_sha: str | None = None,
    ) -> str:
        op_id: str = gen_id()
        self.conn.execute(
            "INSERT INTO git_operations (id, run_id, function_id, operation, branch_name, commit_sha, commit_message, diff, parent_sha, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (op_id, run_id, function_id, operation, branch_name, commit_sha, commit_message, diff, parent_sha, now()),
        )
        self.conn.commit()
        return op_id

    def get_git_operations(self, run_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM git_operations WHERE run_id = ? ORDER BY created_at", (run_id,)
        ).fetchall()
        return [dict(r) for r in rows]
