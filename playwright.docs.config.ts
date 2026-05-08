import { defineConfig, devices } from '@playwright/test';

const docsPort = process.env.PLAYWRIGHT_DOCS_PORT || '18090';
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${docsPort}`;

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: ['**/docs-frontend-*.spec.ts', '**/visual-regression.spec.ts'],
  timeout: 120_000,
  expect: {
    timeout: 8_000,
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.02,
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
      name: 'docs-visual-chromium',
      testMatch: /visual-regression\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'docs-chromium',
      testIgnore: /visual-regression\.spec\.ts/,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'docs-firefox',
      testIgnore: /visual-regression\.spec\.ts/,
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'docs-webkit',
      testIgnore: /visual-regression\.spec\.ts/,
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'docs-mobile-chromium',
      testIgnore: /visual-regression\.spec\.ts/,
      use: { ...devices['Pixel 7'] },
    },
    {
      name: 'docs-mobile-webkit',
      testIgnore: /visual-regression\.spec\.ts/,
      use: { ...devices['iPhone 13'] },
    },
  ],
  webServer: {
    command: `.venv/bin/mkdocs build --strict --site-dir artifacts/site && cp artifacts/site/404/index.html artifacts/site/404.html && python3 -m http.server ${docsPort} --bind 127.0.0.1 --directory artifacts/site`,
    url: `${baseURL}/`,
    reuseExistingServer: false,
    timeout: 120_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
