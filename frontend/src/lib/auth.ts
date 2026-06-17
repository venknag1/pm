const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";

async function post(path: string, body?: object): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    method: "POST",
    credentials: "include",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
}

export async function login(username: string, password: string): Promise<boolean> {
  const resp = await post("/api/auth/login", { username, password });
  return resp.ok;
}

export async function logout(): Promise<void> {
  await post("/api/auth/logout");
}

export async function checkAuth(): Promise<boolean> {
  const resp = await fetch(`${API_BASE}/api/auth/me`, { credentials: "include" });
  return resp.ok;
}
