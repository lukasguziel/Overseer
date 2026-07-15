// E2E tests run the real frontend (vite dev server, source — no build step)
// against a fully mocked /api/* (e2e/mock.ts): no Cinema 4D involved, and no
// request can leak to a live plugin server. Uses the system Chrome like the
// readme skill's screenshot rig — no browser download.
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  reporter: [['list']],
  timeout: 30_000,
  use: {
    baseURL: 'http://localhost:5199',
    channel: 'chrome',
    headless: true,
    viewport: { width: 1440, height: 900 },
  },
  webServer: {
    command: 'pnpm exec vite --port 5199 --strictPort',
    url: 'http://localhost:5199',
    reuseExistingServer: true,
    timeout: 60_000,
  },
})
