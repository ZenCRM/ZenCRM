import { test, expect } from '../fixtures';

// Top-level links verified in the running app; grouped entries are buttons that expand their own child list.
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
    await expect(link).toHaveAttribute('aria-current', 'page');
  }

  for (const group of GROUPS) {
    const button = nav.getByRole('button', { name: group });
    // The group's children are rendered in the innermost wrapper that also holds its toggle button.
    const wrapper = nav.locator('div.space-y-1').filter({ has: page.getByRole('button', { name: group }) }).last();
    const children = wrapper.getByRole('link');
    if (!(await children.first().isVisible())) await button.click();
    const names = await children.allInnerTexts();
    expect(names.length, `${group} has child modules`).toBeGreaterThan(0);
    for (const index of names.keys()) {
      if (!(await children.nth(index).isVisible())) await button.click();
      await children.nth(index).click();
      await expect(children.nth(index), `${group} → ${names[index].trim()}`).toHaveAttribute('aria-current', 'page');
    }
  }
});
