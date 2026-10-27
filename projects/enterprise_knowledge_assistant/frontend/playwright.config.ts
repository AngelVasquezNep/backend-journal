/** Browser acceptance runner; source imports share tsconfig's @/ mapping. */
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  tsconfig: './tsconfig.json',
  globalSetup: './tests/e2e/global-setup.ts',
  use: {
    baseURL: process.env.TASKIFY_BASE_URL ?? (process.env.TASKIFY_WEB_ONLY ? 'http://127.0.0.1:4173' : 'http://localhost:8080'),
    trace: 'off',
    screenshot: 'off',
    video: 'off',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: process.env.TASKIFY_WEB_ONLY ? {
    command: 'pnpm exec vite --host 127.0.0.1 --port 4173',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: false,
  } : undefined,
});
