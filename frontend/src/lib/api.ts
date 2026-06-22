import type { BoardData } from "./kanban";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type BoardSummary = {
  id: number;
  title: string;
  created_at: string;
  card_count: number;
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

export async function createBoard(title: string): Promise<{ id: number; title: string }> {
  const resp = await request("/api/boards", {
    method: "POST",
    body: JSON.stringify({ title }),
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
