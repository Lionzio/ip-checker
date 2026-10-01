import { defineConfig, devices } from "@playwright/test";

/**
 * Smoke e2e (S9-02): a página servida pelo Caddy do compose, falando com a API e o analyzer de
 * verdade. Suba o compose antes (`docker compose -f deploy/compose.yaml up --build -d --wait`).
 */
export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:8180",
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
