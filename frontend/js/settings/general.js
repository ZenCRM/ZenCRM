/* Settings component section; state is created for each CRM instance. */
window.ZenSettings = window.ZenSettings || {};
window.ZenSettings.general = function () { return {
        async loadSettings(publicOnly = false) {
            try {
                if (publicOnly) {
                    // publiczny endpoint zwraca dict {key: value}
                    const data = await this.api(this.token ? '/settings/ui' : '/settings/public');
                    this.settingsForm = { ...data };
                    if (typeof data.needs_setup !== 'undefined') {
                        this.needsSetup = !!data.needs_setup;
                    }
                } else {
                    const items = await this.api('/settings/full');
                    const obj = {};
                    for (const it of items) obj[it.key] = it.value;
                    this.settingsForm = obj;
                }
                try { this.customLeadStages = JSON.parse(this.settingsForm.lead_stages || 'null'); } catch (_) { this.customLeadStages = null; }
                try { const stages = JSON.parse(this.settingsForm.task_stages || 'null'); if (Array.isArray(stages) && stages.length >= 2) this.taskStatusStages = stages; } catch (_) {}
                try {
                    let mp = this.settingsForm.menu_permissions;
                    if (typeof mp === 'string') mp = JSON.parse(mp);
                    this.menuPermissionsState = (mp && typeof mp === 'object') ? mp : {};
                } catch (_) {
                    this.menuPermissionsState = {};
                }
                try {
                    let ls = this.settingsForm.lead_sources;
                    if (typeof ls === 'string') ls = JSON.parse(ls);
                    if (Array.isArray(ls) && ls.length > 0) {
                        this.leadSources = ls;
                    }
                } catch (_) {}
                this.leadWebhookEnabled = this.settingsForm.lead_webhook_enabled === 'true' || this.settingsForm.lead_webhook_enabled === true;
                this.leadWebhookToken = this.settingsForm.lead_webhook_token || '';
                this.applyTheme();
                this.loadStandardRequiredFields();
                if (!publicOnly) {
                    this.loadCustomFieldDefs();
                    this.loadHelpdeskSettings();
                    this.loadEmailTemplates();
                    this.loadSmtpSettings();
                }
            } catch (e) {
                console.warn(window.ZenI18n.t('Nie udalo sie zaladowac ustawien:'), e.message);
            }
        },

}; };
