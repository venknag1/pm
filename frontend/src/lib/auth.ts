const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

async function post(path: string, body?: object): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
}

export type AuthUser = {
  username: string;
  is_admin: boolean;
};

export async function login(username: string, password: string): Promise<AuthUser | null> {
  const resp = await post("/api/auth/login", { username, password });
  if (!resp.ok) return null;
  return resp.json();
}

export async function logout(): Promise<void> {
  await post("/api/auth/logout");
}

export async function checkAuth(): Promise<AuthUser | null> {
  const resp = await fetch(`${API_BASE}/api/auth/me`, { credentials: "include" });
  if (!resp.ok) return null;
  return resp.json();
}
