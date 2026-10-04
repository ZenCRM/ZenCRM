/* Settings component section; state is created for each CRM instance. */
window.ZenSettings = window.ZenSettings || {};
window.ZenSettings.email = function () { return {
        emailTemplateVariables() {
            const value = this.selectedEmailTemplate?.variables;
            const items = Array.isArray(value) ? value : (typeof value === 'string' ? value.split(',') : []);
            return [...new Set(items.filter(v => typeof v === 'string').map(v => v.trim()).filter(Boolean))];
        },
        async loadEmailTemplates() {
            try {
                const list = await this.api('/emails/templates');
                this.emailTemplates = list || [];
                if (!this.selectedEmailTemplate && this.emailTemplates.length > 0) {
                    this.selectEmailTemplate(this.emailTemplates[0]);
                } else if (this.selectedEmailTemplate) {
                    const found = this.emailTemplates.find(t => t.key === this.selectedEmailTemplate.key);
                    if (found) this.selectEmailTemplate(found);
                }
            } catch (e) {
                console.warn('Nie udało się załadować szablonów e-mail:', e.message);
            }
        },

        selectEmailTemplate(tpl) {
            this.selectedEmailTemplate = tpl;
            this.emailTemplateForm = {
                subject: tpl.subject || '',
                body_html: tpl.body_html || '',
            };
            this.emailTemplateSaved = '';
            this.emailTemplateError = '';
        },

        async saveEmailTemplate() {
            if (!this.selectedEmailTemplate) return;
            this.emailTemplateSaved = '';
            this.emailTemplateError = '';
            try {
                const updated = await this.api(`/emails/templates/${this.selectedEmailTemplate.key}`, {
                    method: 'PUT',
                    body: JSON.stringify(this.emailTemplateForm),
                });
                this.selectedEmailTemplate = updated;
                const idx = this.emailTemplates.findIndex(t => t.key === updated.key);
                if (idx !== -1) this.emailTemplates[idx] = updated;
                this.emailTemplateSaved = window.ZenI18n.t('Szablon zapisany pomyślnie');
                setTimeout(() => { this.emailTemplateSaved = ''; }, 3000);
            } catch (e) {
                this.emailTemplateError = window.ZenI18n.t('Błąd: ') + e.message;
            }
        },

        async resetEmailTemplate(key) {
            if (!confirm(window.ZenI18n.t('Przywrócić oryginalną treść tego szablonu?'))) return;
            this.emailTemplateSaved = '';
            this.emailTemplateError = '';
            try {
                const restored = await this.api(`/emails/templates/${key}/reset`, {
                    method: 'POST',
                });
                this.selectedEmailTemplate = restored;
                this.emailTemplateForm = {
                    subject: restored.subject || '',
                    body_html: restored.body_html || '',
                };
                const idx = this.emailTemplates.findIndex(t => t.key === restored.key);
                if (idx !== -1) this.emailTemplates[idx] = restored;
                this.emailTemplateSaved = window.ZenI18n.t('Przywrócono domyślny szablon');
                setTimeout(() => { this.emailTemplateSaved = ''; }, 3000);
            } catch (e) {
                this.emailTemplateError = window.ZenI18n.t('Błąd: ') + e.message;
            }
        },

        async loadSmtpSettings() {
            try {
                const data = await this.api('/emails/smtp');
                this.smtpForm = {
                    smtp_host: data.smtp_host || '',
                    smtp_port: data.smtp_port || 587,
                    smtp_user: data.smtp_user || '',
                    smtp_password: '',
                    smtp_from_email: data.smtp_from_email || '',
                    smtp_from_name: data.smtp_from_name || '',
                    smtp_encryption: data.smtp_encryption || 'tls',
                    smtp_enabled: !!data.smtp_enabled,
                    smtp_password_set: !!data.smtp_password_set,
                };
                if (!this.smtpTestEmail && this.user?.email) {
                    this.smtpTestEmail = this.user.email;
                }
            } catch (e) {
                console.warn('Nie udało się załadować konfiguracji SMTP:', e.message);
            }
        },

        async saveSmtpSettings() {
            this.smtpSaved = '';
            this.smtpError = '';
            try {
                const payload = { ...this.smtpForm };
                await this.api('/emails/smtp', {
                    method: 'PUT',
                    body: JSON.stringify(payload),
                });
                this.smtpSaved = window.ZenI18n.t('Konfiguracja SMTP zapisana');
                if (payload.smtp_password) {
                    this.smtpForm.smtp_password_set = true;
                    this.smtpForm.smtp_password = '';
                }
                setTimeout(() => { this.smtpSaved = ''; }, 3000);
            } catch (e) {
                this.smtpError = window.ZenI18n.t('Błąd: ') + e.message;
            }
        },

        async testSmtpSettings() {
            if (!this.smtpTestEmail) {
                this.smtpTestResult = { ok: false, message: window.ZenI18n.t('Podaj adres e-mail do testu') };
                return;
            }
            this.smtpTestLoading = true;
            this.smtpTestResult = null;
            try {
                const payload = {
                    to_email: this.smtpTestEmail,
                    smtp_host: this.smtpForm.smtp_host,
                    smtp_port: this.smtpForm.smtp_port,
                    smtp_user: this.smtpForm.smtp_user,
                    smtp_password: this.smtpForm.smtp_password,
                    smtp_from_email: this.smtpForm.smtp_from_email,
                    smtp_from_name: this.smtpForm.smtp_from_name,
                    smtp_encryption: this.smtpForm.smtp_encryption,
                };
                const res = await this.api('/emails/smtp/test', {
                    method: 'POST',
                    body: JSON.stringify(payload),
                });
                this.smtpTestResult = { ok: true, message: res.message || window.ZenI18n.t('Test powiódł się! Sprawdź skrzynkę odbiorczą.') };
            } catch (e) {
                this.smtpTestResult = { ok: false, message: e.message || window.ZenI18n.t('Błąd połączenia z serwerem SMTP') };
            } finally {
                this.smtpTestLoading = false;
            }
        },

        getRenderedEmailPreview() {
            if (!this.selectedEmailTemplate) {
                return { subject: '', html: '' };
            }
            const compName = this.settingsForm?.company_name || this.settingsForm?.brand_name || 'ZenCRM Demo';
            const compEmail = this.settingsForm?.company_email || 'kontakt@twojadomena.pl';
            const rawLogo = this.settingsForm?.brand_logo_light || this.settingsForm?.helpdesk_logo || '/logo.png';
            const fullLogoUrl = rawLogo.startsWith('http') ? rawLogo : ((this.settingsForm?.crm_base_url || window.location.origin) + rawLogo);
            const logoTag = `<img src="${fullLogoUrl}" alt="${compName}" style="max-height: 46px; max-width: 220px; object-fit: contain; display: inline-block;" />`;
            const logoHeader = `<div style="text-align: left; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #e5e7eb;">${logoTag}</div>`;

            const sampleContext = {
                company_name: compName,
                company_email: compEmail,
                company_logo: logoTag,
                company_logo_url: fullLogoUrl,
                client_name: window.ZenI18n.t('Jan Kowalski'),
                client_email: window.ZenI18n.t('jan.kowalski@example.com'),
                client_phone: '+48 600 700 800',
                employee_name: this.user?.first_name || 'Anna Nowak',
                agent_name: this.user?.first_name || 'Anna Nowak',
                user_name: window.ZenI18n.t('Jan Kowalski'),
                ticket_url: (this.settingsForm?.crm_base_url || window.location.origin) + (this.helpdeskForm?.helpdesk_path || '/pomoc') + '?ticket=demo',
                ticket_number: 'TK-1042',
                ticket_title: window.ZenI18n.t('Problem z logowaniem do panelu'),
                ticket_priority: window.ZenI18n.t('Wysoki'),
                ticket_category: window.ZenI18n.t('Pomoc techniczna'),
                ticket_description: window.ZenI18n.t('Dzień dobry, od wczoraj nie mogę zalogować się do panelu klienta. Proszę o weryfikację uprawnień.'),
                reply_content: window.ZenI18n.t('Dzień dobry Panie Janie,\n\nSprawdziliśmy konfigurację konta. Dostęp został odblokowany. Prosimy o ponowną próbę logowania.'),
                reply_date: '2026-09-28 11:30',
                task_title: window.ZenI18n.t('Wdrożenie raportowania dla klienta'),
                task_due_date: '2026-10-05 16:00',
                task_priority: window.ZenI18n.t('Wysoki'),
                task_description: window.ZenI18n.t('Przygotować konfigurację eksportu danych i zweryfikować uprawnienia w panelu klienta.'),
                portal_url: (this.settingsForm?.crm_base_url || window.location.origin) + '/portal.html',
                login_url: (this.settingsForm?.crm_base_url || window.location.origin),
                crm_ticket_url: (this.settingsForm?.crm_base_url || window.location.origin) + '/#tickets',
                crm_task_url: (this.settingsForm?.crm_base_url || window.location.origin) + '/#tasks',
                crm_client_url: (this.settingsForm?.crm_base_url || window.location.origin) + '/#clients/1',
                login_email: window.ZenI18n.t('jan.kowalski@example.com'),
                password: 'WymaganeHaslo123!',
                temp_password: 'Xy9#mK2$pL',
            };

            let subject = this.emailTemplateForm.subject || '';
            let body = this.emailTemplateForm.body_html || '';

            if (!body.includes('{{company_logo}}') && !body.includes('<img')) {
                const firstGt = body.indexOf('>');
                if (firstGt !== -1 && body.trim().startsWith('<div')) {
                    body = body.slice(0, firstGt + 1) + logoHeader + body.slice(firstGt + 1);
                } else {
                    body = logoHeader + body;
                }
            }

            for (const [k, v] of Object.entries(sampleContext)) {
                const ph = `{{${k}}}`;
                subject = subject.split(ph).join(String(v));
                body = body.split(ph).join(String(v));
            }

            const fullHtml = `<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f3f4f6; color: #1f2937; }
        .email-wrapper { max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e5e7eb; padding: 28px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }
    </style>
</head>
<body>
    <div class="email-wrapper">
        ${body}
    </div>
</body>
</html>`;
            return { subject, html: fullHtml };
        },

}; };
