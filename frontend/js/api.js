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
                'Authorization': 'Bearer ' + token,
                ...(options.headers || {}),
            },
        });

        if (r.status === 401) {
            if (onUnauthorized) onUnauthorized();
            throw new Error(window.ZenI18n.t('Sesja wygasła – zaloguj się ponownie'));
        }

        const data = r.status === 204 ? null : await r.json();
        if (!r.ok) throw new Error(window.ZenI18n.t((data && data.error) || 'Błąd API'));
        return data;
    },

    /**
     * Logowanie – zwraca { access_token, refresh_token, user }.
     */
    async login(email, password) {
        const r = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(window.ZenI18n.t(data.error || 'Błąd logowania'));
        return data;
    },

    /**
     * Zgłoszenie resetu hasła (zapomniałem hasła).
     */
    async forgotPassword(email) {
        const r = await fetch('/api/auth/forgot-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email }),
        });
        const data = await r.json();
        if (!r.ok) throw new Error(window.ZenI18n.t(data.error || 'Błąd żądania'));
        return data;
    },
};
