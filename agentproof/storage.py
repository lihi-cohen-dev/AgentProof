"""Where results are saved.

The benchmark depends only on ResultStore. Switching from JSON files to a
database means choosing another implementation; nothing else changes.
"""
from __future__ import annotations

import json
import os
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Sequence

from .domain import RunResult


class ResultStore(ABC):
    @abstractmethod
    def save(self, results: Sequence[RunResult]) -> str:
        """Save the results and return where they were saved."""


class JsonResultStore(ResultStore):
    """One JSON file per benchmark run: agent_results_<date>_<time>.json."""

    def __init__(self, folder: str = "."):
        self.folder = folder

    def save(self, results: Sequence[RunResult]) -> str:
        os.makedirs(self.folder, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.folder, f"agent_results_{stamp}.json")
        counter = 1
        while os.path.exists(path):  # two runs in the same second
            counter += 1
            path = os.path.join(self.folder, f"agent_results_{stamp}_{counter}.json")
        with open(path, "w", encoding="utf-8") as file:
            json.dump([r.to_dict() for r in results], file, indent=2)
        return path


class SqliteResultStore(ResultStore):
    """All runs in one SQLite database, one row per run."""

    SCHEMA = """
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            saved_at TEXT NOT NULL,
            task TEXT NOT NULL,
            variant TEXT NOT NULL,
            run INTEGER NOT NULL,
            claimed_done INTEGER NOT NULL,
            hidden_passed INTEGER NOT NULL,
            hidden_total INTEGER NOT NULL,
            false_success INTEGER NOT NULL,
            steps INTEGER NOT NULL,
            tokens INTEGER NOT NULL,
            seconds REAL NOT NULL,
            details TEXT NOT NULL
        )
    """

    def __init__(self, path: str = "agentproof.db"):
        self.path = path
        with sqlite3.connect(self.path) as connection:
            connection.execute(self.SCHEMA)

    def save(self, results: Sequence[RunResult]) -> str:
        saved_at = datetime.now().isoformat(timespec="seconds")
        rows = []
        for result in results:
            data = result.to_dict()
            rows.append((
                saved_at, data["task"], data["variant"], data["run"], int(data["claimed_done"]),
                data["hidden_passed"], data["hidden_total"], int(data["false_success"]),
                data["steps"], data["tokens"], data["seconds"], json.dumps(data),
            ))
        with sqlite3.connect(self.path) as connection:
            connection.executemany(
                "INSERT INTO runs (saved_at, task, variant, run, claimed_done, hidden_passed, hidden_total,"
                " false_success, steps, tokens, seconds, details) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
        return self.path

    def load_all(self) -> list[dict]:
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute("SELECT details FROM runs ORDER BY id").fetchall()
        return [json.loads(row[0]) for row in rows]


STORES = {"json": JsonResultStore, "sqlite": SqliteResultStore}
