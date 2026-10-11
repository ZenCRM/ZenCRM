import { test, expect } from '../fixtures';

type Client = { id: number; name: string; city: string | null };

test('client can be created, edited, given a contact and a note, and archived', async ({ adminPage: page, api, uniqueName }) => {
  const name = uniqueName('Klient');
  const findClient = async () =>
    (await api.get<{ clients: Client[] }>(`/clients?search=${encodeURIComponent(name)}`)).clients[0];

  await page.goto('/#clients');
  await page.getByRole('button', { name: '+ Dodaj klienta' }).click();
  await expect(page.getByRole('heading', { name: 'Nowy klient' })).toBeVisible();
  await page.getByRole('textbox', { name: 'Nazwa', exact: true }).fill(name);
  await page.getByRole('textbox', { name: 'Email', exact: true }).fill('client@e2e.test');
  await page.getByRole('button', { name: 'Zapisz' }).click();
  await page.getByRole('textbox', { name: 'Szukaj klienta...' }).fill(name);
  const row = page.getByRole('row', { name: new RegExp(name) });
  await expect(row).toBeVisible();

  await row.getByRole('button', { name: 'Edytuj' }).click();
  await page.getByRole('textbox', { name: 'Miejscowość', exact: true }).fill('Gdańsk');
  await page.getByRole('button', { name: 'Zapisz' }).click();
  await expect.poll(async () => (await findClient()).city).toBe('Gdańsk');

  await row.getByRole('button', { name }).click();
  await page.getByRole('button', { name: 'Dodaj kontakt', exact: true }).click();
  await page.getByRole('textbox', { name: 'Imię', exact: true }).fill('Kamil');
  await page.getByRole('textbox', { name: 'Nazwisko', exact: true }).fill('Kontakt');
  await page.getByRole('button', { name: 'Zapisz' }).click();
  await expect(page.getByText('Kamil Kontakt').filter({ visible: true }).first()).toBeVisible();

  const note = uniqueName('Notatka');
  await page.getByRole('button', { name: 'Dodaj notatkę' }).click();
  await page.getByRole('textbox', { name: 'Treść notatki' }).fill(note);
  await page.getByRole('button', { name: 'Zapisz wpis' }).click();
  await expect(page.getByRole('article').filter({ hasText: note })).toBeVisible();
  await page.getByRole('button', { name: 'Zamknij wpis' }).click();

  await page.goto('/#clients');
  await page.getByRole('textbox', { name: 'Szukaj klienta...' }).fill(name);
  page.once('dialog', dialog => dialog.accept());
  await row.getByRole('button', { name: 'Usuń' }).click();
  await expect(row).toHaveCount(0);
  await page.goto('/#archive');
  await expect(page.getByRole('heading', { name: 'Archiwum' }).first()).toBeVisible();
  await expect(page.getByText(name, { exact: true }).filter({ visible: true }).first()).toBeVisible();
});
