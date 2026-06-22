import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, type Mock } from "vitest";
import { LoginPage } from "./LoginPage";

const mockUser = { username: "user", is_admin: false };

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("LoginPage", () => {
  it("renders username, password fields and a sign in button", () => {
    render(<LoginPage onLogin={() => {}} />);
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("calls onLogin after a successful API response", async () => {
    (fetch as Mock).mockResolvedValue({ ok: true, json: async () => mockUser });
    const onLogin = vi.fn();
    render(<LoginPage onLogin={onLogin} />);
    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => expect(onLogin).toHaveBeenCalledTimes(1));
    expect(onLogin).toHaveBeenCalledWith(mockUser);
  });

  it("shows an error alert on a failed API response", async () => {
    (fetch as Mock).mockResolvedValue({ ok: false });
    render(<LoginPage onLogin={() => {}} />);
    await userEvent.type(screen.getByLabelText(/username/i), "wrong");
    await userEvent.type(screen.getByLabelText(/password/i), "badpassword");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });

  it("does not call onLogin on a failed API response", async () => {
    (fetch as Mock).mockResolvedValue({ ok: false });
    const onLogin = vi.fn();
    render(<LoginPage onLogin={onLogin} />);
    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "wrongpass");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await screen.findByRole("alert");
    expect(onLogin).not.toHaveBeenCalled();
  });

  it("clears the error when the user starts typing after a failure", async () => {
    (fetch as Mock).mockResolvedValue({ ok: false });
    render(<LoginPage onLogin={() => {}} />);
    await userEvent.type(screen.getByLabelText(/username/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await screen.findByRole("alert");
    await userEvent.type(screen.getByLabelText(/username/i), "x");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows a link to switch to register mode", () => {
    render(<LoginPage onLogin={() => {}} />);
    expect(screen.getByRole("button", { name: /no account/i })).toBeInTheDocument();
  });

  it("switches to register mode on toggle click", async () => {
    render(<LoginPage onLogin={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /no account/i }));
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
  });

  it("shows error when registration API returns conflict", async () => {
    // First call (register) fails with 409, second call (login) succeeds
    (fetch as Mock)
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: "Username already taken" }),
      });
    render(<LoginPage onLogin={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /no account/i }));
    await userEvent.type(screen.getByLabelText(/username/i), "existing");
    await userEvent.type(screen.getByLabelText(/password/i), "password123");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/already taken/i);
  });
});
