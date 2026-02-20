import { defineConfig } from '@playwright/test';

const playwrightPort = process.env.PLAYWRIGHT_PORT || '18080';
const localBaseUrl = `http://127.0.0.1:${playwrightPort}`;
const baseURL = process.env.PLAYWRIGHT_BASE_URL || localBaseUrl;

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 120_000,
  expect: {
    timeout: 5_000,
  },
  retries: 0,
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  webServer: {
    command: `PORT=${playwrightPort} scripts/e2e-server.sh`,
    url: `${localBaseUrl}/docs`,
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
