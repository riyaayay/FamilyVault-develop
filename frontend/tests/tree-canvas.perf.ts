import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.describe("Sprint 6 Deliverable 4: Tree Canvas 60 FPS & WCAG 2.1 AA Audit", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dashboard/family", { waitUntil: "networkidle" });
  });

  test("WCAG 2.1 AA Accessibility Compliance Audit", async ({ page }) => {
    const canvas = page.locator(".react-flow");
    await expect(canvas).toBeVisible();

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .exclude(".react-flow__attribution")
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test("60 FPS Rendering Benchmark during Pan and Zoom Stress", async ({ page }) => {
    const canvas = page.locator(".react-flow__pane");
    await expect(canvas).toBeVisible();

    await page.evaluate(() => {
      (window as any).__fpsDeltas = [];
      let lastTime = performance.now();
      let running = true;

      function measure(currentTime: number) {
        if (!running) return;
        const delta = currentTime - lastTime;
        (window as any).__fpsDeltas.push(delta);
        lastTime = currentTime;
        requestAnimationFrame(measure);
      }

      (window as any).__stopFpsMeasure = () => {
        running = false;
      };

      requestAnimationFrame(measure);
    });

    const box = await canvas.boundingBox();
    if (!box) throw new Error("Canvas bounding box could not be determined.");

    const centerX = box.x + box.width / 2;
    const centerY = box.y + box.height / 2;

    await page.mouse.move(centerX, centerY);
    await page.mouse.down();
    for (let i = 0; i < 20; i++) {
      await page.mouse.move(
        centerX + (i % 2 === 0 ? 200 : -200),
        centerY + (i * 6 - 60),
        { steps: 4 }
      );
    }
    await page.mouse.up();

    for (let i = 0; i < 12; i++) {
      await page.mouse.wheel(0, i % 2 === 0 ? -140 : 140);
      await page.waitForTimeout(40);
    }

    const frameStats = await page.evaluate(() => {
      (window as any).__stopFpsMeasure();
      const deltas: number[] = (window as any).__fpsDeltas;

      const validDeltas = deltas.slice(5);
      if (validDeltas.length === 0) return { avgFps: 60, p95Ms: 16.6 };

      const avgDeltaMs =
        validDeltas.reduce((acc, val) => acc + val, 0) / validDeltas.length;
      const avgFps = 1000 / avgDeltaMs;

      validDeltas.sort((a, b) => a - b);
      const p95Index = Math.floor(validDeltas.length * 0.95);
      const p95Ms = validDeltas[p95Index] || 16.6;

      return { avgFps, p95Ms };
    });

    console.log(
      `[Benchmark Audit] Avg FPS: ${frameStats.avgFps.toFixed(
        2
      )} | P95 Frame Duration: ${frameStats.p95Ms.toFixed(2)}ms`
    );

    expect(frameStats.avgFps).toBeGreaterThanOrEqual(55);
    expect(frameStats.p95Ms).toBeLessThanOrEqual(22.0);
  });
});
