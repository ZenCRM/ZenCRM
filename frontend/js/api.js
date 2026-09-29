/* ═══════════════════════════════════════════════
   ZenCRM – klient API (fetch + JWT)
   ═══════════════════════════════════════════════ */
window.ZenApi = {
    /**
     * Wykonuje żądanie HTTP do API.
     * @param {string} path      – ścieżka względem /api, np. "/clients"
     * @param {object} options   – opcje fetch (method, body, headers)
     * @param {string} token     – JWT access token
     * @param {function} onUnauthorized – callback przy 401
     * @returns {Promise<any>}
     */
    async request(path, options = {}, token = '', onUnauthorized = null) {
        const r = await fetch('/api' + path, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                'Accept-Language': window.ZenI18n.locale,
                'Authorization': 'Bearer ' + token,
                ...(options.headers || {}),
            },
        });

        if (r.status === 401) {
            if (onUnauthorized) onUnauthorized();
            throw new Error(window.ZenI18n.t('Sesja wygasła – zaloguj się ponownie'));
        }

        if (r.status !== 204 && !r.headers.get('Content-Type')?.toLowerCase().includes('application/json')) {
            throw new Error(window.ZenI18n.t('Serwer zwrócił stronę zamiast odpowiedzi API. Uruchom ponownie serwer aplikacji.'));
        }
        const data = r.status === 204 ? null : await r.json();
        if (!r.ok) throw new Error(window.ZenI18n.t((data && data.error) || window.ZenI18n.t('Błąd API')));
        return data;
    },

    /**
     * Logowanie – zwraca { access_token, refresh_token, user }.
     */
    async login(email, password) {
        const r = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept-Language': window.ZenI18n.locale },
            body: JSON.stringify({ email, password }),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(window.ZenI18n.t(data.error || window.ZenI18n.t('Błąd logowania')));
        return data;
    },

    /**
     * Zgłoszenie resetu hasła (zapomniałem hasła).
     */
    async forgotPassword(email) {
        const r = await fetch('/api/auth/forgot-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept-Language': window.ZenI18n.locale },
            body: JSON.stringify({ email }),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(window.ZenI18n.t(data.error || window.ZenI18n.t('Błąd żądania')));
        return data;
    },

    /**
     * Sprawdza status konfiguracji początkowej.
     */
    async getSetupStatus() {
        const r = await fetch('/api/auth/setup-status', {
            headers: { 'Accept-Language': window.ZenI18n.locale }
        });
        return await r.json();
    },

    /**
     * Tworzy pierwsze konto administratora.
     */
    async setupAdmin(payload) {
        const r = await fetch('/api/auth/setup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Accept-Language': window.ZenI18n.locale },
            body: JSON.stringify(payload),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(window.ZenI18n.t(data.error || window.ZenI18n.t('Błąd żądania')));
        return data;
    },
};
