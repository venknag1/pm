import { vi, type Mock } from "vitest";
import { login, logout, checkAuth } from "./auth";

const mockUser = { username: "user", is_admin: false };

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("login", () => {
  it("returns user object on 200 response", async () => {
    (fetch as Mock).mockResolvedValue({ ok: true, json: async () => mockUser });
    const result = await login("user", "password");
    expect(result).toEqual(mockUser);
  });

  it("returns null on non-200 response", async () => {
    (fetch as Mock).mockResolvedValue({ ok: false });
    expect(await login("user", "wrong")).toBeNull();
  });

  it("posts credentials as JSON to /api/auth/login", async () => {
    (fetch as Mock).mockResolvedValue({ ok: true, json: async () => mockUser });
    await login("user", "password");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/login"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ username: "user", password: "password" }),
      })
    );
  });
});

describe("logout", () => {
  it("posts to /api/auth/logout", async () => {
    (fetch as Mock).mockResolvedValue({ ok: true });
    await logout();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/logout"),
      expect.objectContaining({ method: "POST" })
    );
  });
});

describe("checkAuth", () => {
  it("returns user object when /api/auth/me succeeds", async () => {
    (fetch as Mock).mockResolvedValue({ ok: true, json: async () => mockUser });
    const result = await checkAuth();
    expect(result).toEqual(mockUser);
  });

  it("returns null when /api/auth/me fails", async () => {
    (fetch as Mock).mockResolvedValue({ ok: false });
    expect(await checkAuth()).toBeNull();
  });

  it("includes credentials in the request", async () => {
    (fetch as Mock).mockResolvedValue({ ok: true, json: async () => mockUser });
    await checkAuth();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/me"),
      expect.objectContaining({ credentials: "include" })
    );
  });
});
