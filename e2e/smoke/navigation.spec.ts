import { test, expect } from '../fixtures';

// Top-level links verified in the running app; grouped entries are buttons that expand.
const LINKS = ['Dashboard', 'Klienci', 'Leady', 'Kontakty', 'Projekty', 'Zadania', 'Kalendarz',
  'Telefonia & SMS', 'Pracownicy', 'Powiadomienia', 'Ustawienia', 'Archiwum'];
const GROUPS = ['Poczta e-mail', 'Usługi', 'Dokumenty', 'Tickety', 'Portal użytkownika'];

test('every menu module renders without browser errors', async ({ adminPage: page }) => {
  await page.goto('/#dashboard');
  const nav = page.getByRole('navigation');
  for (const name of LINKS) {
    const link = nav.getByRole('link', { name, exact: true });
    if (!(await link.isVisible())) await nav.getByRole('button', { name: 'CRM' }).click();
    await link.click();
    await expect(page.locator('main')).toBeVisible();
  }
  for (const group of GROUPS) {
    await nav.getByRole('button', { name: group }).click();
    const children = nav.getByRole('link').filter({ visible: true });
    await children.last().click();
    await expect(page.locator('main')).toBeVisible();
  }
});
