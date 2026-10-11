import { test, expect } from '../fixtures';

// The public form allows 5 submissions per hour per IP, so this suite submits exactly once.
test('ticket submitted on the public helpdesk can be answered in the panel', async ({ page, adminPage, api, uniqueName }) => {
  const title = uniqueName('Ticket');
  await page.goto('/pomoc');
  await page.getByRole('textbox', { name: 'Twój adres e-mail *' }).fill('customer@e2e.test');
  await page.getByRole('combobox', { name: 'Kategoria zgłoszenia *' }).selectOption({ label: 'Pomoc techniczna' });
  await page.getByRole('textbox', { name: 'Temat zgłoszenia *' }).fill(title);
  await page.locator('#f-description').fill('Opis zgłoszenia z testu E2E.');
  await page.locator('#btn-submit').click();
  await expect(page.getByText('Zgłoszenie zostało wysłane!')).toBeVisible();

  await adminPage.goto('/#tickets');
  await adminPage.getByText(title).filter({ visible: true }).first().click();
  const reply = uniqueName('Odpowiedź');
  await adminPage.getByRole('textbox').filter({ visible: true }).last().fill(reply);
  await adminPage.getByRole('button', { name: /Wyślij|Odpowiedz/ }).filter({ visible: true }).first().click();
  await expect(adminPage.getByText(reply).filter({ visible: true }).first()).toBeVisible();

  const ticket = (await api.get<{ id: number; title: string }[]>('/tickets')).find(t => t.title === title)!;
  const detail = await api.get<{ messages: unknown[] }>(`/tickets/${ticket.id}`);
  expect(JSON.stringify(detail.messages)).toContain(reply);
});
