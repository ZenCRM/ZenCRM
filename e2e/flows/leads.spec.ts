import { test, expect } from '../fixtures';

type Lead = { id: number; stage: string; converted_to_client_id: number | null };

test('lead moves across the board and converts to a client', async ({ adminPage: page, api, uniqueName }) => {
  const title = uniqueName('Lead');
  const lead = await api.post<Lead>('/leads', { title });
  const { stages } = await api.get<{ stages: { id: string }[] }>('/leads/board-settings');
  const target = stages.find(stage => stage.id !== lead.stage && stage.id !== 'won' && stage.id !== 'lost')!.id;

  await page.goto('/#leads');
  const card = page.locator('.zen-lead-card', { hasText: title });
  const column = page.locator(`.kanban-col-new[data-stage="${target}"]`);
  await card.dragTo(column);
  await expect(column.locator('.zen-lead-card', { hasText: title })).toBeVisible();
  await expect.poll(async () => (await api.get<Lead>(`/leads/${lead.id}`)).stage).toBe(target);

  // A click right after a drop can be swallowed by the drag handlers; open the record by its address.
  await page.goto(`/#lead/${lead.id}`);
  await page.reload();
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: 'Konwertuj na klienta' }).click();
  await expect.poll(async () => (await api.get<Lead>(`/leads/${lead.id}`)).converted_to_client_id).not.toBeNull();
});
