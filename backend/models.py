from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class CardData(BaseModel):
    id: str
    title: str
    details: str


class ColumnData(BaseModel):
    id: str
    title: str
    cardIds: list[str]


class BoardResponse(BaseModel):
    columns: list[ColumnData]
    cards: dict[str, CardData]


class RenameColumnRequest(BaseModel):
    title: str = Field(min_length=1)


class CreateCardRequest(BaseModel):
    column_id: str
    title: str = Field(min_length=1)
    details: str = ""


class UpdateCardRequest(BaseModel):
    title: str | None = None
    details: str | None = None


class MoveCardRequest(BaseModel):
    column_id: str
    position: int = Field(ge=0)


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
