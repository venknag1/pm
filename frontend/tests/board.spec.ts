import { expect, test } from "@playwright/test";

async function login(page: Parameters<typeof test>[1] extends (arg: infer T) => unknown ? T : never) {
  await page.goto("/");
  await page.getByLabel(/username/i).fill("user");
  await page.getByLabel(/password/i).fill("password");
  await page.getByRole("button", { name: /sign in/i }).click();
  // User has exactly one board → goes directly to board view
  await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
}

// Use a unique suffix per test run so repeated runs don't accumulate stale data
const run = Date.now();

test("created card persists after reload", async ({ page }) => {
  await login(page);
  const title = `Persistent-${run}`;

  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill(title);
  await firstColumn.getByPlaceholder("Details").fill("Still here after reload");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText(title)).toBeVisible();

  await page.reload();
  // After reload, user lands on board selector; click the board to open it
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await page.locator('.group').filter({ hasText: "My Board" }).first().click();
  await expect(page.locator('[data-testid^="column-"]').first().getByText(title)).toBeVisible();
});

test("deleted card does not reappear after reload", async ({ page }) => {
  await login(page);
  const title = `Temporary-${run}`;

  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill(title);
  await firstColumn.getByRole("button", { name: /add card/i }).click();

  const card = firstColumn.locator('[data-testid^="card-"]').filter({ hasText: title });
  await expect(card).toBeVisible();

  await card.locator(`button[aria-label="Delete ${title}"]`).click();
  await expect(firstColumn.getByText(title)).not.toBeVisible();

  await page.reload();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  // Go back into the board
  await page.locator('.group').filter({ hasText: "My Board" }).first().click();
  await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
  await expect(page.getByText(title)).not.toBeVisible();
});

test("renamed column persists after reload", async ({ page }) => {
  await login(page);
  const newTitle = `Renamed-${run}`;

  const firstColumn = page.locator('[data-testid^="column-"]').first();
  const titleInput = firstColumn.getByLabel("Column title");
  await titleInput.fill(newTitle);
  await page.keyboard.press("Tab");

  await page.reload();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await page.locator('.group').filter({ hasText: "My Board" }).first().click();
  await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]').first().getByLabel("Column title")).toHaveValue(newTitle);
});

test("moved card appears in new column after reload", async ({ page }) => {
  await login(page);
  const title = `MovedCard-${run}`;

  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill(title);
  await firstColumn.getByRole("button", { name: /add card/i }).click();

  const card = firstColumn.locator('[data-testid^="card-"]').filter({ hasText: title });
  await expect(card).toBeVisible();

  const doneColumn = page.getByTestId("column-col-done");
  const cardBox = await card.boundingBox();
  const colBox = await doneColumn.boundingBox();
  if (!cardBox || !colBox) throw new Error("Unable to resolve bounding boxes.");

  await page.mouse.move(cardBox.x + cardBox.width / 2, cardBox.y + cardBox.height / 2);
  await page.mouse.down();
  await page.mouse.move(colBox.x + colBox.width / 2, colBox.y + 120, { steps: 12 });
  await page.mouse.up();

  await expect(doneColumn.getByText(title)).toBeVisible();

  await page.reload();
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await page.locator('.group').filter({ hasText: "My Board" }).first().click();
  await expect(page.locator('[data-testid^="column-"]').first()).toBeVisible();
  await expect(page.getByTestId("column-col-done").getByText(title)).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]').first().getByText(title)).not.toBeVisible();
});
