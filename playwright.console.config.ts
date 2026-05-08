import { defineConfig, devices } from '@playwright/test';

const consolePort = process.env.PLAYWRIGHT_CONSOLE_PORT || '18110';
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${consolePort}`;

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: ['**/console-frontend.spec.ts'],
  timeout: 120_000,
  expect: {
    timeout: 8_000,
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.025,
    },
  },
  retries: 0,
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'console-chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'console-firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'console-webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'console-mobile-chromium',
      use: { ...devices['Pixel 7'] },
    },
    {
      name: 'console-mobile-webkit',
      use: { ...devices['iPhone 13'] },
    },
  ],
  webServer: {
    command: `pnpm --filter @agentgate/console exec next dev -H 127.0.0.1 -p ${consolePort}`,
    url: `${baseURL}/`,
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
