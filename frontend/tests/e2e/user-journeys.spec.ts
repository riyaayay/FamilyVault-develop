import { test, expect, Page } from "@playwright/test";

const EMAIL = process.env.E2E_EMAIL ?? "";
const PASSWORD = process.env.E2E_PASSWORD ?? "";

async function login(page: Page) {
  await page.goto("/login");
  await page.waitForLoadState("networkidle");
  await page.getByLabel("Email").fill(EMAIL);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Log In", exact: true }).click();
  await expect(page).toHaveURL(/dashboard/, { timeout: 15000 });
}

test("login lands on dashboard", async ({ page }) => {
  await login(page);
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await expect(page.getByText("Clan Trust Summary", { exact: true })).toBeVisible();
});

test("dashboard to inbox", async ({ page }) => {
  await login(page);
  await page.goto("/dashboard/inbox");
  await expect(page).toHaveURL(/dashboard\/inbox/);
});

test("vault shows capsules", async ({ page }) => {
  await login(page);
  await page.goto("/dashboard/vault");
  await expect(page.getByText("Arthur_Ancestral_Will.pdf")).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("Sophia_18th_Birthday.mp4")).toBeVisible();
});

test("capsule unseal via trustee signature", async ({ page }) => {
  await login(page);
  await page.goto("/dashboard/vault");
  await page.getByRole("button", { name: "Review and sign", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await dialog.getByRole("button", { name: "Sign as trustee", exact: true }).click();
  await expect(dialog.getByRole("button", { name: "Released", exact: true })).toBeVisible();
});

test("inbox accept and reject", async ({ page }) => {
  await page.route("**/api/v1/media/*/triage", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      headers: { "access-control-allow-origin": "*" },
      body: "{}",
    }),
  );
  await login(page);
  await page.goto("/dashboard/inbox");
  await page.getByRole("button", { name: "Accept", exact: true }).first().click();
  await expect(page.getByText("Accepted", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Reject", exact: true }).first().click();
  await expect(page.getByText("Rejected", { exact: true }).first()).toBeVisible();
});

test("emergency red alert opens medical dossier", async ({ page }) => {
  await login(page);
  await page.goto("/dashboard/family");
  await page.getByTitle("Emergency Red Alert Active - Click for Medical Dossier").first().click();
  await expect(page.getByText("Emergency Medical Red Alert")).toBeVisible({ timeout: 15000 });
  await expect(page.getByText("24-Hour Signed Offline Emergency QR")).toBeVisible();
  await page.getByRole("button", { name: "Dismiss Medical Alert Dossier" }).click();
  await expect(page.getByText("Emergency Medical Red Alert")).toBeHidden();
});
