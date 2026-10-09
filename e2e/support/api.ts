export class ApiClient {
  constructor(private readonly baseURL: string, readonly token: string) {}

  static async login(baseURL: string, email: string, password: string): Promise<ApiClient> {
    const response = await fetch(`${baseURL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) throw new Error(`login ${email}: HTTP ${response.status}`);
    const body = await response.json();
    return new ApiClient(baseURL, body.access_token);
  }

  get<T>(path: string): Promise<T> { return this.send<T>('GET', path); }
  post<T>(path: string, body: unknown): Promise<T> { return this.send<T>('POST', path, body); }
  put<T>(path: string, body: unknown): Promise<T> { return this.send<T>('PUT', path, body); }

  private async send<T>(method: string, path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${this.baseURL}/api${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${this.token}` },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!response.ok) throw new Error(`${method} ${path}: HTTP ${response.status} ${await response.text()}`);
    return (response.status === 204 ? null : await response.json()) as T;
  }
}
