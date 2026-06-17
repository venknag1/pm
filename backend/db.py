import os
import sqlite3
from datetime import datetime, timezone

DEFAULT_COLUMNS = [
    ("col-backlog", "Backlog", 0),
    ("col-discovery", "Discovery", 1),
    ("col-progress", "In Progress", 2),
    ("col-review", "Review", 3),
    ("col-done", "Done", 4),
]


def _db_path() -> str:
    return os.getenv("DB_PATH", "pm.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    from .auth import hash_password

    conn = _connect()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS columns (
                id TEXT PRIMARY KEY,
                board_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                position INTEGER NOT NULL,
                FOREIGN KEY (board_id) REFERENCES boards(id)
            );
            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                board_id INTEGER NOT NULL,
                column_id TEXT NOT NULL,
                title TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                position INTEGER NOT NULL,
                FOREIGN KEY (board_id) REFERENCES boards(id),
                FOREIGN KEY (column_id) REFERENCES columns(id)
            );
        """)

        if conn.execute("SELECT 1 FROM users WHERE username = 'user'").fetchone():
            return

        now = datetime.now(timezone.utc).isoformat()
        with conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                ("user", hash_password("password"), now),
            )
            user_id = conn.execute(
                "SELECT id FROM users WHERE username = 'user'"
            ).fetchone()["id"]
            conn.execute(
                "INSERT INTO boards (user_id, created_at) VALUES (?, ?)",
                (user_id, now),
            )
            board_id = conn.execute(
                "SELECT id FROM boards WHERE user_id = ?", (user_id,)
            ).fetchone()["id"]
            for col_id, title, position in DEFAULT_COLUMNS:
                conn.execute(
                    "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
                    (col_id, board_id, title, position),
                )
    finally:
        conn.close()
