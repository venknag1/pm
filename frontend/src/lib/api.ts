import type { BoardData } from "./kanban";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
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

export async function getBoard(): Promise<BoardData> {
  const resp = await request("/api/board");
  if (!resp.ok) throw new Error("Failed to load board");
  return resp.json();
}

export async function renameColumn(columnId: string, title: string): Promise<void> {
  await request(`/api/columns/${columnId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
}

export async function createCard(
  columnId: string,
  title: string,
  details: string
): Promise<string> {
  const resp = await request("/api/cards", {
    method: "POST",
    body: JSON.stringify({ column_id: columnId, title, details }),
  });
  if (!resp.ok) throw new Error("Failed to create card");
  const data = await resp.json();
  return data.id;
}

export async function updateCard(
  cardId: string,
  updates: { title?: string; details?: string }
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

export async function sendAIMessage(
  message: string,
  history: ChatMessage[]
): Promise<{ reply: string; board: BoardData | null }> {
  const resp = await request("/api/ai", {
    method: "POST",
    body: JSON.stringify({ message, history }),
  });
  if (!resp.ok) throw new Error("AI request failed");
  return resp.json();
}
