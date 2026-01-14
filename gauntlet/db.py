"""SQLite database layer for storing run results and metrics."""

from datetime import datetime
from pathlib import Path
from typing import Any

import sqlite_utils


def get_db(db_path: str | Path = "results.sqlite") -> sqlite_utils.Database:
    """Get or create the database connection."""
    return sqlite_utils.Database(db_path)


def init_db(db_path: str | Path = "results.sqlite") -> sqlite_utils.Database:
    """Initialize the database with required tables."""
    db = get_db(db_path)
    
    # Create runs table
    if "runs" not in db.table_names():
        db["runs"].create(
            {
                "run_id": str,
                "started_at": str,
                "model": str,
                "base_url": str,
                "git_commit": str,
            },
            pk="run_id",
        )
    
    # Create attempts table
    if "attempts" not in db.table_names():
        db["attempts"].create(
            {
                "id": int,
                "run_id": str,
                "task_name": str,
                "strategy_name": str,
                "attempt_num": int,
                "success": int,
                "score": float,
                "latency_ms": float,
                "error_type": str,
                "artifact_dir": str,
                "created_at": str,
            },
            pk="id",
            foreign_keys=[("run_id", "runs", "run_id")],
        )
    
    return db


def insert_run(
    db: sqlite_utils.Database,
    run_id: str,
    model: str,
    base_url: str,
    git_commit: str | None = None,
) -> None:
    """Insert a new run record."""
    db["runs"].insert(
        {
            "run_id": run_id,
            "started_at": datetime.now().isoformat(),
            "model": model,
            "base_url": base_url,
            "git_commit": git_commit or "",
        }
    )


def insert_attempt(
    db: sqlite_utils.Database,
    run_id: str,
    task_name: str,
    strategy_name: str,
    attempt_num: int,
    success: bool,
    score: float,
    latency_ms: float,
    artifact_dir: str,
    error_type: str | None = None,
) -> None:
    """Insert an attempt record."""
    db["attempts"].insert(
        {
            "run_id": run_id,
            "task_name": task_name,
            "strategy_name": strategy_name,
            "attempt_num": attempt_num,
            "success": 1 if success else 0,
            "score": score,
            "latency_ms": latency_ms,
            "error_type": error_type or "",
            "artifact_dir": artifact_dir,
            "created_at": datetime.now().isoformat(),
        }
    )


def get_attempts(
    db: sqlite_utils.Database,
    run_id: str | None = None,
) -> list[dict[str, Any]]:
    """Get all attempts, optionally filtered by run_id."""
    if run_id:
        return list(db["attempts"].rows_where("run_id = ?", [run_id]))
    return list(db["attempts"].rows)


def get_run(db: sqlite_utils.Database, run_id: str) -> dict[str, Any] | None:
    """Get a specific run by ID."""
    try:
        return db["runs"].get(run_id)
    except sqlite_utils.db.NotFoundError:
        return None
