export class ApiClient {
  constructor(private readonly baseURL: string, readonly token: string) {}

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
