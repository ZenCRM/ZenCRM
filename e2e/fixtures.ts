import { test as base, expect, type Page } from '@playwright/test';
import { randomBytes } from 'node:crypto';
import { ADMIN, STORAGE, baseURL } from './support/env';
import { ApiClient } from './support/api';

// console.error messages that are known and harmless. Keep this list short and justified.
const ALLOWED_CONSOLE_ERRORS: RegExp[] = [
  // HTTP failures are judged by the response listener below, not by Chromium's console echo.
  /^Failed to load resource/,
  // Mail, signature and template previews render in iframes sandboxed without allow-scripts on purpose.
  /^Blocked script execution in 'about:(blank|srcdoc)' because the document's frame is sandboxed/,
];

export function watchErrors(page: Page): string[] {
  const problems: string[] = [];
  page.on('pageerror', error => problems.push(`page error: ${error.message}`));
  page.on('console', message => {
    if (message.type() === 'error' && !ALLOWED_CONSOLE_ERRORS.some(pattern => pattern.test(message.text()))) {
      problems.push(`console.error: ${message.text()}`);
    }
  });
  page.on('response', response => {
    if (response.url().includes('/api/') && response.status() >= 500) {
      problems.push(`HTTP ${response.status()} ${response.request().method()} ${response.url()}`);
    }
  });
  return problems;
}

type Fixtures = {
  adminPage: Page;
  employeePage: Page;
  api: ApiClient;
  uniqueName: (prefix: string) => string;
};

export const test = base.extend<Fixtures>({
  page: async ({ page }, use) => {
    const problems = watchErrors(page);
    await use(page);
    expect(problems, 'browser errors during the test').toEqual([]);
  },
  adminPage: async ({ browser }, use) => {
    const context = await browser.newContext({ storageState: STORAGE.admin });
    const page = await context.newPage();
    const problems = watchErrors(page);
    await use(page);
    await context.close();
    expect(problems, 'browser errors during the test').toEqual([]);
  },
  employeePage: async ({ browser }, use) => {
    const context = await browser.newContext({ storageState: STORAGE.employee });
    const page = await context.newPage();
    const problems = watchErrors(page);
    await use(page);
    await context.close();
    expect(problems, 'browser errors during the test').toEqual([]);
  },
  api: async ({}, use) => {
    await use(await ApiClient.login(baseURL, ADMIN.email, ADMIN.password));
  },
  uniqueName: async ({}, use) => {
    await use(prefix => `${prefix} E2E ${randomBytes(3).toString('hex')}`);
  },
});

export { expect };
