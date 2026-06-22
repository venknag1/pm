from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=6)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6)


class ReorderColumnsRequest(BaseModel):
    column_ids: list[str]


class CardData(BaseModel):
    id: str
    title: str
    details: str
    due_date: str | None = None
    priority: Literal["low", "medium", "high"] = "medium"
    label: str | None = None


class ColumnData(BaseModel):
    id: str
    title: str
    cardIds: list[str]


class BoardResponse(BaseModel):
    columns: list[ColumnData]
    cards: dict[str, CardData]


class BoardSummary(BaseModel):
    id: int
    title: str
    created_at: str
    card_count: int = 0


class RenameColumnRequest(BaseModel):
    title: str = Field(min_length=1)


class CreateColumnRequest(BaseModel):
    title: str = Field(min_length=1)


class CreateCardRequest(BaseModel):
    column_id: str
    title: str = Field(min_length=1)
    details: str = ""
    due_date: str | None = None
    priority: Literal["low", "medium", "high"] = "medium"
    label: str | None = None


class UpdateCardRequest(BaseModel):
    title: str | None = None
    details: str | None = None
    due_date: str | None = None
    priority: Literal["low", "medium", "high"] | None = None
    label: str | None = None


class MoveCardRequest(BaseModel):
    column_id: str
    position: int = Field(ge=0)


class CreateBoardRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)


class RenameBoardRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AIRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatMessage] = []


# --- AI structured output types ---

class CreateCardOp(BaseModel):
    column_id: str
    title: str = Field(min_length=1)
    details: str = ""


class MoveCardOp(BaseModel):
    card_id: str
    column_id: str
    position: int = Field(ge=0)


class RenameColumnOp(BaseModel):
    column_id: str
    title: str = Field(min_length=1)


class BoardUpdate(BaseModel):
    create_cards: list[CreateCardOp] = []
    delete_card_ids: list[str] = []
    move_cards: list[MoveCardOp] = []
    rename_columns: list[RenameColumnOp] = []


class AIResponseBody(BaseModel):
    reply: str
    board: BoardResponse | None = None


# --- Admin ---

class UserSummary(BaseModel):
    id: int
    username: str
    is_admin: bool
    created_at: str
    board_count: int = 0
