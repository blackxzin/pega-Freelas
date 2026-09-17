import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './browser-tests',
  use: {
    browserName: 'chromium',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  reporter: 'list',
});
