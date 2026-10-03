/* Settings component section; state is created for each CRM instance. */
window.ZenSettings = window.ZenSettings || {};
window.ZenSettings.navigation = function () { return {
        getMenuModuleConfig(id) {
            const current = this.menuPermissionsState[id];
            return {
                enabled: current?.enabled !== false,
                role: current?.role || 'all',
            };
        },
        setMenuModuleEnabled(id, enabled) {
            if (!this.menuPermissionsState[id]) {
                this.menuPermissionsState[id] = { enabled: true, role: 'all' };
            }
            this.menuPermissionsState[id].enabled = !!enabled;
            this.menuPermissionsState = { ...this.menuPermissionsState };
            this.settingsForm.menu_permissions = JSON.stringify(this.menuPermissionsState);
        },
        setMenuModuleRole(id, role) {
            if (!this.menuPermissionsState[id]) {
                this.menuPermissionsState[id] = { enabled: true, role: 'all' };
            }
            this.menuPermissionsState[id].role = role;
            this.menuPermissionsState = { ...this.menuPermissionsState };
            this.settingsForm.menu_permissions = JSON.stringify(this.menuPermissionsState);
        },
        async saveMenuSettings() {
            this.savingMenuSettings = true;
            this.menuSettingsSaved = false;
            try {
                const jsonStr = JSON.stringify(this.menuPermissionsState);
                const updated = await this.api('/settings', {
                    method: 'PUT',
                    body: JSON.stringify({ menu_permissions: jsonStr }),
                });
                this.settingsForm = { ...this.settingsForm, ...updated, menu_permissions: jsonStr };
                this.menuSettingsSaved = true;
                this.notify(window.ZenI18n.t('Ustawienia menu zostały zapisane'));
                setTimeout(() => { this.menuSettingsSaved = false; }, 3000);
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            } finally {
                this.savingMenuSettings = false;
            }
        },

        addLeadSource() {
            const name = (this.newLeadSourceName || '').trim();
            if (!name) return;
            if (this.leadSources.includes(name)) {
                this.notify(window.ZenI18n.t('Takie źródło już istnieje'));
                return;
            }
            this.leadSources.push(name);
            this.newLeadSourceName = '';
            this.settingsForm.lead_sources = JSON.stringify(this.leadSources);
        },
        startEditLeadSource(index) {
            this.editingLeadSourceIndex = index;
            this.editingLeadSourceName = this.leadSources[index] || '';
        },
        saveEditLeadSource() {
            if (this.editingLeadSourceIndex === null) return;
            const name = (this.editingLeadSourceName || '').trim();
            if (!name) return;
            this.leadSources[this.editingLeadSourceIndex] = name;
            this.editingLeadSourceIndex = null;
            this.editingLeadSourceName = '';
            this.settingsForm.lead_sources = JSON.stringify(this.leadSources);
        },
        cancelEditLeadSource() {
            this.editingLeadSourceIndex = null;
            this.editingLeadSourceName = '';
        },
        deleteLeadSource(index) {
            if (!confirm(window.ZenI18n.t('Czy na pewno chcesz usunąć to źródło?'))) return;
            this.leadSources.splice(index, 1);
            if (this.editingLeadSourceIndex === index) {
                this.cancelEditLeadSource();
            }
            this.settingsForm.lead_sources = JSON.stringify(this.leadSources);
        },
        async generateNewLeadWebhookToken() {
            if (!confirm(window.ZenI18n.t('Wygenerować nowy token dla webhooka? Stary token przestanie działać!'))) return;
            try {
                const res = await this.api('/settings/lead-webhook/generate-token', { method: 'POST' });
                if (res?.token) {
                    this.leadWebhookToken = res.token;
                    this.settingsForm.lead_webhook_token = res.token;
                    this.notify(window.ZenI18n.t('Wygenerowano nowy token webhooka'));
                }
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            }
        },
        async copyLeadWebhookUrl() {
            const url = window.location.origin + '/api/leads/webhook';
            try {
                await navigator.clipboard.writeText(url);
                this.notify(window.ZenI18n.t('Skopiowano URL webhooka'));
            } catch (_) {
                this.notify(url);
            }
        },
        async copyLeadWebhookToken() {
            if (!this.leadWebhookToken) return;
            try {
                await navigator.clipboard.writeText(this.leadWebhookToken);
                this.notify(window.ZenI18n.t('Skopiowano token'));
            } catch (_) {
                this.notify(this.leadWebhookToken);
            }
        },
        async saveLeadSettings() {
            this.savingLeadSettings = true;
            this.leadSettingsSaved = false;
            try {
                const sourcesJson = JSON.stringify(this.leadSources);
                const updated = await this.api('/settings', {
                    method: 'PUT',
                    body: JSON.stringify({
                        lead_sources: sourcesJson,
                        lead_webhook_enabled: this.leadWebhookEnabled ? 'true' : 'false',
                    }),
                });
                this.settingsForm = {
                    ...this.settingsForm,
                    ...updated,
                    lead_sources: sourcesJson,
                    lead_webhook_enabled: this.leadWebhookEnabled ? 'true' : 'false',
                };
                this.leadSettingsSaved = true;
                this.notify(window.ZenI18n.t('Ustawienia leadów zostały zapisane'));
                setTimeout(() => { this.leadSettingsSaved = false; }, 3000);
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            } finally {
                this.savingLeadSettings = false;
            }
        },

}; };
