import { test, expect } from '../fixtures';

test('login page switches to English', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('combobox', { name: 'Język' }).selectOption({ label: '🇬🇧 English' });
  await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible();
});

// Selecting a template applies it immediately; nothing is saved, so other tests are unaffected.
test('Modern template applies the theme class', async ({ adminPage: page }) => {
  await page.goto('/#settings');
  await page.getByRole('button', { name: 'Szablony wyglądu' }).click();
  // Settings may finish loading after the first click and reset the selection, so retry the selection.
  await expect(async () => {
    await page.locator('input[name="ui-template"][value="modern"]').check();
    await expect(page.locator('html')).toHaveClass(/theme-modern/, { timeout: 1_000 });
  }).toPass();
});
