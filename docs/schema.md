# Database Schema

SQLite database, created on startup if it does not exist. File path: `pm.db` in the working directory.

## Tables

### users

| column | type | constraints |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `username` | TEXT | UNIQUE NOT NULL |
| `password_hash` | TEXT | NOT NULL |
| `created_at` | TEXT | NOT NULL (ISO-8601) |

On startup the backend checks for a `user` row and inserts one (with bcrypt-hashed `password`) if absent.

### boards

| column | type | constraints |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `user_id` | INTEGER | NOT NULL, UNIQUE, FK → users.id |
| `created_at` | TEXT | NOT NULL (ISO-8601) |

UNIQUE on `user_id` enforces one board per user at the DB level. On startup, a board is created for the seeded user if one does not exist, pre-populated with the five default columns.

### columns

| column | type | constraints |
|---|---|---|
| `id` | TEXT | PRIMARY KEY (e.g. `col-backlog`) |
| `board_id` | INTEGER | NOT NULL, FK → boards.id |
| `title` | TEXT | NOT NULL |
| `position` | INTEGER | NOT NULL |

`position` is 0-based and determines display order. On rename or reorder, affected positions are updated in a single transaction.

### cards

| column | type | constraints |
|---|---|---|
| `id` | TEXT | PRIMARY KEY (e.g. `card-abc123`) |
| `board_id` | INTEGER | NOT NULL, FK → boards.id |
| `column_id` | TEXT | NOT NULL, FK → columns.id |
| `title` | TEXT | NOT NULL |
| `details` | TEXT | NOT NULL DEFAULT `''` |
| `position` | INTEGER | NOT NULL |

`position` is 0-based within a column. `board_id` is stored directly on cards (redundant with `column_id → board_id`) to allow a single `WHERE board_id = ?` query to load all cards without a join through columns.

## Design decisions

- **String IDs for columns and cards** match the frontend's existing ID scheme so the backend can return IDs the frontend uses directly.
- **Integer position for ordering** — on drag-and-drop reorder, positions for the affected column(s) are renumbered in a transaction.
- **UNIQUE(user_id) on boards** enforces the one-board-per-user constraint at the DB level rather than in application code.
- **Password hash stored** even in the MVP so the schema does not need to change when real auth is added.
