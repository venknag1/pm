import type { BoardData, ChecklistItem } from "./kanban";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type BoardSummary = {
  id: number;
  title: string;
  created_at: string;
  card_count: number;
  done_count: number;
  pinned: boolean;
};

export type UserSummary = {
  id: number;
  username: string;
  is_admin: boolean;
  created_at: string;
  board_count: number;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

async function request(path: string, options?: RequestInit): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...options,
    headers: {
      ...(options?.body ? { "Content-Type": "application/json" } : {}),
      ...options?.headers,
    },
  });
}

// --- Auth ---

export async function login(username: string, password: string): Promise<{ username: string; is_admin: boolean }> {
  const resp = await request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  if (!resp.ok) throw new Error("Invalid credentials");
  return resp.json();
}

export async function register(username: string, password: string): Promise<void> {
  const resp = await request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body?.detail ?? "Registration failed");
  }
}

export async function logout(): Promise<void> {
  await request("/api/auth/logout", { method: "POST" });
}

export async function getMe(): Promise<{ username: string; is_admin: boolean } | null> {
  const resp = await request("/api/auth/me");
  if (!resp.ok) return null;
  return resp.json();
}

// --- Boards ---

export async function listBoards(): Promise<BoardSummary[]> {
  const resp = await request("/api/boards");
  if (!resp.ok) throw new Error("Failed to load boards");
  return resp.json();
}

export async function createBoard(title: string, template?: string): Promise<{ id: number; title: string }> {
  const resp = await request("/api/boards", {
    method: "POST",
    body: JSON.stringify({ title, template }),
  });
  if (!resp.ok) throw new Error("Failed to create board");
  return resp.json();
}

