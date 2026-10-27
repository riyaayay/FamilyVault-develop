import { test, expect, Page } from "@playwright/test";
import fs from "fs";
import path from "path";

const EMAIL = process.env.E2E_EMAIL ?? "";
const PASSWORD = process.env.E2E_PASSWORD ?? "";

const VIEWPORTS = [
  { name: "mobile", width: 375, height: 812 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "desktop", width: 1280, height: 800 },
  { name: "wide", width: 1920, height: 1080 },
];

const ROUTES = [
  { path: "/", auth: false },
  { path: "/login", auth: false },
  { path: "/sign-in", auth: false },
  { path: "/sign-up", auth: false },
  { path: "/dashboard", auth: true },
  { path: "/dashboard/family", auth: true },
  { path: "/dashboard/inbox", auth: true },
  { path: "/dashboard/nuclear-family", auth: true },
  { path: "/dashboard/vault", auth: true },
];

type Result = {
  route: string;
  viewport: string;
  status: "PASS" | "FAIL";
  note: string;
};

const results: Result[] = [];

async function login(page: Page) {
  await page.goto("/login");
  await page.waitForLoadState("networkidle");

  await page.getByLabel("Email").fill(EMAIL);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);

  await page.getByRole("button", { name: "Log In", exact: true }).click();

  await expect(page).toHaveURL(/dashboard/, { timeout: 15000 });
}

test.describe("Responsive viewport gate", () => {
  test.afterAll(() => {
    const header =
      "# Mobile / Responsive Verification Log\n\n" +
      `Generated: ${new Date().toISOString()}\n\n` +
      "| Route | " +
      VIEWPORTS.map((v) => `${v.width}px`).join(" | ") +
      " |\n" +
      "|---|" +
      VIEWPORTS.map(() => "---").join("|") +
      "|\n";

    const rows = ROUTES.map((r) => {
      const cells = VIEWPORTS.map((v) => {
        const hit = results.find(
          (x) => x.route === r.path && x.viewport === v.name
        );

        return hit
          ? hit.status === "PASS"
            ? "PASS"
            : `FAIL (${hit.note})`
          : "-";
      });

      return `| \`${r.path}\` | ${cells.join(" | ")} |`;
    }).join("\n");

    const out = path.resolve(
      process.cwd(),
      "../docs/MOBILE_VERIFICATION_LOG.md"
    );

    fs.writeFileSync(out, header + rows + "\n");
  });

  for (const vp of VIEWPORTS) {
    for (const route of ROUTES) {
      test(`${route.path} @ ${vp.width}px`, async ({ page }) => {
        if (route.auth) {
          test.skip(
            !EMAIL || !PASSWORD,
            "E2E_EMAIL / E2E_PASSWORD not set"
          );
        }

        try {
          await page.setViewportSize({
            width: vp.width,
            height: vp.height,
          });

          if (route.auth) {
            await login(page);
          }

          await page.goto(route.path);
          await page.waitForLoadState("networkidle");

          await expect(
            page.locator("main, h1, h2, form").first()
          ).toBeVisible();

          const overflow = await page.evaluate(
            () =>
              document.documentElement.scrollWidth -
              document.documentElement.clientWidth
          );

          expect(
            overflow,
            `horizontal overflow of ${overflow}px`
          ).toBeLessThanOrEqual(1);

          results.push({
            route: route.path,
            viewport: vp.name,
            status: "PASS",
            note: "",
          });
        } catch (e) {
          results.push({
            route: route.path,
            viewport: vp.name,
            status: "FAIL",
            note: String((e as Error).message)
              .split("\n")[0]
              .slice(0, 60),
          });

          throw e;
        }
      });
    }
  }
});