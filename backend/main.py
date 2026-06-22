import json
import os
import random
import string
import time
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI
from pydantic import ValidationError

from .auth import create_session_token, get_current_user_id, hash_password, verify_password
from .db import get_db, init_db
from .models import (
    ActivityEntry,
    AIRequest,
    AIResponseBody,
    ArchivedCard,
    AssignCardRequest,
    BoardExportResponse,
    BoardResponse,
    BoardStats,
    BoardSummary,
    CardSearchResult,
    BoardUpdate,
    CardComment,
    CardData,
    ChangePasswordRequest,
    ChecklistItem,
    ColumnData,
    CreateBoardRequest,
    CreateCardRequest,
    CreateChecklistItemRequest,
    CreateColumnRequest,
    CreateCommentRequest,
    LoginRequest,
    MoveCardRequest,
    MoveCardToBoardRequest,
    RegisterRequest,
    RenameBoardRequest,
    RenameColumnRequest,
    ReorderColumnsRequest,
    SetWipLimitRequest,
    UpdateCardRequest,
    UpdateChecklistItemRequest,
    UserBrief,
    UserSummary,
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
AI_MODEL = "openai/gpt-oss-120b:free"

BOARD_TEMPLATES: dict[str, list[tuple[str, int]]] = {
    "default": [("Backlog", 0), ("Discovery", 1), ("In Progress", 2), ("Review", 3), ("Done", 4)],
    "sprint": [("Backlog", 0), ("Sprint", 1), ("In Progress", 2), ("Review", 3), ("Done", 4)],
    "marketing": [("Ideas", 0), ("Planning", 1), ("In Production", 2), ("Review", 3), ("Published", 4)],
    "bug-tracker": [("Reported", 0), ("Triaged", 1), ("In Progress", 2), ("Testing", 3), ("Resolved", 4)],
    "kanban": [("To Do", 0), ("In Progress", 1), ("Done", 2)],
}

_AI_SYSTEM_PROMPT = """\
You are a Kanban board assistant. Output ONLY a JSON object — no preamble, no markdown.

BOARD STATE (columns ordered left-to-right; "position" is the 0-based column index):
{board_json}

Each card may include: id, title, details, priority (low/medium/high), due_date (YYYY-MM-DD), label.

CRITICAL — your "reply" text is shown to the user but does NOT change the board.
Board changes happen ONLY through the board_update field.
If board_update is null, NOTHING on the board changes, even if your reply says it did.
When the user asks for any board modification, board_update MUST contain the operations.

Output format:
{{"reply": "<one sentence for the user>", "board_update": <null or operations object>}}

When making board changes, board_update is an object with any combination of these keys:
  "move_cards":      [{{"card_id": "<EXACT id>", "column_id": "<EXACT col id>", "position": <0-based slot in target column>}}]
  "create_cards":    [{{"column_id": "<EXACT col id>", "title": "...", "details": "...", "priority": "low|medium|high", "due_date": "YYYY-MM-DD or omit", "label": "bug|feature|chore|design|docs or omit"}}]
  "delete_card_ids": ["<EXACT card id>"]
  "rename_columns":  [{{"column_id": "<EXACT col id>", "title": "..."}}]

Rules:
- Copy IDs verbatim from the board state above. Never shorten or invent IDs.
- "Left" means the column at position N-1. "Right" means the column at position N+1.
- Cards in the position-0 column are already at the far left — skip them when moving left.
- position in move_cards is the 0-based slot index within the target column.
- When creating cards, omit due_date and label if not specified by the user.\
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="PM MVP", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _new_id(prefix: str) -> str:
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    ts = hex(int(time.time() * 1000))[2:]
    return f"{prefix}-{rand}{ts}"


def _get_board(db, user_id: int):
    """Get the user's first/primary board (backward compat)."""
    board = db.execute(
        "SELECT * FROM boards WHERE user_id = ? ORDER BY id LIMIT 1", (user_id,)
    ).fetchone()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return board


def _get_board_by_id(db, board_id: int, user_id: int):
    """Get a specific board and verify it belongs to the user."""
    board = db.execute(
        "SELECT * FROM boards WHERE id = ? AND user_id = ?", (board_id, user_id)
    ).fetchone()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return board


def _build_board_response(db, board_id: int) -> BoardResponse:
    cols = db.execute(
        "SELECT id, title, wip_limit FROM columns WHERE board_id = ? ORDER BY position",
        (board_id,),
    ).fetchall()
    all_cards = db.execute(
        "SELECT c.id, c.column_id, c.title, c.details, c.due_date, c.priority, c.label,"
        " c.assigned_to, c.story_points, u.username AS assigned_to_username"
        " FROM cards c LEFT JOIN users u ON c.assigned_to = u.id"
        " WHERE c.board_id = ? AND c.archived = 0 ORDER BY c.position",
        (board_id,),
    ).fetchall()

    # Aggregate checklist counts per card in one query
    checklist_counts = db.execute(
        "SELECT ci.card_id, COUNT(*) AS total, SUM(ci.completed) AS done"
        " FROM checklist_items ci"
        " JOIN cards c ON ci.card_id = c.id"
        " WHERE c.board_id = ? GROUP BY ci.card_id",
        (board_id,),
    ).fetchall()
    checklist_map = {row["card_id"]: (row["total"], int(row["done"] or 0)) for row in checklist_counts}

    card_ids_by_col: dict[str, list[str]] = {col["id"]: [] for col in cols}
    cards_map: dict[str, CardData] = {}
    for card in all_cards:
        card_ids_by_col[card["column_id"]].append(card["id"])
        cl_total, cl_done = checklist_map.get(card["id"], (0, 0))
        cards_map[card["id"]] = CardData(
            id=card["id"],
            title=card["title"],
            details=card["details"],
            due_date=card["due_date"],
            priority=card["priority"] or "medium",
            label=card["label"],
            assigned_to_username=card["assigned_to_username"],
            checklist_count=cl_total,
            checklist_done=cl_done,
            story_points=card["story_points"],
        )
    return BoardResponse(
        columns=[
            ColumnData(
                id=col["id"],
                title=col["title"],
                cardIds=card_ids_by_col[col["id"]],
                wip_limit=col["wip_limit"],
            )
            for col in cols
        ],
        cards=cards_map,
    )


def _board_for_prompt(db, board_id: int) -> dict:
    cols = db.execute(
        "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position",
        (board_id,),
    ).fetchall()
    all_cards = db.execute(
        "SELECT c.id, c.column_id, c.title, c.details, c.priority, c.due_date, c.label,"
        " u.username AS assigned_to_username"
        " FROM cards c LEFT JOIN users u ON c.assigned_to = u.id"
        " WHERE c.board_id = ? ORDER BY c.position",
        (board_id,),
    ).fetchall()
    cards_by_col: dict[str, list[dict]] = {col["id"]: [] for col in cols}
    for card in all_cards:
        entry: dict = {
            "id": card["id"],
            "title": card["title"],
            "details": card["details"],
            "priority": card["priority"] or "medium",
        }
        if card["due_date"]:
            entry["due_date"] = card["due_date"]
        if card["label"]:
            entry["label"] = card["label"]
        if card["assigned_to_username"]:
            entry["assigned_to"] = card["assigned_to_username"]
        cards_by_col[card["column_id"]].append(entry)
    return {
        "columns": [
            {"position": i, "id": col["id"], "title": col["title"], "cards": cards_by_col[col["id"]]}
            for i, col in enumerate(cols)
        ]
    }


def _apply_board_update(db, board_id: int, update: BoardUpdate) -> bool:
    valid_cols = {
        row["id"]
        for row in db.execute(
            "SELECT id FROM columns WHERE board_id = ?", (board_id,)
        ).fetchall()
    }
    valid_cards = {
        row["id"]
        for row in db.execute(
            "SELECT id FROM cards WHERE board_id = ?", (board_id,)
        ).fetchall()
    }

    changed = False

    with db:
        for op in update.rename_columns:
            if op.column_id in valid_cols:
                db.execute(
                    "UPDATE columns SET title = ? WHERE id = ?", (op.title, op.column_id)
                )
                changed = True

        for card_id in update.delete_card_ids:
            if card_id not in valid_cards:
                continue
            card = db.execute(
                "SELECT column_id, position FROM cards WHERE id = ?", (card_id,)
            ).fetchone()
            if card:
                db.execute("DELETE FROM cards WHERE id = ?", (card_id,))
                db.execute(
                    "UPDATE cards SET position = position - 1"
                    " WHERE column_id = ? AND position > ?",
                    (card["column_id"], card["position"]),
                )
                valid_cards.discard(card_id)
                changed = True

        for op in update.move_cards:
            if op.card_id not in valid_cards or op.column_id not in valid_cols:
                continue
            card = db.execute(
                "SELECT column_id, position FROM cards WHERE id = ?", (op.card_id,)
            ).fetchone()
            if not card:
                continue
            old_col, old_pos = card["column_id"], card["position"]
            new_col, new_pos = op.column_id, op.position
            if old_col == new_col and old_pos == new_pos:
                continue
            if old_col == new_col:
                if old_pos < new_pos:
                    db.execute(
                        "UPDATE cards SET position = position - 1"
                        " WHERE column_id = ? AND position > ? AND position <= ?",
                        (old_col, old_pos, new_pos),
                    )
                else:
                    db.execute(
                        "UPDATE cards SET position = position + 1"
                        " WHERE column_id = ? AND position >= ? AND position < ?",
                        (old_col, new_pos, old_pos),
                    )
                db.execute(
                    "UPDATE cards SET position = ? WHERE id = ?", (new_pos, op.card_id)
                )
            else:
                db.execute(
                    "UPDATE cards SET position = position - 1"
                    " WHERE column_id = ? AND position > ?",
                    (old_col, old_pos),
                )
                db.execute(
                    "UPDATE cards SET position = position + 1"
                    " WHERE column_id = ? AND position >= ?",
                    (new_col, new_pos),
                )
                db.execute(
                    "UPDATE cards SET column_id = ?, position = ? WHERE id = ?",
                    (new_col, new_pos, op.card_id),
                )
            changed = True

        for op in update.create_cards:
            if op.column_id not in valid_cols:
                continue
            max_pos = db.execute(
                "SELECT COALESCE(MAX(position), -1) FROM cards WHERE column_id = ?",
                (op.column_id,),
            ).fetchone()[0]
            card_id = _new_id("card")
            db.execute(
                "INSERT INTO cards (id, board_id, column_id, title, details, position)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (card_id, board_id, op.column_id, op.title, op.details, max_pos + 1),
            )
            changed = True

    return changed


def _require_admin(user_id: int, db) -> None:
    user = db.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user or not user["is_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")


def _log(db, board_id: int, user_id: int, action: str, details: str, card_id: str | None = None) -> None:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        "INSERT INTO activity_log (board_id, user_id, card_id, action, details, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (board_id, user_id, card_id, action, details, now),
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/api/auth/login")
def login(req: LoginRequest, response: Response, db=Depends(get_db)):
    user = db.execute(
        "SELECT * FROM users WHERE username = ?", (req.username,)
    ).fetchone()
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    response.set_cookie(
        key="session",
        value=create_session_token(user["id"]),
        httponly=True,
        samesite="lax",
    )
    return {"username": user["username"], "is_admin": bool(user["is_admin"])}


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(key="session")
    return {"ok": True}


@app.get("/api/auth/me")
def me(user_id: int = Depends(get_current_user_id), db=Depends(get_db)):
    user = db.execute(
        "SELECT username, is_admin FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"username": user["username"], "is_admin": bool(user["is_admin"])}


@app.patch("/api/auth/password")
def change_password(
    req: ChangePasswordRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    user = db.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user or not verify_password(req.current_password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    with db:
        db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(req.new_password), user_id),
        )
    return {"ok": True}


@app.post("/api/auth/register", status_code=201)
def register(req: RegisterRequest, db=Depends(get_db)):
    existing = db.execute(
        "SELECT 1 FROM users WHERE username = ?", (req.username,)
    ).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    from .db import DEFAULT_COLUMNS
    with db:
        db.execute(
            "INSERT INTO users (username, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?)",
            (req.username, hash_password(req.password), 0, now),
        )
        user_id = db.execute(
            "SELECT id FROM users WHERE username = ?", (req.username,)
        ).fetchone()["id"]
        db.execute(
            "INSERT INTO boards (user_id, title, created_at) VALUES (?, ?, ?)",
            (user_id, "My Board", now),
        )
        board_id = db.execute(
            "SELECT id FROM boards WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
        ).fetchone()["id"]
        for col_id, title, position in DEFAULT_COLUMNS:
            new_col_id = _new_id("col")
            db.execute(
                "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
                (new_col_id, board_id, title, position),
            )

    return {"username": req.username}


# ---------------------------------------------------------------------------
# Boards
# ---------------------------------------------------------------------------

@app.get("/api/boards", response_model=list[BoardSummary])
def list_boards(user_id: int = Depends(get_current_user_id), db=Depends(get_db)):
    boards = db.execute(
        "SELECT id, title, pinned, created_at FROM boards WHERE user_id = ? ORDER BY pinned DESC, id",
        (user_id,),
    ).fetchall()
    result = []
    for board in boards:
        card_count = db.execute(
            "SELECT COUNT(*) FROM cards WHERE board_id = ? AND archived = 0",
            (board["id"],),
        ).fetchone()[0]
        # "done" column = last column, or one titled done/complete/completed
        cols = db.execute(
            "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position",
            (board["id"],),
        ).fetchall()
        done_col_id = cols[-1]["id"] if cols else None
        for col in cols:
            if col["title"].lower() in ("done", "complete", "completed"):
                done_col_id = col["id"]
                break
        done_count = 0
        if done_col_id:
            done_count = db.execute(
                "SELECT COUNT(*) FROM cards WHERE column_id = ? AND archived = 0",
                (done_col_id,),
            ).fetchone()[0]
        result.append(BoardSummary(
            id=board["id"],
            title=board["title"],
            created_at=board["created_at"],
            card_count=card_count,
            done_count=done_count,
            pinned=bool(board["pinned"]),
        ))
    return result


@app.post("/api/boards", status_code=201)
def create_board(
    req: CreateBoardRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    columns = BOARD_TEMPLATES.get(req.template or "", BOARD_TEMPLATES["default"])
    with db:
        db.execute(
            "INSERT INTO boards (user_id, title, created_at) VALUES (?, ?, ?)",
            (user_id, req.title, now),
        )
        board_id = db.execute(
            "SELECT id FROM boards WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
        ).fetchone()["id"]
        for col_title, position in columns:
            col_id = _new_id("col")
            db.execute(
                "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
                (col_id, board_id, col_title, position),
            )
        _log(db, board_id, user_id, "board_created", f"Created board '{req.title}'")
    return {"id": board_id, "title": req.title}


@app.get("/api/boards/{board_id}", response_model=BoardResponse)
def get_board_by_id(
    board_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    board = _get_board_by_id(db, board_id, user_id)
    return _build_board_response(db, board["id"])


@app.patch("/api/boards/{board_id}")
def rename_board(
    board_id: int,
    req: RenameBoardRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_board_by_id(db, board_id, user_id)
    with db:
        db.execute("UPDATE boards SET title = ? WHERE id = ?", (req.title, board_id))
    return {"ok": True}


@app.post("/api/boards/{board_id}/pin")
def pin_board(
    board_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_board_by_id(db, board_id, user_id)
    with db:
        db.execute("UPDATE boards SET pinned = 1 WHERE id = ?", (board_id,))
    return {"ok": True}


@app.post("/api/boards/{board_id}/unpin")
def unpin_board(
    board_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_board_by_id(db, board_id, user_id)
    with db:
        db.execute("UPDATE boards SET pinned = 0 WHERE id = ?", (board_id,))
    return {"ok": True}


@app.delete("/api/boards/{board_id}")
def delete_board(
    board_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_board_by_id(db, board_id, user_id)
    # Verify user has more than one board before deleting
    board_count = db.execute(
        "SELECT COUNT(*) FROM boards WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    if board_count <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete your only board")
    with db:
        db.execute("DELETE FROM boards WHERE id = ?", (board_id,))
    return {"ok": True}


# ---------------------------------------------------------------------------
# Columns (board-specific)
# ---------------------------------------------------------------------------

@app.post("/api/boards/{board_id}/columns", status_code=201)
def create_column(
    board_id: int,
    req: CreateColumnRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_board_by_id(db, board_id, user_id)
    max_pos = db.execute(
        "SELECT COALESCE(MAX(position), -1) FROM columns WHERE board_id = ?",
        (board_id,),
    ).fetchone()[0]
    col_id = _new_id("col")
    with db:
        db.execute(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            (col_id, board_id, req.title, max_pos + 1),
        )
    return {"id": col_id, "title": req.title}


@app.delete("/api/boards/{board_id}/columns/{column_id}")
def delete_column(
    board_id: int,
    column_id: str,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_board_by_id(db, board_id, user_id)
    col = db.execute(
        "SELECT position FROM columns WHERE id = ? AND board_id = ?", (column_id, board_id)
    ).fetchone()
    if not col:
        raise HTTPException(status_code=404, detail="Column not found")
    col_count = db.execute(
        "SELECT COUNT(*) FROM columns WHERE board_id = ?", (board_id,)
    ).fetchone()[0]
    if col_count <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the only column")
    with db:
        db.execute("DELETE FROM columns WHERE id = ?", (column_id,))
        db.execute(
            "UPDATE columns SET position = position - 1 WHERE board_id = ? AND position > ?",
            (board_id, col["position"]),
        )
    return {"ok": True}


@app.patch("/api/boards/{board_id}/columns/reorder")
def reorder_columns(
    board_id: int,
    req: ReorderColumnsRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_board_by_id(db, board_id, user_id)
    existing_ids = {
        row["id"]
        for row in db.execute(
            "SELECT id FROM columns WHERE board_id = ?", (board_id,)
        ).fetchall()
    }
    # Only update positions for IDs that belong to this board
    valid = [cid for cid in req.column_ids if cid in existing_ids]
    with db:
        for position, col_id in enumerate(valid):
            db.execute(
                "UPDATE columns SET position = ? WHERE id = ?", (position, col_id)
            )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Board (legacy single-board endpoint — keeps old API working)
# ---------------------------------------------------------------------------

@app.get("/api/board", response_model=BoardResponse)
def get_board(user_id: int = Depends(get_current_user_id), db=Depends(get_db)):
    board = _get_board(db, user_id)
    return _build_board_response(db, board["id"])


# ---------------------------------------------------------------------------
# Columns (legacy route)
# ---------------------------------------------------------------------------

@app.patch("/api/columns/{column_id}")
def rename_column(
    column_id: str,
    req: RenameColumnRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    board = _get_board(db, user_id)
    if not db.execute(
        "SELECT 1 FROM columns WHERE id = ? AND board_id = ?", (column_id, board["id"])
    ).fetchone():
        raise HTTPException(status_code=404, detail="Column not found")
    with db:
        db.execute("UPDATE columns SET title = ? WHERE id = ?", (req.title, column_id))
    return {"ok": True}


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------

@app.post("/api/cards", status_code=201)
def create_card(
    req: CreateCardRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    board = _get_board(db, user_id)
    if not db.execute(
        "SELECT 1 FROM columns WHERE id = ? AND board_id = ?", (req.column_id, board["id"])
    ).fetchone():
        raise HTTPException(status_code=404, detail="Column not found")

    max_pos = db.execute(
        "SELECT COALESCE(MAX(position), -1) FROM cards WHERE column_id = ?",
        (req.column_id,),
    ).fetchone()[0]

    card_id = _new_id("card")
    col_title = db.execute("SELECT title FROM columns WHERE id = ?", (req.column_id,)).fetchone()["title"]
    with db:
        db.execute(
            "INSERT INTO cards (id, board_id, column_id, title, details, position,"
            " due_date, priority, label) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                card_id, board["id"], req.column_id, req.title, req.details,
                max_pos + 1, req.due_date, req.priority, req.label,
            ),
        )
        _log(db, board["id"], user_id, "card_created", f"Created '{req.title}' in '{col_title}'", card_id)
    return {"id": card_id}


@app.post("/api/boards/{board_id}/cards", status_code=201)
def create_card_on_board(
    board_id: int,
    req: CreateCardRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    board = _get_board_by_id(db, board_id, user_id)
    if not db.execute(
        "SELECT 1 FROM columns WHERE id = ? AND board_id = ?", (req.column_id, board["id"])
    ).fetchone():
        raise HTTPException(status_code=404, detail="Column not found")

    max_pos = db.execute(
        "SELECT COALESCE(MAX(position), -1) FROM cards WHERE column_id = ?",
        (req.column_id,),
    ).fetchone()[0]

    card_id = _new_id("card")
    col_title = db.execute("SELECT title FROM columns WHERE id = ?", (req.column_id,)).fetchone()["title"]
    with db:
        db.execute(
            "INSERT INTO cards (id, board_id, column_id, title, details, position,"
            " due_date, priority, label) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                card_id, board["id"], req.column_id, req.title, req.details,
                max_pos + 1, req.due_date, req.priority, req.label,
            ),
        )
        _log(db, board["id"], user_id, "card_created", f"Created '{req.title}' in '{col_title}'", card_id)
    return {"id": card_id}


@app.patch("/api/cards/{card_id}")
def update_card(
    card_id: str,
    req: UpdateCardRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    # Find the board this card belongs to (verify user owns it)
    card = db.execute(
        "SELECT c.id, c.title, c.details, c.due_date, c.priority, c.label, b.user_id"
        " FROM cards c JOIN boards b ON c.board_id = b.id WHERE c.id = ?",
        (card_id,),
    ).fetchone()
    if not card or card["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Card not found")
    with db:
        db.execute(
            "UPDATE cards SET title = ?, details = ?, due_date = ?, priority = ?, label = ?, story_points = ?"
            " WHERE id = ?",
            (
                req.title if req.title is not None else card["title"],
                req.details if req.details is not None else card["details"],
                req.due_date if req.due_date is not None else card["due_date"],
                req.priority if req.priority is not None else card["priority"],
                req.label if req.label is not None else card["label"],
                req.story_points,
                card_id,
            ),
        )
    return {"ok": True}


@app.delete("/api/cards/{card_id}")
def delete_card(
    card_id: str,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    card = db.execute(
        "SELECT c.column_id, c.position, c.title, c.board_id, b.user_id"
        " FROM cards c JOIN boards b ON c.board_id = b.id WHERE c.id = ?",
        (card_id,),
    ).fetchone()
    if not card or card["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Card not found")
    with db:
        db.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        db.execute(
            "UPDATE cards SET position = position - 1"
            " WHERE column_id = ? AND position > ?",
            (card["column_id"], card["position"]),
        )
        _log(db, card["board_id"], user_id, "card_deleted", f"Deleted card '{card['title']}'")
    return {"ok": True}


@app.post("/api/cards/{card_id}/archive")
def archive_card(
    card_id: str,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    card = db.execute(
        "SELECT c.id, c.title, c.board_id, b.user_id FROM cards c"
        " JOIN boards b ON c.board_id = b.id WHERE c.id = ?",
        (card_id,),
    ).fetchone()
    if not card or card["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Card not found")
    with db:
        db.execute("UPDATE cards SET archived = 1 WHERE id = ?", (card_id,))
        _log(db, card["board_id"], user_id, "card_archived", f"Archived card '{card['title']}'", card_id)
    return {"ok": True}


@app.post("/api/cards/{card_id}/unarchive")
def unarchive_card(
    card_id: str,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    card = db.execute(
        "SELECT c.id, c.title, c.board_id, b.user_id FROM cards c"
        " JOIN boards b ON c.board_id = b.id WHERE c.id = ?",
        (card_id,),
    ).fetchone()
    if not card or card["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Card not found")
    with db:
        db.execute("UPDATE cards SET archived = 0 WHERE id = ?", (card_id,))
        _log(db, card["board_id"], user_id, "card_unarchived", f"Restored card '{card['title']}'", card_id)
    return {"ok": True}


@app.get("/api/boards/{board_id}/archived", response_model=list[ArchivedCard])
def list_archived_cards(
    board_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_board_by_id(db, board_id, user_id)
    rows = db.execute(
        "SELECT c.id, c.title, col.title AS column_title"
        " FROM cards c JOIN columns col ON c.column_id = col.id"
        " WHERE c.board_id = ? AND c.archived = 1 ORDER BY c.id DESC",
        (board_id,),
    ).fetchall()
    return [ArchivedCard(id=r["id"], title=r["title"], column_title=r["column_title"]) for r in rows]


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------

@app.get("/api/boards/{board_id}/activity", response_model=list[ActivityEntry])
def get_activity(
    board_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_board_by_id(db, board_id, user_id)
    rows = db.execute(
        "SELECT al.id, u.username, al.action, al.details, al.card_id, al.created_at"
        " FROM activity_log al JOIN users u ON al.user_id = u.id"
        " WHERE al.board_id = ? ORDER BY al.created_at DESC LIMIT 100",
        (board_id,),
    ).fetchall()
    return [
        ActivityEntry(
            id=row["id"],
            username=row["username"],
            action=row["action"],
            details=row["details"],
            card_id=row["card_id"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Move card to a different board
# ---------------------------------------------------------------------------


@app.post("/api/cards/{card_id}/move-to-board")
def move_card_to_board(
    card_id: str,
    req: MoveCardToBoardRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_card_for_user(db, card_id, user_id)
    card_row = db.execute(
        "SELECT id, title, column_id, board_id, position FROM cards WHERE id = ?", (card_id,)
    ).fetchone()
    src_board_id = card_row["board_id"]

    if src_board_id == req.target_board_id:
        raise HTTPException(status_code=400, detail="Card is already on this board")

    target = db.execute(
        "SELECT id FROM boards WHERE id = ? AND user_id = ?",
        (req.target_board_id, user_id),
    ).fetchone()
    if not target:
        raise HTTPException(status_code=404, detail="Target board not found")

    first_col = db.execute(
        "SELECT id FROM columns WHERE board_id = ? ORDER BY position LIMIT 1",
        (req.target_board_id,),
    ).fetchone()
    if not first_col:
        raise HTTPException(status_code=400, detail="Target board has no columns")

    old_col_id = card_row["column_id"]
    old_pos = card_row["position"]
    max_pos = db.execute(
        "SELECT COALESCE(MAX(position), -1) FROM cards WHERE column_id = ?",
        (first_col["id"],),
    ).fetchone()[0]

    with db:
        db.execute(
            "UPDATE cards SET position = position - 1 WHERE column_id = ? AND position > ?",
            (old_col_id, old_pos),
        )
        db.execute(
            "UPDATE cards SET column_id = ?, board_id = ?, position = ? WHERE id = ?",
            (first_col["id"], req.target_board_id, max_pos + 1, card_id),
        )
        _log(db, src_board_id, user_id, "card_moved_out", f"Card '{card_row['title']}' moved to another board", card_id)
        _log(db, req.target_board_id, user_id, "card_moved_in", f"Card '{card_row['title']}' moved from another board", card_id)

    return {"ok": True}


# ---------------------------------------------------------------------------
# Board export
# ---------------------------------------------------------------------------


@app.get("/api/boards/{board_id}/export")
def export_board(
    board_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_board_by_id(db, board_id, user_id)
    board_row = db.execute("SELECT title FROM boards WHERE id = ?", (board_id,)).fetchone()
    columns = db.execute(
        "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position",
        (board_id,),
    ).fetchall()

    result_columns = []
    for col in columns:
        cards = db.execute(
            "SELECT c.title, c.details, c.priority, c.label, c.due_date, u.username AS assigned_to"
            " FROM cards c LEFT JOIN users u ON c.assigned_to = u.id"
            " WHERE c.column_id = ? AND c.archived = 0 ORDER BY c.position",
            (col["id"],),
        ).fetchall()
        result_columns.append({
            "column": col["title"],
            "cards": [dict(c) for c in cards],
        })

    return {
        "board": board_row["title"],
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "columns": result_columns,
    }


# ---------------------------------------------------------------------------
# Card comments
# ---------------------------------------------------------------------------

@app.get("/api/cards/{card_id}/comments", response_model=list[CardComment])
def get_comments(
    card_id: str,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_card_for_user(db, card_id, user_id)
    rows = db.execute(
        "SELECT cc.id, cc.card_id, u.username, cc.content, cc.created_at"
        " FROM card_comments cc JOIN users u ON cc.user_id = u.id"
        " WHERE cc.card_id = ? ORDER BY cc.created_at",
        (card_id,),
    ).fetchall()
    return [
        CardComment(
            id=row["id"],
            card_id=row["card_id"],
            username=row["username"],
            content=row["content"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


@app.post("/api/cards/{card_id}/comments", status_code=201, response_model=CardComment)
def add_comment(
    card_id: str,
    req: CreateCommentRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    card = _get_card_for_user(db, card_id, user_id)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    comment_id = _new_id("cmt")
    username = db.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()["username"]
    with db:
        db.execute(
            "INSERT INTO card_comments (id, card_id, user_id, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (comment_id, card_id, user_id, req.content, now),
        )
        _log(db, card["board_id"], user_id, "comment_added", f"Commented on card", card_id)
    return CardComment(id=comment_id, card_id=card_id, username=username, content=req.content, created_at=now)


@app.delete("/api/cards/{card_id}/comments/{comment_id}")
def delete_comment(
    card_id: str,
    comment_id: str,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_card_for_user(db, card_id, user_id)
    comment = db.execute(
        "SELECT id, user_id FROM card_comments WHERE id = ? AND card_id = ?",
        (comment_id, card_id),
    ).fetchone()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    # Only the comment author (or board owner) can delete
    if comment["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Cannot delete another user's comment")
    with db:
        db.execute("DELETE FROM card_comments WHERE id = ?", (comment_id,))
    return {"ok": True}


@app.patch("/api/cards/{card_id}/assign")
def assign_card(
    card_id: str,
    req: AssignCardRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    card = db.execute(
        "SELECT c.id, b.user_id FROM cards c JOIN boards b ON c.board_id = b.id WHERE c.id = ?",
        (card_id,),
    ).fetchone()
    if not card or card["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Card not found")
    if req.assigned_to_id is not None:
        user_exists = db.execute(
            "SELECT 1 FROM users WHERE id = ?", (req.assigned_to_id,)
        ).fetchone()
        if not user_exists:
            raise HTTPException(status_code=404, detail="User not found")
    with db:
        db.execute(
            "UPDATE cards SET assigned_to = ? WHERE id = ?",
            (req.assigned_to_id, card_id),
        )
    return {"ok": True}


@app.post("/api/cards/{card_id}/duplicate", status_code=201)
def duplicate_card(
    card_id: str,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    card = db.execute(
        "SELECT c.id, c.board_id, c.column_id, c.title, c.details, c.position,"
        " c.due_date, c.priority, c.label, c.assigned_to, b.user_id"
        " FROM cards c JOIN boards b ON c.board_id = b.id WHERE c.id = ?",
        (card_id,),
    ).fetchone()
    if not card or card["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Card not found")

    new_id = _new_id("card")
    with db:
        # Insert after original card
        db.execute(
            "UPDATE cards SET position = position + 1"
            " WHERE column_id = ? AND position > ?",
            (card["column_id"], card["position"]),
        )
        db.execute(
            "INSERT INTO cards (id, board_id, column_id, title, details, position,"
            " due_date, priority, label, assigned_to)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                new_id, card["board_id"], card["column_id"],
                card["title"] + " (copy)", card["details"],
                card["position"] + 1,
                card["due_date"], card["priority"], card["label"], card["assigned_to"],
            ),
        )
    return {"id": new_id}


# ---------------------------------------------------------------------------
# Checklist
# ---------------------------------------------------------------------------

def _get_card_for_user(db, card_id: str, user_id: int):
    """Return card row after verifying ownership. Allows archived cards."""
    card = db.execute(
        "SELECT c.id, c.board_id, b.user_id FROM cards c"
        " JOIN boards b ON c.board_id = b.id WHERE c.id = ?",
        (card_id,),
    ).fetchone()
    if not card or card["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@app.get("/api/cards/{card_id}/checklist", response_model=list[ChecklistItem])
def get_checklist(
    card_id: str,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_card_for_user(db, card_id, user_id)
    items = db.execute(
        "SELECT id, title, completed, position FROM checklist_items"
        " WHERE card_id = ? ORDER BY position",
        (card_id,),
    ).fetchall()
    return [
        ChecklistItem(id=row["id"], title=row["title"], completed=bool(row["completed"]), position=row["position"])
        for row in items
    ]


@app.post("/api/cards/{card_id}/checklist", status_code=201, response_model=ChecklistItem)
def add_checklist_item(
    card_id: str,
    req: CreateChecklistItemRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_card_for_user(db, card_id, user_id)
    max_pos = db.execute(
        "SELECT COALESCE(MAX(position), -1) FROM checklist_items WHERE card_id = ?",
        (card_id,),
    ).fetchone()[0]
    item_id = _new_id("chk")
    with db:
        db.execute(
            "INSERT INTO checklist_items (id, card_id, title, completed, position)"
            " VALUES (?, ?, ?, 0, ?)",
            (item_id, card_id, req.title, max_pos + 1),
        )
    return ChecklistItem(id=item_id, title=req.title, completed=False, position=max_pos + 1)


@app.patch("/api/cards/{card_id}/checklist/{item_id}", response_model=ChecklistItem)
def update_checklist_item(
    card_id: str,
    item_id: str,
    req: UpdateChecklistItemRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_card_for_user(db, card_id, user_id)
    item = db.execute(
        "SELECT id, title, completed, position FROM checklist_items WHERE id = ? AND card_id = ?",
        (item_id, card_id),
    ).fetchone()
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    new_title = req.title if req.title is not None else item["title"]
    new_completed = int(req.completed) if req.completed is not None else item["completed"]
    with db:
        db.execute(
            "UPDATE checklist_items SET title = ?, completed = ? WHERE id = ?",
            (new_title, new_completed, item_id),
        )
    return ChecklistItem(id=item_id, title=new_title, completed=bool(new_completed), position=item["position"])


@app.delete("/api/cards/{card_id}/checklist/{item_id}")
def delete_checklist_item(
    card_id: str,
    item_id: str,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_card_for_user(db, card_id, user_id)
    item = db.execute(
        "SELECT position FROM checklist_items WHERE id = ? AND card_id = ?",
        (item_id, card_id),
    ).fetchone()
    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    with db:
        db.execute("DELETE FROM checklist_items WHERE id = ?", (item_id,))
        db.execute(
            "UPDATE checklist_items SET position = position - 1"
            " WHERE card_id = ? AND position > ?",
            (card_id, item["position"]),
        )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Column WIP limit
# ---------------------------------------------------------------------------

@app.patch("/api/boards/{board_id}/columns/{column_id}/wip")
def set_wip_limit(
    board_id: int,
    column_id: str,
    req: SetWipLimitRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_board_by_id(db, board_id, user_id)
    col = db.execute(
        "SELECT id FROM columns WHERE id = ? AND board_id = ?", (column_id, board_id)
    ).fetchone()
    if not col:
        raise HTTPException(status_code=404, detail="Column not found")
    with db:
        db.execute(
            "UPDATE columns SET wip_limit = ? WHERE id = ?", (req.wip_limit, column_id)
        )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Board stats
# ---------------------------------------------------------------------------

@app.get("/api/boards/{board_id}/stats", response_model=BoardStats)
def get_board_stats(
    board_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _get_board_by_id(db, board_id, user_id)

    cols = db.execute(
        "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position",
        (board_id,),
    ).fetchall()

    all_cards = db.execute(
        "SELECT column_id, priority, due_date, story_points FROM cards WHERE board_id = ? AND archived = 0",
        (board_id,),
    ).fetchall()

    from datetime import date
    today = date.today().isoformat()

    cards_by_column: dict[str, int] = {col["id"]: 0 for col in cols}
    cards_by_priority: dict[str, int] = {"low": 0, "medium": 0, "high": 0}
    overdue_count = 0
    total_story_points = 0

    for card in all_cards:
        cards_by_column[card["column_id"]] = cards_by_column.get(card["column_id"], 0) + 1
        pri = card["priority"] or "medium"
        cards_by_priority[pri] = cards_by_priority.get(pri, 0) + 1
        if card["due_date"] and card["due_date"] < today:
            overdue_count += 1
        if card["story_points"]:
            total_story_points += card["story_points"]

    # Identify "done" column (last column by position, or one titled "Done")
    done_col_id = None
    if cols:
        done_col_id = cols[-1]["id"]
        for col in cols:
            if col["title"].lower() in ("done", "complete", "completed"):
                done_col_id = col["id"]
                break

    return BoardStats(
        total_cards=len(all_cards),
        cards_by_column={col["title"]: cards_by_column.get(col["id"], 0) for col in cols},
        cards_by_priority=cards_by_priority,
        overdue_count=overdue_count,
        total_story_points=total_story_points,
        completed_column_id=done_col_id,
    )


# ---------------------------------------------------------------------------
# Users list (for card assignment)
# ---------------------------------------------------------------------------

@app.get("/api/users", response_model=list[UserBrief])
def list_users(user_id: int = Depends(get_current_user_id), db=Depends(get_db)):
    users = db.execute("SELECT id, username FROM users ORDER BY username").fetchall()
    return [UserBrief(id=u["id"], username=u["username"]) for u in users]


# ---------------------------------------------------------------------------
# Global search
# ---------------------------------------------------------------------------


@app.get("/api/search", response_model=list[CardSearchResult])
def global_search(
    q: str,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    pattern = f"%{q.strip()}%"
    rows = db.execute(
        "SELECT c.id, c.title, c.details, c.board_id, b.title AS board_title,"
        " col.title AS column_title, c.priority, c.label, c.due_date, c.story_points"
        " FROM cards c"
        " JOIN boards b ON c.board_id = b.id"
        " JOIN columns col ON c.column_id = col.id"
        " WHERE b.user_id = ? AND c.archived = 0"
        " AND (c.title LIKE ? OR c.details LIKE ?)"
        " ORDER BY b.id, col.title, c.position"
        " LIMIT 50",
        (user_id, pattern, pattern),
    ).fetchall()
    return [
        CardSearchResult(
            id=row["id"],
            title=row["title"],
            details=row["details"],
            board_id=row["board_id"],
            board_title=row["board_title"],
            column_title=row["column_title"],
            priority=row["priority"] or "medium",
            label=row["label"],
            due_date=row["due_date"],
            story_points=row["story_points"],
        )
        for row in rows
    ]


@app.patch("/api/cards/{card_id}/move")
def move_card(
    card_id: str,
    req: MoveCardRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    card = db.execute(
        "SELECT c.column_id, c.position, c.board_id, b.user_id"
        " FROM cards c JOIN boards b ON c.board_id = b.id WHERE c.id = ?",
        (card_id,),
    ).fetchone()
    if not card or card["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Card not found")
    if not db.execute(
        "SELECT 1 FROM columns WHERE id = ? AND board_id = ?",
        (req.column_id, card["board_id"]),
    ).fetchone():
        raise HTTPException(status_code=404, detail="Column not found")

    old_col, old_pos = card["column_id"], card["position"]
    new_col, new_pos = req.column_id, req.position

    with db:
        if old_col == new_col:
            if old_pos == new_pos:
                return {"ok": True}
            if old_pos < new_pos:
                db.execute(
                    "UPDATE cards SET position = position - 1"
                    " WHERE column_id = ? AND position > ? AND position <= ?",
                    (old_col, old_pos, new_pos),
                )
            else:
                db.execute(
                    "UPDATE cards SET position = position + 1"
                    " WHERE column_id = ? AND position >= ? AND position < ?",
                    (old_col, new_pos, old_pos),
                )
            db.execute(
                "UPDATE cards SET position = ? WHERE id = ?", (new_pos, card_id)
            )
        else:
            db.execute(
                "UPDATE cards SET position = position - 1"
                " WHERE column_id = ? AND position > ?",
                (old_col, old_pos),
            )
            db.execute(
                "UPDATE cards SET position = position + 1"
                " WHERE column_id = ? AND position >= ?",
                (new_col, new_pos),
            )
            db.execute(
                "UPDATE cards SET column_id = ?, position = ? WHERE id = ?",
                (new_col, new_pos, card_id),
            )
    return {"ok": True}


# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------

async def _run_ai(board_id: int, req: AIRequest, db) -> AIResponseBody:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="AI service not configured")

    board_json = json.dumps(_board_for_prompt(db, board_id), indent=2)
    system_content = _AI_SYSTEM_PROMPT.format(board_json=board_json)

    messages: list[dict] = [{"role": "system", "content": system_content}]
    for msg in req.history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": req.message})

    client = AsyncOpenAI(api_key=api_key, base_url=OPENROUTER_BASE_URL)
    try:
        completion = await client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI service error: {exc}") from exc

    raw = completion.choices[0].message.content or ""
    print(f"[AI raw] {raw[:800]}", flush=True)

    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1]
        stripped = stripped.rsplit("```", 1)[0].strip()

    if not stripped.startswith("{"):
        start = stripped.find("{")
        end = stripped.rfind("}") + 1
        if start != -1 and end > start:
            stripped = stripped[start:end]

    try:
        parsed = json.loads(stripped)
        reply = str(parsed.get("reply", ""))
        raw_update = parsed.get("board_update")
    except (json.JSONDecodeError, AttributeError):
        print(f"[AI parse error] could not parse: {stripped[:400]}", flush=True)
        return AIResponseBody(reply=raw, board=None)

    updated_board = None
    if raw_update and isinstance(raw_update, dict):
        try:
            update = BoardUpdate(**raw_update)
        except (ValidationError, TypeError):
            update = BoardUpdate()
        if _apply_board_update(db, board_id, update):
            updated_board = _build_board_response(db, board_id)

    return AIResponseBody(reply=reply, board=updated_board)


@app.post("/api/ai", response_model=AIResponseBody)
async def ai_chat(
    req: AIRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    board = _get_board(db, user_id)
    return await _run_ai(board["id"], req, db)


@app.post("/api/boards/{board_id}/ai", response_model=AIResponseBody)
async def ai_chat_for_board(
    board_id: int,
    req: AIRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    board = _get_board_by_id(db, board_id, user_id)
    return await _run_ai(board["id"], req, db)


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@app.get("/api/admin/users", response_model=list[UserSummary])
def admin_list_users(
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _require_admin(user_id, db)
    users = db.execute(
        "SELECT id, username, is_admin, created_at FROM users ORDER BY id"
    ).fetchall()
    result = []
    for user in users:
        board_count = db.execute(
            "SELECT COUNT(*) FROM boards WHERE user_id = ?", (user["id"],)
        ).fetchone()[0]
        result.append(UserSummary(
            id=user["id"],
            username=user["username"],
            is_admin=bool(user["is_admin"]),
            created_at=user["created_at"],
            board_count=board_count,
        ))
    return result


@app.delete("/api/admin/users/{target_user_id}")
def admin_delete_user(
    target_user_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _require_admin(user_id, db)
    if target_user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    target = db.execute("SELECT id FROM users WHERE id = ?", (target_user_id,)).fetchone()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    with db:
        db.execute("DELETE FROM users WHERE id = ?", (target_user_id,))
    return {"ok": True}


@app.patch("/api/admin/users/{target_user_id}/promote")
def admin_promote_user(
    target_user_id: int,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    _require_admin(user_id, db)
    target = db.execute("SELECT id FROM users WHERE id = ?", (target_user_id,)).fetchone()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    with db:
        db.execute("UPDATE users SET is_admin = 1 WHERE id = ?", (target_user_id,))
    return {"ok": True}


public_dir = Path(__file__).resolve().parent / "public"
if public_dir.exists():
    app.mount("/", StaticFiles(directory=public_dir, html=True), name="public")