export async function renameBoard(boardId: number, title: string): Promise<void> {
  await request(`/api/boards/${boardId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
}

export async function deleteBoard(boardId: number): Promise<void> {
  const resp = await request(`/api/boards/${boardId}`, { method: "DELETE" });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body?.detail ?? "Failed to delete board");
  }
}

export async function getBoardById(boardId: number): Promise<BoardData> {
  const resp = await request(`/api/boards/${boardId}`);
  if (!resp.ok) throw new Error("Failed to load board");
  return resp.json();
}

// Legacy: get the user's first/primary board
export async function getBoard(): Promise<BoardData> {
  const resp = await request("/api/board");
  if (!resp.ok) throw new Error("Failed to load board");
  return resp.json();
}

// --- Columns ---

export async function createColumn(boardId: number, title: string): Promise<{ id: string; title: string }> {
  const resp = await request(`/api/boards/${boardId}/columns`, {
    method: "POST",
    body: JSON.stringify({ title }),
  });
  if (!resp.ok) throw new Error("Failed to create column");
  return resp.json();
}

export async function reorderColumns(boardId: number, columnIds: string[]): Promise<void> {
  await request(`/api/boards/${boardId}/columns/reorder`, {
    method: "PATCH",
    body: JSON.stringify({ column_ids: columnIds }),
  });
}

export async function deleteColumn(boardId: number, columnId: string): Promise<void> {
  const resp = await request(`/api/boards/${boardId}/columns/${columnId}`, {
    method: "DELETE",
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body?.detail ?? "Failed to delete column");
  }
}

export async function renameColumn(columnId: string, title: string): Promise<void> {
  await request(`/api/columns/${columnId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
}

// --- Cards ---

export async function createCard(
  columnId: string,
  title: string,
  details: string,
  options?: { due_date?: string; priority?: "low" | "medium" | "high"; label?: string }
): Promise<string> {
  const resp = await request("/api/cards", {
    method: "POST",
    body: JSON.stringify({ column_id: columnId, title, details, ...options }),
  });
  if (!resp.ok) throw new Error("Failed to create card");
  const data = await resp.json();
  return data.id;
}

export async function updateCard(
  cardId: string,
  updates: { title?: string; details?: string; due_date?: string; priority?: "low" | "medium" | "high"; label?: string }
): Promise<void> {
  await request(`/api/cards/${cardId}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export async function deleteCard(cardId: string): Promise<void> {
  await request(`/api/cards/${cardId}`, { method: "DELETE" });
}

export async function moveCard(
  cardId: string,
  columnId: string,
  position: number
): Promise<void> {
  await request(`/api/cards/${cardId}/move`, {
    method: "PATCH",
    body: JSON.stringify({ column_id: columnId, position }),
  });
}

export async function assignCard(cardId: string, assignedToId: number | null): Promise<void> {
  await request(`/api/cards/${cardId}/assign`, {
    method: "PATCH",
    body: JSON.stringify({ assigned_to_id: assignedToId }),
  });
}

export async function duplicateCard(cardId: string): Promise<{ id: string }> {
  const resp = await request(`/api/cards/${cardId}/duplicate`, { method: "POST" });
  if (!resp.ok) throw new Error("Failed to duplicate card");
  return resp.json();
}

// --- Checklist ---

export async function getChecklist(cardId: string): Promise<ChecklistItem[]> {
  const resp = await request(`/api/cards/${cardId}/checklist`);
  if (!resp.ok) throw new Error("Failed to load checklist");
  return resp.json();
}

export async function addChecklistItem(cardId: string, title: string): Promise<ChecklistItem> {
  const resp = await request(`/api/cards/${cardId}/checklist`, {
    method: "POST",
    body: JSON.stringify({ title }),
  });
  if (!resp.ok) throw new Error("Failed to add checklist item");
  return resp.json();
}

export async function updateChecklistItem(
  cardId: string,
  itemId: string,
  updates: { title?: string; completed?: boolean }
): Promise<ChecklistItem> {
  const resp = await request(`/api/cards/${cardId}/checklist/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
  if (!resp.ok) throw new Error("Failed to update checklist item");
  return resp.json();
}

export async function deleteChecklistItem(cardId: string, itemId: string): Promise<void> {
  await request(`/api/cards/${cardId}/checklist/${itemId}`, { method: "DELETE" });
}

// --- WIP limit ---

export async function setWipLimit(boardId: number, columnId: string, wipLimit: number | null): Promise<void> {
  await request(`/api/boards/${boardId}/columns/${columnId}/wip`, {
    method: "PATCH",
    body: JSON.stringify({ wip_limit: wipLimit }),
  });
}

// --- Board stats ---

export type BoardStats = {
  total_cards: number;
  cards_by_column: Record<string, number>;
  cards_by_priority: Record<string, number>;
  overdue_count: number;
  total_story_points: number;
  completed_column_id: string | null;
};

export async function getBoardStats(boardId: number): Promise<BoardStats> {
  const resp = await request(`/api/boards/${boardId}/stats`);
  if (!resp.ok) throw new Error("Failed to load stats");
  return resp.json();
}

// --- Users ---

export type UserBrief = { id: number; username: string };

export async function listUsers(): Promise<UserBrief[]> {
  const resp = await request("/api/users");
  if (!resp.ok) throw new Error("Failed to load users");
  return resp.json();
}

// --- Card comments ---

export type CardComment = {
  id: string;
  card_id: string;
  username: string;
  content: string;
  created_at: string;
};

export async function getComments(cardId: string): Promise<CardComment[]> {
  const resp = await request(`/api/cards/${cardId}/comments`);
  if (!resp.ok) throw new Error("Failed to load comments");
  return resp.json();
}

export async function addComment(cardId: string, content: string): Promise<CardComment> {
  const resp = await request(`/api/cards/${cardId}/comments`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
  if (!resp.ok) throw new Error("Failed to add comment");
  return resp.json();
}

export async function deleteComment(cardId: string, commentId: string): Promise<void> {
  await request(`/api/cards/${cardId}/comments/${commentId}`, { method: "DELETE" });
}

// --- Card archiving ---

export async function archiveCard(cardId: string): Promise<void> {
  await request(`/api/cards/${cardId}/archive`, { method: "POST" });
}

export async function unarchiveCard(cardId: string): Promise<void> {
  await request(`/api/cards/${cardId}/unarchive`, { method: "POST" });
}

export type ArchivedCard = { id: string; title: string; column_title: string };

export async function listArchivedCards(boardId: number): Promise<ArchivedCard[]> {
  const resp = await request(`/api/boards/${boardId}/archived`);
  if (!resp.ok) throw new Error("Failed to load archived cards");
  return resp.json();
}

// --- Activity log ---

export type ActivityEntry = {
  id: number;
  username: string;
  action: string;
  details: string;
  card_id: string | null;
  created_at: string;
};

export async function getBoardActivity(boardId: number): Promise<ActivityEntry[]> {
  const resp = await request(`/api/boards/${boardId}/activity`);
  if (!resp.ok) throw new Error("Failed to load activity");
  return resp.json();
}

// --- AI ---

export async function sendAIMessage(
  message: string,
  history: ChatMessage[],
  boardId?: number
): Promise<{ reply: string; board: BoardData | null }> {
  const path = boardId ? `/api/boards/${boardId}/ai` : "/api/ai";
  const resp = await request(path, {
    method: "POST",
    body: JSON.stringify({ message, history }),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body?.detail ?? "AI request failed");
  }
  return resp.json();
}

// --- Account ---

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  const resp = await request("/api/auth/password", {
    method: "PATCH",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body?.detail ?? "Failed to change password");
  }
}

// --- Admin ---

export async function adminListUsers(): Promise<UserSummary[]> {
  const resp = await request("/api/admin/users");
  if (!resp.ok) throw new Error("Failed to load users");
  return resp.json();
}

export async function adminDeleteUser(userId: number): Promise<void> {
  const resp = await request(`/api/admin/users/${userId}`, { method: "DELETE" });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body?.detail ?? "Failed to delete user");
  }
}

export async function adminPromoteUser(userId: number): Promise<void> {
  const resp = await request(`/api/admin/users/${userId}/promote`, { method: "PATCH" });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body?.detail ?? "Failed to promote user");
  }
}

// --- Move card to board ---

export async function moveCardToBoard(cardId: string, targetBoardId: number): Promise<void> {
  const resp = await request(`/api/cards/${cardId}/move-to-board`, {
    method: "POST",
    body: JSON.stringify({ target_board_id: targetBoardId }),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body?.detail ?? "Failed to move card");
  }
}

// --- Board export ---

export type BoardExportColumn = { column: string; cards: Record<string, unknown>[] };
export type BoardExport = { board: string; exported_at: string; columns: BoardExportColumn[] };

export async function exportBoard(boardId: number): Promise<BoardExport> {
  const resp = await request(`/api/boards/${boardId}/export`);
  if (!resp.ok) throw new Error("Failed to export board");
  return resp.json();
}

// --- Global search ---

export type CardSearchResult = {
  id: string;
  title: string;
  details: string;
  board_id: number;
  board_title: string;
  column_title: string;
  priority: string;
  label: string | null;
  due_date: string | null;
  story_points: number | null;
};

export async function searchCards(q: string): Promise<CardSearchResult[]> {
  const resp = await request(`/api/search?q=${encodeURIComponent(q)}`);
  if (!resp.ok) throw new Error("Search failed");
  return resp.json();
}

// --- Board pin ---

export async function pinBoard(boardId: number): Promise<void> {
  await request(`/api/boards/${boardId}/pin`, { method: "POST" });
}

export async function unpinBoard(boardId: number): Promise<void> {
  await request(`/api/boards/${boardId}/unpin`, { method: "POST" });
}
