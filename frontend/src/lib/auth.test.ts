import { vi, type Mock } from "vitest";
import { login, logout, checkAuth } from "./auth";

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("login", () => {
  it("returns true on 200 response", async () => {
    (fetch as Mock).mockResolvedValue({ ok: true });
    expect(await login("user", "password")).toBe(true);
  });

  it("returns false on non-200 response", async () => {
    (fetch as Mock).mockResolvedValue({ ok: false });
    expect(await login("user", "wrong")).toBe(false);
  });

  it("posts credentials as JSON to /api/auth/login", async () => {
    (fetch as Mock).mockResolvedValue({ ok: true });
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
  it("returns true when /api/auth/me succeeds", async () => {
    (fetch as Mock).mockResolvedValue({ ok: true });
    expect(await checkAuth()).toBe(true);
  });

  it("returns false when /api/auth/me fails", async () => {
    (fetch as Mock).mockResolvedValue({ ok: false });
    expect(await checkAuth()).toBe(false);
  });

  it("includes credentials in the request", async () => {
    (fetch as Mock).mockResolvedValue({ ok: true });
    await checkAuth();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/me"),
      expect.objectContaining({ credentials: "include" })
    );
  });
});
