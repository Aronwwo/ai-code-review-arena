import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'EVIDENCE/playwright-report', open: 'never' }],
  ],
  outputDir: 'EVIDENCE/playwright',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  webServer: {
    command: 'node scripts/e2e-servers.js',
    url: 'http://127.0.0.1:5173',
    timeout: 120_000,
    reuseExistingServer: false,
  },
});
