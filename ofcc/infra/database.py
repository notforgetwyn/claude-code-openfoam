import sqlite3
from pathlib import Path
from typing import Any
from ofcc.infra.logger import get_logger

logger = get_logger(__name__)


class Database:
    _instance = None

    def __init__(self):
        self.db_path = Path.home() / ".ofcc" / "database.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @classmethod
    def get_instance(cls) -> "Database":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS cases (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    solver TEXT,
                    status TEXT DEFAULT 'idle',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                );
            """)
            logger.info(f"Database initialized at {self.db_path}")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._connect() as conn:
            return conn.execute(query, params)

    def commit(self, query: str, params: tuple = ()) -> None:
        with self._connect() as conn:
            conn.execute(query, params)
            conn.commit()

    def fetchone(self, query: str, params: tuple = ()) -> tuple | None:
        with self._connect() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchone()

    def fetchall(self, query: str, params: tuple = ()) -> list:
        with self._connect() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()
