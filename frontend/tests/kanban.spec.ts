import { expect, test } from "@playwright/test";

const run = Date.now();

async function loginUser(page: Parameters<typeof test>[1] extends (arg: infer T) => unknown ? T : never) {
  await page.goto("/");
  await page.getByLabel(/username/i).fill("user");
  await page.getByLabel(/password/i).fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
  // User has exactly one board → goes directly to board view
  await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
}

test("loads the kanban board with five columns", async ({ page }) => {
  await loginUser(page);
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  await loginUser(page);
  const title = `E2E-Card-${run}`;
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill(title);
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText(title)).toBeVisible();
});

test("moves a card between columns via drag and drop", async ({ page }) => {
  await loginUser(page);
  const title = `DragCard-${run}`;

  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill(title);
  await firstColumn.getByRole("button", { name: /add card/i }).click();

  const card = firstColumn.locator('[data-testid^="card-"]').filter({ hasText: title });
  await expect(card).toBeVisible();

  const targetColumn = page.getByTestId("column-col-done");
  const cardBox = await card.boundingBox();
  const columnBox = await targetColumn.boundingBox();
  if (!cardBox || !columnBox) throw new Error("Unable to resolve drag coordinates.");

  await page.mouse.move(cardBox.x + cardBox.width / 2, cardBox.y + cardBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(columnBox.x + columnBox.width / 2, columnBox.y + 120, { steps: 12 });
  await page.mouse.up();

  await expect(targetColumn.getByText(title)).toBeVisible();
});

test("filter bar appears when filter button is clicked", async ({ page }) => {
  await loginUser(page);
  await page.getByRole("button", { name: /filter/i }).click();
  await expect(page.getByPlaceholder(/search cards/i)).toBeVisible();
});

test("add column button shows column form", async ({ page }) => {
  await loginUser(page);
  await page.getByRole("button", { name: /add column/i }).click();
  await expect(page.getByPlaceholder(/column title/i)).toBeVisible();
});

test("back button goes to board selector", async ({ page }) => {
  await loginUser(page);
  await page.getByLabel(/back to boards/i).click();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.getByText("Your Boards")).toBeVisible();
});
