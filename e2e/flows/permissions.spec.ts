import { test, expect } from '../fixtures';

test('employee does not see admin settings', async ({ employeePage: page }) => {
  await page.goto('/#dashboard');
  const nav = page.getByRole('navigation');
  await expect(nav.getByRole('link', { name: 'Dashboard', exact: true })).toBeVisible();
  await expect(nav.getByRole('link', { name: 'Ustawienia', exact: true })).toHaveCount(0);
  await expect(nav.getByRole('link', { name: 'Pracownicy', exact: true })).toHaveCount(0);
});

test('employee cannot call admin API', async ({ employeePage: page }) => {
  await page.goto('/#dashboard');
  const status = await page.evaluate(async () => {
    const response = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + localStorage.getItem('token') },
      body: JSON.stringify({ email: 'intruder@e2e.test', password: 'E2e-Password-123' }),
    });
    return response.status;
  });
  expect(status).toBe(403);
});
