import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { ADMIN, EMPLOYEE, STORAGE, baseURL } from './support/env';
import { ApiClient } from './support/api';

async function postJson(path: string, body: unknown) {
  const response = await fetch(`${baseURL}/api${path}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status} ${await response.text()}`);
  return response.json();
}

// The SPA reads the session from localStorage keys 'token' and 'user', and the locale from 'zen-locale'.
function saveSession(path: string, login: { access_token: string; user: unknown }) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, JSON.stringify({
    cookies: [],
    origins: [{
      origin: new URL(baseURL).origin,
      localStorage: [
        { name: 'token', value: login.access_token },
        { name: 'user', value: JSON.stringify(login.user) },
        { name: 'zen-locale', value: 'pl' },
      ],
    }],
  }));
}

export default async function globalSetup() {
  const status = await (await fetch(`${baseURL}/api/auth/setup-status`)).json();
  if (!status.needs_setup) throw new Error(`${baseURL} is not a fresh instance; E2E needs an empty database`);

  const admin = await postJson('/auth/setup', {
    email: ADMIN.email, password: ADMIN.password, first_name: ADMIN.firstName, last_name: ADMIN.lastName,
  });
  saveSession(STORAGE.admin, admin);
  // Seed default settings once; concurrent first requests race (see findings: settings seeding race).
  await fetch(`${baseURL}/api/settings/ui`, { headers: { Authorization: `Bearer ${admin.access_token}` } });

  const api = new ApiClient(baseURL, admin.access_token);
  await api.post('/auth/register', {
    email: EMPLOYEE.email, password: EMPLOYEE.password, first_name: EMPLOYEE.firstName, last_name: EMPLOYEE.lastName,
  });
  saveSession(STORAGE.employee, await postJson('/auth/login', { email: EMPLOYEE.email, password: EMPLOYEE.password }));
}
