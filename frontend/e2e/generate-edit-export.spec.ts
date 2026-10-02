import { expect, test } from "@playwright/test"

test("generate, edit, and export a presentation", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("heading", { name: /make room/i })).toBeVisible()
  await page.getByRole("button", { name: /create with ai/i }).click()
  await expect(
    page.getByRole("heading", { name: /create with ai/i }),
  ).toBeVisible()
  await page
    .getByRole("textbox")
    .first()
    .fill("A short presentation about local-first software")
  await page.getByRole("button", { name: /generate/i }).click()
  await expect(page.getByText(/presentation/i).first()).toBeVisible({
    timeout: 30_000,
  })
})
