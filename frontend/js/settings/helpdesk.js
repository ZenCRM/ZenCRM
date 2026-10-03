/* Settings component section; state is created for each CRM instance. */
window.ZenSettings = window.ZenSettings || {};
window.ZenSettings.helpdesk = function () { return {
        helpdeskForm: {
            helpdesk_enabled: true,
            helpdesk_path: '/pomoc',
            helpdesk_title: 'Centrum Pomocy',
            helpdesk_header_subtitle: 'Wsparcie i obsługa zgłoszeń',
            helpdesk_badge: 'Zgłoszenie serwisowe',
            helpdesk_heading: 'W czym możemy Ci pomóc?',
            helpdesk_description: 'Wypełnij poniższy formularz. Otrzymasz unikalny link do śledzenia statusu zgłoszenia oraz powiadomienie e-mail.',
            helpdesk_success_heading: 'Zgłoszenie zostało wysłane!',
            helpdesk_success_description: 'Wysłaliśmy potwierdzenie na Twój adres e-mail wraz z bezpośrednim linkiem do śledzenia statusu zgłoszenia.',
            helpdesk_footer_text: 'Obsługa klienta · Bezpieczny portal pomocy',
            helpdesk_logo: '',
            helpdesk_accent_color: '#018bfc',
            helpdesk_categories: [],
            helpdesk_auto_assign: true,
            helpdesk_auto_assign_target: 'team',
            helpdesk_default_team_id: '',
            helpdesk_default_user_id: '',
            helpdesk_webhook_enabled: true,
            helpdesk_webhook_token: '',
        },
        newHelpdeskCategory: { id: '', name: '' },

        async uploadHelpdeskLogo(event) {
            const file = event.target.files && event.target.files[0];
            if (!file) return;
            const fd = new FormData();
            fd.append('file', file);
            fd.append('variant', 'helpdesk');
            try {
                const r = await fetch('/api/settings/upload-logo', {
                    method: 'POST',
                    headers: { 'Authorization': 'Bearer ' + this.token, 'Accept-Language': window.ZenI18n.locale },
                    body: fd,
                });
                const data = await r.json();
                if (!r.ok) throw new Error(data.error || window.ZenI18n.t('Blad uploadu'));
                this.helpdeskForm.helpdesk_logo = data.url + '?t=' + Date.now();
                this.notify(window.ZenI18n.t('Zaktualizowano logo portalu pomocy'));
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            }
            event.target.value = '';
        },

        removeHelpdeskLogo() {
            this.helpdeskForm.helpdesk_logo = '';
        },

        async loadHelpdeskSettings() {
            try {
                const data = await this.api('/tickets/settings');
                this.helpdeskForm = {
                    ...this.helpdeskForm,
                    ...data,
                    helpdesk_default_team_id: data.helpdesk_default_team_id || '',
                    helpdesk_default_user_id: data.helpdesk_default_user_id || '',
                };
            } catch (e) {
                console.warn('Nie udało się załadować ustawień helpdesku:', e.message);
            }
        },

        async saveHelpdeskSettings() {
            this.settingsSaved = '';
            this.settingsError = '';
            try {
                const payload = {
                    ...this.helpdeskForm,
                    helpdesk_default_team_id: this.helpdeskForm.helpdesk_default_team_id ? Number(this.helpdeskForm.helpdesk_default_team_id) : null,
                    helpdesk_default_user_id: this.helpdeskForm.helpdesk_default_user_id ? Number(this.helpdeskForm.helpdesk_default_user_id) : null,
                };
                const updated = await this.api('/tickets/settings', {
                    method: 'PUT',
                    body: JSON.stringify(payload)
                });
                this.helpdeskForm = {
                    ...updated,
                    helpdesk_default_team_id: updated.helpdesk_default_team_id || '',
                    helpdesk_default_user_id: updated.helpdesk_default_user_id || '',
                };
                this.settingsSaved = window.ZenI18n.t('Ustawienia zapisane');
                setTimeout(() => { this.settingsSaved = ''; }, 2000);
            } catch (e) {
                this.settingsError = window.ZenI18n.t('Błąd: ') + e.message;
            }
        },

        addHelpdeskCategory() {
            const id = (this.newHelpdeskCategory.id || '').trim().toLowerCase().replace(/[^a-z0-9_-]/g, '');
            const name = (this.newHelpdeskCategory.name || '').trim();
            if (!id || !name) return;
            this.helpdeskForm.helpdesk_categories = this.helpdeskForm.helpdesk_categories || [];
            if (this.helpdeskForm.helpdesk_categories.some(c => c.id === id)) {
                this.notify(window.ZenI18n.t('Kategoria o tym identyfikatorze już istnieje'));
                return;
            }
            this.helpdeskForm.helpdesk_categories.push({ id, name });
            this.newHelpdeskCategory = { id: '', name: '' };
        },

        removeHelpdeskCategory(idx) {
            if (!this.helpdeskForm.helpdesk_categories) return;
            this.helpdeskForm.helpdesk_categories.splice(idx, 1);
        },

        async regenerateWebhookToken() {
            if (!confirm(window.ZenI18n.t('Wygenerować nowy token webhooka? Stary token przestanie działać.'))) return;
            const randHex = Array.from(crypto.getRandomValues(new Uint8Array(20))).map(b => b.toString(16).padStart(2, '0')).join('');
            this.helpdeskForm.helpdesk_webhook_token = randHex;
            await this.saveHelpdeskSettings();
        },

        copyWebhookUrl() {
            const url = `${window.location.origin}/api/tickets/webhook`;
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(url).then(() => this.notify(window.ZenI18n.t('Skopiowano URL webhooka')));
            } else {
                prompt(window.ZenI18n.t('Skopiuj URL:'), url);
            }
        },

        copyWebhookToken() {
            const tok = this.helpdeskForm.helpdesk_webhook_token;
            if (!tok) return;
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(tok).then(() => this.notify(window.ZenI18n.t('Skopiowano token webhooka')));
            } else {
                prompt(window.ZenI18n.t('Skopiuj token:'), tok);
            }
        },

}; };
