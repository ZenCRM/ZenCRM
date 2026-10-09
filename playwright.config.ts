import { defineConfig, devices } from '@playwright/test';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { randomBytes } from 'node:crypto';
import { baseURL, firstRunBaseURL } from './e2e/support/env';

const isCI = !!process.env.CI;
const python = process.platform === 'win32' ? 'venv\\Scripts\\python' : 'venv/bin/python';

// Local runs start the app twice from venv on throwaway databases: the main instance and an empty one for first-run tests.
function localServer(port: number) {
  const dir = mkdtempSync(join(tmpdir(), 'zencrm-e2e-'));
  return {
    command: `${python} run.py`,
    url: `http://127.0.0.1:${port}/api/auth/setup-status`,
    reuseExistingServer: false,
    timeout: 60_000,
    env: {
      PORT: String(port),
      DATABASE_URL: `sqlite:///${join(dir, 'zencrm.db')}`,
      SECRET_KEY: randomBytes(32).toString('hex'),
      JWT_SECRET_KEY: randomBytes(32).toString('hex'),
      PUSH_ENABLED: 'false',
      MAIL_POLLING_ENABLED: 'false',
    },
  };
}

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  reporter: isCI ? [['list'], ['html', { open: 'never' }]] : [['list']],
  globalSetup: './e2e/global-setup.ts',
  use: {
    baseURL,
    locale: 'pl-PL',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] }, testIgnore: /first-run\.spec\.ts/ },
    { name: 'first-run', use: { ...devices['Desktop Chrome'], baseURL: firstRunBaseURL }, testMatch: /first-run\.spec\.ts/ },
  ],
  webServer: process.env.BASE_URL ? undefined : [localServer(5101), localServer(5102)],
});
