import { test, expect } from '../fixtures';

test('public helpdesk renders', async ({ page }) => {
  await page.goto('/pomoc');
  await expect(page.getByRole('heading', { name: 'W czym możemy Ci pomóc?' })).toBeVisible();
});

test('client portal renders', async ({ page }) => {
  await page.goto('/portal.html');
  await expect(page.locator('body')).not.toBeEmpty();
  await expect(page.getByRole('button').first()).toBeVisible();
});
