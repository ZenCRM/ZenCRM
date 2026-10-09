import { test, expect } from '../fixtures';

function today() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

test('task and meeting created today appear in the calendar', async ({ adminPage: page, api, uniqueName }) => {
  const day = today();
  const taskTitle = uniqueName('Zadanie');
  const meetingTitle = uniqueName('Spotkanie');

  await page.goto('/#tasks');
  await page.getByRole('button', { name: '+ Dodaj zadanie' }).click();
  await page.getByRole('textbox', { name: 'Tytuł', exact: true }).fill(taskTitle);
  await page.getByRole('textbox', { name: 'Termin', exact: true }).fill(`${day}T12:00`);
  await page.getByRole('button', { name: 'Dodaj zadanie', exact: true }).click();
  await expect(page.getByText(taskTitle).filter({ visible: true }).first()).toBeVisible();

  await api.post('/meetings', { title: meetingTitle, start_time: `${day}T15:00:00`, end_time: `${day}T16:00:00` });

  await page.reload();
  await page.getByRole('navigation').getByRole('link', { name: 'Kalendarz', exact: true }).click();
  await expect(page.getByText(taskTitle).filter({ visible: true }).first()).toBeVisible();
  await expect(page.getByText(meetingTitle).filter({ visible: true }).first()).toBeVisible();
});
