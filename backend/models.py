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
    assigned_to_username: str | None = None
    checklist_count: int = 0
    checklist_done: int = 0
    story_points: int | None = None


class ColumnData(BaseModel):
    id: str
    title: str
    cardIds: list[str]
    wip_limit: int | None = None


class BoardResponse(BaseModel):
    columns: list[ColumnData]
    cards: dict[str, CardData]


class BoardSummary(BaseModel):
    id: int
    title: str
    created_at: str
    card_count: int = 0
    done_count: int = 0
    pinned: bool = False


class CardSearchResult(BaseModel):
    id: str
    title: str
    details: str
    board_id: int
    board_title: str
    column_title: str
    priority: str
    label: str | None = None
    due_date: str | None = None
    story_points: int | None = None


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
    story_points: int | None = Field(default=None, ge=0, le=999)


class AssignCardRequest(BaseModel):
    assigned_to_id: int | None = None


class ChecklistItem(BaseModel):
    id: str
    title: str
    completed: bool
    position: int


class CreateChecklistItemRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class UpdateChecklistItemRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    completed: bool | None = None


class SetWipLimitRequest(BaseModel):
    wip_limit: int | None = Field(default=None, ge=1)


class BoardStats(BaseModel):
    total_cards: int
    cards_by_column: dict[str, int]
    cards_by_priority: dict[str, int]
    overdue_count: int
    total_story_points: int = 0
    completed_column_id: str | None = None


class MoveCardRequest(BaseModel):
    column_id: str
    position: int = Field(ge=0)


class CreateBoardRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    template: str | None = None  # "sprint" | "marketing" | "bug-tracker" | "kanban"


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


class UserBrief(BaseModel):
    id: int
    username: str


class CardComment(BaseModel):
    id: str
    card_id: str
    username: str
    content: str
    created_at: str


class CreateCommentRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class ActivityEntry(BaseModel):
    id: int
    username: str
    action: str
    details: str
    card_id: str | None = None
    created_at: str


class ArchivedCard(BaseModel):
    id: str
    title: str
    column_title: str
    archived_at: str | None = None


class MoveCardToBoardRequest(BaseModel):
    target_board_id: int


class BoardExportColumn(BaseModel):
    column: str
    cards: list[dict]


class BoardExportResponse(BaseModel):
    board: str
    exported_at: str
    columns: list[BoardExportColumn]
