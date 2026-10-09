// Imports the base test on purpose: the shared page fixture would fail on the deliberate error below.
import { test, expect } from '@playwright/test';
import { watchErrors } from '../fixtures';

test('guard ignores HTTP 4xx console echoes but reports page errors', async ({ page }) => {
  const problems = watchErrors(page);
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  expect(problems).toEqual([]); // the login page currently gets HTTP 422 from /api/custom-fields
  await page.evaluate(() => setTimeout(() => { throw new Error('boom'); }));
  await expect.poll(() => problems.length).toBe(1);
  expect(problems[0]).toContain('boom');
});
