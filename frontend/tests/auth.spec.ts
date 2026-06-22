import { expect, test } from "@playwright/test";

test("shows login page on first visit", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});

test("shows error on wrong credentials", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel(/username/i).fill("wrong");
  await page.getByLabel(/password/i).fill("badpassword");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.getByRole("alert").filter({ hasText: /incorrect/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});

test("logs in with correct credentials and sees the board", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel(/username/i).fill("user");
  await page.getByLabel(/password/i).fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
  // User has exactly one board, so goes directly to board view
  await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("logs out and returns to login page", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel(/username/i).fill("user");
  await page.getByLabel(/password/i).fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
  await page.getByRole("button", { name: /log out/i }).click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});

test("session persists across page reload", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel(/username/i).fill("user");
  await page.getByLabel(/password/i).fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
  await page.reload();
  // After reload, user goes to boards selector (shows "Kanban Studio" heading)
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
});

test("shows registration toggle", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: /no account/i })).toBeVisible();
});

test("can switch to registration mode and back", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /no account/i }).click();
  await expect(page.getByRole("heading", { name: "Create account" })).toBeVisible();
  await page.getByRole("button", { name: /already have an account/i }).click();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});
