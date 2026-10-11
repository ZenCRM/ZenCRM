export const ADMIN = { email: 'admin@e2e.test', password: 'E2e-Admin-Password-1', firstName: 'Ada', lastName: 'Admin' };
export const EMPLOYEE = { email: 'employee@e2e.test', password: 'E2e-Employee-Password-1', firstName: 'Eryk', lastName: 'Employee' };
export const baseURL = process.env.BASE_URL || 'http://127.0.0.1:5101';
export const firstRunBaseURL = process.env.FIRST_RUN_BASE_URL || 'http://127.0.0.1:5102';
export const STORAGE = { admin: 'test-results/.auth/admin.json', employee: 'test-results/.auth/employee.json' };
