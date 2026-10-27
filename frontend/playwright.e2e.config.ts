import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30000,
  retries: 0,
  workers: 1,
  use: {
    baseURL: "http://localhost:3000",
    video: "on",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    {
      name: "tablet",
      use: { ...devices["Desktop Chrome"], viewport: { width: 820, height: 1180 }, hasTouch: true },
    },
    { name: "mobile", use: { ...devices["Pixel 5"] } },
  ],
});
