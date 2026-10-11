import { test, expect } from '../fixtures';

test('first run creates the administrator, then login and logout work', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Utwórz konto administratora' })).toBeVisible();
  await page.getByRole('textbox', { name: 'Imię' }).fill('Fiona');
  await page.getByRole('textbox', { name: 'Nazwisko', exact: true }).fill('First');
  await page.getByRole('textbox', { name: 'nazwisko@twojafirma.pl' }).fill('first@e2e.test');
  await page.getByRole('textbox', { name: '••••••••' }).nth(0).fill('E2e-First-Password-1');
  await page.getByRole('textbox', { name: '••••••••' }).nth(1).fill('E2e-First-Password-1');
  await page.getByRole('button', { name: 'Utwórz konto i zaloguj się' }).click();
  await expect(page.getByRole('heading', { name: 'Witaj, Fiona!' })).toBeVisible();

  await page.getByRole('button', { name: 'Menu profilu' }).click();
  await page.getByRole('button', { name: 'Wyloguj się' }).click();
  await expect(page.getByRole('heading', { name: 'Witaj ponownie!' })).toBeVisible();

  await page.getByRole('textbox', { name: 'nazwisko@twojafirma.pl' }).fill('first@e2e.test');
  await page.getByRole('textbox', { name: '••••••••' }).fill('E2e-First-Password-1');
  await page.getByRole('button', { name: 'Zaloguj się' }).click();
  await expect(page.getByRole('heading', { name: 'Witaj, Fiona!' })).toBeVisible();
});
