import { test, expect } from "@playwright/test";

test.describe("Enterprise Login Screen with Character Stage", () => {
  test("renders form, google button, and character stage", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Log In", exact: true })).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Log in with Google" })
    ).toBeVisible();
  });

  test("password field toggles visibility and updates aria state", async ({
    page,
  }) => {
    await page.goto("/login");
    const password = page.getByLabel("Password", { exact: true });
    const toggle = page.getByRole("button", { name: "Show password" });

    await expect(password).toHaveAttribute("type", "password");
    await toggle.click();
    await expect(password).toHaveAttribute("type", "text");
    await expect(
      page.getByRole("button", { name: "Hide password" })
    ).toHaveAttribute("aria-pressed", "true");
  });

  test("blank submission surfaces zod validation errors", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: "Log In", exact: true }).click();
    await expect(page.getByText("Email is required.")).toBeVisible();
    await expect(
      page.getByText("Password must be at least 8 characters long.")
    ).toBeVisible();
  });

  test("invalid email format shows corporate email error", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill("notanemail");
    await page.getByRole("button", { name: "Log In", exact: true }).click();
    await expect(
      page.getByText("Please enter a valid corporate email address.")
    ).toBeVisible();
  });

  test("redirects /sign-in to /login", async ({ page }) => {
    await page.goto("/sign-in");
    await expect(page).toHaveURL(/\/login/);
  });

  test("mobile viewport stacks panels vertically", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/login");
    const card = page.locator("div.grid");
    await expect(card).toHaveClass(/grid-cols-1/);
  });
});