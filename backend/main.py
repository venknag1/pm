import json
import os
import random
import string
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI
from pydantic import ValidationError

from .auth import create_session_token, get_current_user_id, verify_password
from .db import get_db, init_db
from .models import (
    AIRequest,
    AIResponseBody,
    BoardResponse,
    BoardUpdate,
    CardData,
    ColumnData,
    CreateCardRequest,
    LoginRequest,
    MoveCardRequest,
    RenameColumnRequest,
    UpdateCardRequest,
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
AI_MODEL = "meta-llama/llama-3.3-70b-instruct"

_AI_SYSTEM_PROMPT = """\
You are a helpful assistant for a Kanban board. You can read and modify the board.

Board state — columns are listed in left-to-right order; the "position" field is their \
0-based index (0 = leftmost):
{board_json}

Respond ONLY with a valid JSON object. No text outside the JSON.

When the user asks a question only:
{{"reply": "<answer>", "board_update": null}}

When the user asks for board changes:
{{"reply": "<confirmation>", "board_update": {{"move_cards": [...], "create_cards": [...], "delete_card_ids": [...], "rename_columns": [...]}}}}

board_update fields (all are optional lists — omit any you don't need):
  "move_cards"      — [{{"card_id": "<id>", "column_id": "<target-column-id>", "position": <0-based slot in target column>}}]
  "create_cards"    — [{{"column_id": "<id>", "title": "<title>", "details": "<details>"}}]
  "delete_card_ids" — ["<card-id>"]
  "rename_columns"  — [{{"column_id": "<id>", "title": "<new-title>"}}]

Rules:
- Use exact IDs from the board state — never invent IDs.
- "Left" means the column at position N-1; "right" means position N+1.
- Cards already in the leftmost column (position 0) cannot go further left — skip them.
- position inside move_cards is the 0-based index within the destination column.
- When the user asks for changes, board_update must NOT be null.\
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
    board = db.execute("SELECT * FROM boards WHERE user_id = ?", (user_id,)).fetchone()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    return board


def _build_board_response(db, user_id: int) -> BoardResponse:
    board = _get_board(db, user_id)
    cols = db.execute(
        "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position",
        (board["id"],),
    ).fetchall()
    all_cards = db.execute(
        "SELECT id, column_id, title, details FROM cards WHERE board_id = ? ORDER BY position",
        (board["id"],),
    ).fetchall()
    card_ids_by_col: dict[str, list[str]] = {col["id"]: [] for col in cols}
    cards_map: dict[str, CardData] = {}
    for card in all_cards:
        card_ids_by_col[card["column_id"]].append(card["id"])
        cards_map[card["id"]] = CardData(
            id=card["id"], title=card["title"], details=card["details"]
        )
    return BoardResponse(
        columns=[
            ColumnData(id=col["id"], title=col["title"], cardIds=card_ids_by_col[col["id"]])
            for col in cols
        ],
        cards=cards_map,
    )


def _board_for_prompt(db, user_id: int) -> dict:
    """Return a simplified board dict suitable for the AI system prompt."""
    board = _get_board(db, user_id)
    cols = db.execute(
        "SELECT id, title FROM columns WHERE board_id = ? ORDER BY position",
        (board["id"],),
    ).fetchall()
    all_cards = db.execute(
        "SELECT id, column_id, title, details FROM cards WHERE board_id = ? ORDER BY position",
        (board["id"],),
    ).fetchall()
    cards_by_col: dict[str, list[dict]] = {col["id"]: [] for col in cols}
    for card in all_cards:
        cards_by_col[card["column_id"]].append({
            "id": card["id"],
            "title": card["title"],
            "details": card["details"],
        })
    return {
        "columns": [
            {"position": i, "id": col["id"], "title": col["title"], "cards": cards_by_col[col["id"]]}
            for i, col in enumerate(cols)
        ]
    }


def _apply_board_update(db, board_id: str, update: BoardUpdate) -> bool:
    """Apply AI-generated board mutations. Returns True if any changes were made."""
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


# --- Auth ---

@app.get("/api/health")
def health():
    return {"status": "ok"}


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
    return {"username": user["username"]}


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(key="session")
    return {"ok": True}


@app.get("/api/auth/me")
def me(user_id: int = Depends(get_current_user_id), db=Depends(get_db)):
    user = db.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"username": user["username"]}


# --- Board ---

@app.get("/api/board", response_model=BoardResponse)
def get_board(user_id: int = Depends(get_current_user_id), db=Depends(get_db)):
    return _build_board_response(db, user_id)


# --- Columns ---

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


# --- Cards ---

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
    with db:
        db.execute(
            "INSERT INTO cards (id, board_id, column_id, title, details, position)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (card_id, board["id"], req.column_id, req.title, req.details, max_pos + 1),
        )
    return {"id": card_id}


@app.patch("/api/cards/{card_id}")
def update_card(
    card_id: str,
    req: UpdateCardRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    board = _get_board(db, user_id)
    card = db.execute(
        "SELECT id, title, details FROM cards WHERE id = ? AND board_id = ?",
        (card_id, board["id"]),
    ).fetchone()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    with db:
        db.execute(
            "UPDATE cards SET title = ?, details = ? WHERE id = ?",
            (
                req.title if req.title is not None else card["title"],
                req.details if req.details is not None else card["details"],
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
    board = _get_board(db, user_id)
    card = db.execute(
        "SELECT column_id, position FROM cards WHERE id = ? AND board_id = ?",
        (card_id, board["id"]),
    ).fetchone()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    with db:
        db.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        db.execute(
            "UPDATE cards SET position = position - 1"
            " WHERE column_id = ? AND position > ?",
            (card["column_id"], card["position"]),
        )
    return {"ok": True}


@app.patch("/api/cards/{card_id}/move")
def move_card(
    card_id: str,
    req: MoveCardRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    board = _get_board(db, user_id)
    card = db.execute(
        "SELECT column_id, position FROM cards WHERE id = ? AND board_id = ?",
        (card_id, board["id"]),
    ).fetchone()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    if not db.execute(
        "SELECT 1 FROM columns WHERE id = ? AND board_id = ?", (req.column_id, board["id"])
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


# --- AI ---

@app.post("/api/ai", response_model=AIResponseBody)
async def ai_chat(
    req: AIRequest,
    user_id: int = Depends(get_current_user_id),
    db=Depends(get_db),
):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="AI service not configured")

    board = _get_board(db, user_id)
    board_json = json.dumps(_board_for_prompt(db, user_id), indent=2)
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

    # Strip markdown code fences
    stripped = raw.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1]
        stripped = stripped.rsplit("```", 1)[0].strip()

    # If the model prefixed preamble text, find the outermost JSON object
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
        if _apply_board_update(db, board["id"], update):
            updated_board = _build_board_response(db, user_id)

    return AIResponseBody(reply=reply, board=updated_board)


public_dir = Path(__file__).resolve().parent / "public"
if public_dir.exists():
    app.mount("/", StaticFiles(directory=public_dir, html=True), name="public")
