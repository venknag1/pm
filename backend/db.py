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


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def _migrate(conn: sqlite3.Connection) -> None:
    """Apply schema migrations for new columns and structural changes."""
    # Add is_admin to users if missing
    if not _has_column(conn, "users", "is_admin"):
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")

    # Add title to boards and remove UNIQUE constraint on user_id.
    # SQLite can't DROP CONSTRAINT directly — recreate the table if needed.
    if not _has_column(conn, "boards", "title"):
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS boards_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT 'My Board',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            INSERT INTO boards_new (id, user_id, title, created_at)
                SELECT id, user_id, 'My Board', created_at FROM boards;
            DROP TABLE boards;
            ALTER TABLE boards_new RENAME TO boards;
        """)

    # Add due_date, priority, label, assigned_to to cards if missing
    if not _has_column(conn, "cards", "due_date"):
        conn.execute("ALTER TABLE cards ADD COLUMN due_date TEXT")
    if not _has_column(conn, "cards", "priority"):
        conn.execute("ALTER TABLE cards ADD COLUMN priority TEXT NOT NULL DEFAULT 'medium'")
    if not _has_column(conn, "cards", "label"):
        conn.execute("ALTER TABLE cards ADD COLUMN label TEXT")
    if not _has_column(conn, "cards", "assigned_to"):
        conn.execute("ALTER TABLE cards ADD COLUMN assigned_to INTEGER")

    # Add wip_limit to columns if missing
    if not _has_column(conn, "columns", "wip_limit"):
        conn.execute("ALTER TABLE columns ADD COLUMN wip_limit INTEGER")

    # Add archived flag to cards
    if not _has_column(conn, "cards", "archived"):
        conn.execute("ALTER TABLE cards ADD COLUMN archived INTEGER NOT NULL DEFAULT 0")

    # Add story_points to cards
    if not _has_column(conn, "cards", "story_points"):
        conn.execute("ALTER TABLE cards ADD COLUMN story_points INTEGER")

    # Add pinned to boards
    if not _has_column(conn, "boards", "pinned"):
        conn.execute("ALTER TABLE boards ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")

    # Add color to cards
    if not _has_column(conn, "cards", "color"):
        conn.execute("ALTER TABLE cards ADD COLUMN color TEXT")

    conn.commit()


def init_db() -> None:
    from .auth import hash_password

    conn = _connect()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT 'My Board',
                pinned INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS columns (
                id TEXT PRIMARY KEY,
                board_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                position INTEGER NOT NULL,
                wip_limit INTEGER,
                FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                board_id INTEGER NOT NULL,
                column_id TEXT NOT NULL,
                title TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                position INTEGER NOT NULL,
                due_date TEXT,
                priority TEXT NOT NULL DEFAULT 'medium',
                label TEXT,
                assigned_to INTEGER,
                archived INTEGER NOT NULL DEFAULT 0,
                story_points INTEGER,
                color TEXT,
                FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE,
                FOREIGN KEY (column_id) REFERENCES columns(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS checklist_items (
                id TEXT PRIMARY KEY,
                card_id TEXT NOT NULL,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                position INTEGER NOT NULL,
                FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS card_comments (
                id TEXT PRIMARY KEY,
                card_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (card_id) REFERENCES cards(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                board_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                card_id TEXT,
                action TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
            );
        """)

        _migrate(conn)

        # Create default admin user and default user if they don't exist
        now = datetime.now(timezone.utc).isoformat()

        if not conn.execute("SELECT 1 FROM users WHERE username = 'admin'").fetchone():
            with conn:
                conn.execute(
                    "INSERT INTO users (username, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?)",
                    ("admin", hash_password("admin123"), 1, now),
                )
                admin_id = conn.execute(
                    "SELECT id FROM users WHERE username = 'admin'"
                ).fetchone()["id"]
                conn.execute(
                    "INSERT INTO boards (user_id, title, created_at) VALUES (?, ?, ?)",
                    (admin_id, "Admin Board", now),
                )
                board_id = conn.execute(
                    "SELECT id FROM boards WHERE user_id = ? ORDER BY id DESC LIMIT 1", (admin_id,)
                ).fetchone()["id"]
                for col_id, title, position in DEFAULT_COLUMNS:
                    conn.execute(
                        "INSERT OR IGNORE INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
                        (f"admin-{col_id}", board_id, title, position),
                    )

        if not conn.execute("SELECT 1 FROM users WHERE username = 'user'").fetchone():
            with conn:
                conn.execute(
                    "INSERT INTO users (username, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?)",
                    ("user", hash_password("password"), 0, now),
                )
                user_id = conn.execute(
                    "SELECT id FROM users WHERE username = 'user'"
                ).fetchone()["id"]
                conn.execute(
                    "INSERT INTO boards (user_id, title, created_at) VALUES (?, ?, ?)",
                    (user_id, "My Board", now),
                )
                board_id = conn.execute(
                    "SELECT id FROM boards WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
                ).fetchone()["id"]
                for col_id, title, position in DEFAULT_COLUMNS:
                    conn.execute(
                        "INSERT OR IGNORE INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
                        (col_id, board_id, title, position),
                    )
    finally:
        conn.close()
