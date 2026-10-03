/* Settings component section; state is created for each CRM instance. */
window.ZenSettings = window.ZenSettings || {};
window.ZenSettings.translations = function () { return {
        async loadReleases() {
            this.releaseLoading = true;
            this.releaseError = '';
            try { this.releaseInfo = await this.api('/updates/releases'); }
            catch (e) { this.releaseError = e.message; }
            finally { this.releaseLoading = false; }
        },

        async loadTranslations() {
            this.translationError = '';
            try {
                this.translationData = await this.api('/translations');
                window.ZenCustomI18n = this.translationData;
                sessionStorage.setItem('zen-i18n-catalog', JSON.stringify(this.translationData));
                this.selectTranslationLocale(this.translationLocale);
            } catch (e) { this.translationError = e.message; }
        },

        selectTranslationLocale(locale) {
            if (!this.translationData.languages[locale]) locale = 'pl';
            this.translationLocale = locale;
            this.translationSearch = '';
            this.translationLimit = 80;
            this.translationDraft = { ...(this.translationData.overrides[locale] || {}) };
            this.translationOriginal = { ...this.translationDraft };
            this.translationSaved = '';
        },

        translationBase(key) {
            const base = this.translationData.languages[this.translationLocale]?.base || 'pl';
            return (base !== this.translationLocale ? this.translationData.overrides[base]?.[key] : undefined) ?? window.ZenLocales[base]?.[key] ?? window.ZenLocales.pl?.[key] ?? key;
        },

        translationKeys() {
            const keys = [...new Set([...Object.keys(window.ZenLocales.pl || {}), ...Object.keys(window.ZenLocales.en || {})])];
            const query = this.translationSearch.trim().toLocaleLowerCase();
            return query ? keys.filter(key => key.toLocaleLowerCase().includes(query) || String(this.translationBase(key)).toLocaleLowerCase().includes(query) || String(this.translationDraft[key] || '').toLocaleLowerCase().includes(query)) : keys;
        },

        async createTranslationLanguage() {
            this.translationError = '';
            try {
                const code = this.newTranslationLanguage.code.trim().toLowerCase();
                this.translationData = await this.api('/translations/languages', {method:'POST', body:JSON.stringify(this.newTranslationLanguage)});
                window.ZenCustomI18n = this.translationData;
                sessionStorage.setItem('zen-i18n-catalog', JSON.stringify(this.translationData));
                this.newTranslationLanguage = {code:'',name:'',base_locale:'pl'};
                this.selectTranslationLocale(code);
            } catch (e) { this.translationError = e.message; }
        },

        async saveTranslations() {
            this.translationError = '';
            this.translationSaved = '';
            const entries = {};
            for (const key of new Set([...Object.keys(window.ZenLocales.pl || {}), ...Object.keys(window.ZenLocales.en || {})])) {
                const value = this.translationDraft[key] || '';
                if (value !== (this.translationOriginal[key] || '')) entries[key] = value;
            }
            if (!Object.keys(entries).length) return;
            try {
                this.translationData = await this.api(`/translations/${encodeURIComponent(this.translationLocale)}/entries`, {method:'PUT',body:JSON.stringify({entries})});
                window.ZenCustomI18n = this.translationData;
                sessionStorage.setItem('zen-i18n-catalog', JSON.stringify(this.translationData));
                this.selectTranslationLocale(this.translationLocale);
                this.translationSaved = window.ZenI18n.t('Tłumaczenia zapisane. Odśwież stronę, aby zobaczyć zmiany w całym interfejsie.');
            } catch (e) { this.translationError = e.message; }
        },

}; };
