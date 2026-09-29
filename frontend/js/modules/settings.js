window.ZenModules = window.ZenModules || {};
window.ZenModules.settings = function () { return {
        permissionCatalog: [],
        managedRoles: [],
        roleRules: {},
        teamRules: {},
        permissionSubject: 'role:manager',
        permissionError: '',
        permissionSaved: '',
        newRoleName: '',
        roleNameDraft: '',
        effectivePermissions: {},
        // Menu settings
        menuModulesList: [
            { id: 'dashboard', label: 'Dashboard', group: 'Główne' },
            { id: 'clients', label: 'CRM - Klienci', group: 'CRM' },
            { id: 'leads', label: 'CRM - Leady', group: 'CRM' },
            { id: 'contacts', label: 'CRM - Kontakty', group: 'CRM' },
            { id: 'projects', label: 'Projekty', group: 'Główne' },
            { id: 'tasks', label: 'Zadania', group: 'Główne' },
            { id: 'meetings', label: 'Kalendarz', group: 'Główne' },
            { id: 'services', label: 'Usługi', group: 'Usługi' },
            { id: 'serviceCatalog', label: 'Katalog usług', group: 'Usługi' },
            { id: 'offers', label: 'Oferty', group: 'Dokumenty' },
            { id: 'documents', label: 'Dokumenty', group: 'Dokumenty' },
            { id: 'templates', label: 'Szablony', group: 'Dokumenty' },
            { id: 'tickets', label: 'Lista ticketów', group: 'Tickety' },
            { id: 'ticketSettings', label: 'Ustawienia ticketów', group: 'Tickety' },
            { id: 'sms', label: 'Telefonia & SMS', group: 'Komunikacja' },
            { id: 'archive', label: 'Archiwum', group: 'System' },
        ],
        menuPermissionsState: {},
        savingMenuSettings: false,
        menuSettingsSaved: false,

        // Lead settings
        leadSources: ['Strona WWW', 'Polecenie', 'Telefon', 'Social Media', 'Kampania Google', 'Inne'],
        newLeadSourceName: '',
        editingLeadSourceIndex: null,
        editingLeadSourceName: '',
        leadWebhookEnabled: false,
        leadWebhookToken: '',
        savingLeadSettings: false,
        leadSettingsSaved: false,
        can(permission) {
            return this.user?.role === 'admin' || this.effectivePermissions[permission] !== false;
        },
        canRecordAction(view, action) {
            if (view === 'users' || view === 'teams') return this.user?.role === 'admin';
            const module = view === 'serviceCatalog' ? 'service_catalog' : view;
            return this.can(`${module}.${action}`);
        },
        async loadMyPermissions() {
            if (!this.token) return;
            try { this.effectivePermissions = await this.api('/permissions/me'); }
            catch (e) { console.warn('Nie pobrano uprawnień:', e.message); }
        },
        async loadPermissions() {
            this.permissionError = '';
            try {
                const data = await this.api('/permissions');
                this.permissionCatalog = data.permissions || [];
                this.managedRoles = data.roles || [];
                this.roleRules = data.role_rules || {};
                this.teamRules = data.team_rules || {};
                if (!this.teams.length) await this.loadTeams();
            } catch (e) { this.permissionError = e.message; }
        },
        permissionRule(key) {
            const [kind, id] = this.permissionSubject.split(':');
            const rules = kind === 'role' ? this.roleRules[id] : this.teamRules[id];
            return rules?.[key] === true ? 'allow' : rules?.[key] === false ? 'deny' : 'inherit';
        },
        setPermissionRule(key, value) {
            const [kind, id] = this.permissionSubject.split(':');
            const source = kind === 'role' ? this.roleRules : this.teamRules;
            if (!source[id]) source[id] = {};
            if (value === 'inherit') delete source[id][key];
            else source[id][key] = value === 'allow';
        },
        async savePermissions() {
            const [kind, id] = this.permissionSubject.split(':');
            const rules = kind === 'role' ? this.roleRules[id] || {} : this.teamRules[id] || {};
            this.permissionError = '';
            this.permissionSaved = '';
            try {
                await this.api(kind === 'role' ? `/permissions/roles/${id}/rules` : `/permissions/teams/${id}/rules`, {
                    method: 'PUT', body: JSON.stringify({ rules: Object.fromEntries(this.permissionCatalog.map(p => [p.key, Object.prototype.hasOwnProperty.call(rules, p.key) ? rules[p.key] : null])) }),
                });
                this.permissionSaved = window.ZenI18n.t('Uprawnienia zapisane');
                await this.loadMyPermissions();
            } catch (e) { this.permissionError = e.message; }
        },
        async createManagedRole() {
            this.permissionError = '';
            try {
                const role = await this.api('/permissions/roles', { method: 'POST', body: JSON.stringify({ name: this.newRoleName }) });
                this.newRoleName = '';
                await this.loadPermissions();
                this.permissionSubject = `role:${role.key}`;
                this.roleNameDraft = role.name;
            } catch (e) { this.permissionError = e.message; }
        },
        async renameManagedRole() {
            const [kind, id] = this.permissionSubject.split(':');
            if (kind !== 'role') return;
            this.permissionError = '';
            try {
                await this.api(`/permissions/roles/${id}`, { method: 'PUT', body: JSON.stringify({ name: this.roleNameDraft }) });
                await this.loadPermissions();
                this.permissionSaved = window.ZenI18n.t('Nazwa roli zapisana');
            } catch (e) { this.permissionError = e.message; }
        },
        async deleteManagedRole() {
            const [kind, id] = this.permissionSubject.split(':');
            if (kind !== 'role' || ['admin', 'manager', 'employee'].includes(id)) return;
            if (!confirm(window.ZenI18n.t('Usunąć tę rolę?'))) return;
            try {
                await this.api(`/permissions/roles/${id}`, { method: 'DELETE' });
                this.permissionSubject = 'role:manager';
                await this.loadPermissions();
            } catch (e) { this.permissionError = e.message; }
        },
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

        async saveSettings() {
            if (this.settingsTab === 'helpdesk') {
                await this.saveHelpdeskSettings();
                return;
            }
            this.settingsSaved = '';
            this.settingsError = '';
            try {
                const updated = await this.api('/settings', {
                    method: 'PUT',
                    body: JSON.stringify(this.settingsForm),
                });
                this.settingsForm = { ...updated };
                this.applyTheme();
                this.settingsSaved = window.ZenI18n.t('Ustawienia zapisane');
                setTimeout(() => { this.settingsSaved = ''; }, 2000);
            } catch (e) {
                this.settingsError = window.ZenI18n.t('Błąd: ') + e.message;
            }
        },

        async resetSettings() {
            if (!confirm(window.ZenI18n.t('Przywrócić domyślne ustawienia?'))) return;
            try {
                await this.api('/settings/reset', { method: 'POST' });
                await this.loadSettings();
            } catch (e) { this.notify(e.message); }
        },

        async uploadBrandFile(event, variant) {
            const file = event.target.files && event.target.files[0];
            if (!file) return;
            const fd = new FormData();
            fd.append('file', file);
            fd.append('variant', variant);
            try {
                const r = await fetch('/api/settings/upload-logo', {
                    method: 'POST',
                    headers: { 'Authorization': 'Bearer ' + this.token, 'Accept-Language': window.ZenI18n.locale },
                    body: fd,
                });
                const data = await r.json();
                if (!r.ok) throw new Error(data.error || window.ZenI18n.t('Blad uploadu'));
                const keyMap = { light: 'brand_logo_light', dark: 'brand_logo_dark', favicon: 'brand_favicon' };
                this.settingsForm[keyMap[variant]] = data.url + '?t=' + Date.now();
                this.applyTheme();
            } catch (e) { this.notify(window.ZenI18n.t('Błąd: ') + e.message); }
            event.target.value = '';
        },

        applyTheme() {
            const s = this.settingsForm || {};

            // Kolor glowny jako CSS variable
            const primary = s.brand_color_primary || '#007fce';
            const secondary = s.brand_color_secondary || '#009fb9';
            document.documentElement.style.setProperty('--brand-primary', primary);
            document.documentElement.style.setProperty('--brand-secondary', secondary);

            // Zamien kolor w przyciskach bg-brand-600 (inline override)
            let styleTag = document.getElementById('zen-theme-override');
            if (!styleTag) {
                styleTag = document.createElement('style');
                styleTag.id = 'zen-theme-override';
                document.head.appendChild(styleTag);
            }
            styleTag.textContent = `
                .bg-brand-600 { background-color: ${primary} !important; }
                .bg-brand-700 { background-color: ${this._darken(primary, 15)} !important; }
                .hover\\:bg-brand-700:hover { background-color: ${this._darken(primary, 15)} !important; }
                .text-brand-600 { color: ${primary} !important; }
                .text-brand-700 { color: ${this._darken(primary, 20)} !important; }
                .bg-brand-100 { background-color: ${this._lighten(primary, 85)} !important; }
                .bg-brand-50 { background-color: ${this._lighten(primary, 93)} !important; }
                .border-brand-200 { border-color: ${this._lighten(primary, 75)} !important; }
                .focus\\:ring-brand-500:focus { --tw-ring-color: ${primary} !important; }

            `;

            const lightLogo = s.brand_logo_light || '/logo.png';
            const darkLogo = s.brand_logo_dark || lightLogo;

            // Logo na ekranie logowania
            const loginLogo = document.getElementById('zen-login-logo');
            if (loginLogo) {
                loginLogo.style.display = (s.login_show_logo === 'false') ? 'none' : '';
                loginLogo.src = this.darkMode ? darkLogo : lightLogo;
            }

            // Logo w sidebarze
            const sidebarLogo = document.getElementById('zen-sidebar-logo');
            if (sidebarLogo) {
                sidebarLogo.src = this.darkMode ? darkLogo : lightLogo;
                if (s.brand_logo_size) {
                    sidebarLogo.style.height = `${s.brand_logo_size}px`;
                    sidebarLogo.style.maxHeight = `${s.brand_logo_size}px`;
                }
            }

            // Favicon
            const favicon = document.querySelector('link[rel="icon"]');
            if (favicon) {
                favicon.href = s.brand_favicon || '/icon.png';
            }
        },

        previewBranding() {
            if (this.settingsForm.brand_name) {
                document.title = this.settingsForm.brand_name;
            }
            this.applyTheme();
        },

        _darken(hex, percent) {
            return this._shift(hex, -percent);
        },
        _lighten(hex, percent) {
            hex = (hex || '#007fce').replace('#', '');
            if (hex.length === 3) hex = hex.split('').map(c => c + c).join('');
            const num = parseInt(hex, 16);
            let r = num >> 16;
            let g = (num >> 8) & 0x00FF;
            let b = num & 0x0000FF;
            const factor = Math.max(0, Math.min(100, percent)) / 100;
            // Mix channels towards 255 (white) to produce clean tint without hue shifting into neon colors like #74feff
            r = Math.round(r + (255 - r) * factor);
            g = Math.round(g + (255 - g) * factor);
            b = Math.round(b + (255 - b) * factor);
            return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0');
        },
        _shift(hex, percent) {
            hex = (hex || '#007fce').replace('#', '');
            if (hex.length === 3) hex = hex.split('').map(c => c + c).join('');
            const num = parseInt(hex, 16);
            let r = (num >> 16) + Math.round(2.55 * percent);
            let g = ((num >> 8) & 0x00FF) + Math.round(2.55 * percent);
            let b = (num & 0x0000FF) + Math.round(2.55 * percent);
            r = Math.max(0, Math.min(255, r));
            g = Math.max(0, Math.min(255, g));
            b = Math.max(0, Math.min(255, b));
            return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0');
        },

        // ═══════════════════════════════════════════════════════════
        // POLA WŁASNE (CUSTOM FIELDS)
        // ═══════════════════════════════════════════════════════════
        customFieldDefs: [],
        customFieldsFilter: '',
        newCustomField: { entity: 'clients', label: '', kind: 'text', required: false },
        editingCustomField: null,
        customValuesEntity: 'clients',
        customValuesRecords: [],
        customValuesSelectedRecord: '',
        customValuesRecordData: {},
        customValuesFields: [],
        customValuesSaving: false,
        customValuesSuccess: '',
        customValuesError: '',
        customEntityLabels: {
            clients: window.ZenI18n.t('Klienci'),
            leads: window.ZenI18n.t('Leady'),
            projects: window.ZenI18n.t('Projekty'),
            contacts: window.ZenI18n.t('Kontakty'),
            tasks: window.ZenI18n.t('Zadania'),
            meetings: window.ZenI18n.t('Spotkania'),
            services: window.ZenI18n.t('Usługi'),
            service_catalog: window.ZenI18n.t('Katalog usług'),
            documents: window.ZenI18n.t('Dokumenty'),
            offers: window.ZenI18n.t('Oferty'),
            templates: window.ZenI18n.t('Szablony'),
            users: window.ZenI18n.t('Pracownicy')
        },
        customKindLabels: {
            text: window.ZenI18n.t('Tekst krótki'),
            textarea: window.ZenI18n.t('Długi tekst'),
            number: window.ZenI18n.t('Liczba'),
            date: window.ZenI18n.t('Data'),
            boolean: window.ZenI18n.t('Tak / Nie')
        },

        // ═══════════════════════════════════════════════════════════
        // POLA STANDARDOWE & WYMAGANIA
        // ═══════════════════════════════════════════════════════════
        standardRequiredEntities: [
            { key: 'clients', label: window.ZenI18n.t('Klienci') },
            { key: 'leads', label: window.ZenI18n.t('Leady') },
            { key: 'contacts', label: window.ZenI18n.t('Osoby kontaktowe') },
            { key: 'tasks', label: window.ZenI18n.t('Zadania') },
        ],
        standardRequiredFields: {
            clients: ['name'],
            leads: ['title'],
            contacts: ['first_name'],
            tasks: ['title'],
        },
        standardFieldLabels: {},
        standardFieldDefinitions: {
            clients: [
                { key: 'name', label: window.ZenI18n.t('Nazwa klienta'), type: 'text', systemRequired: true },
                { key: 'email', label: window.ZenI18n.t('Adres e-mail'), type: 'email' },
                { key: 'phone', label: window.ZenI18n.t('Numer telefonu'), type: 'text' },
                { key: 'company', label: window.ZenI18n.t('Nazwa firmy'), type: 'text' },
                { key: 'address', label: window.ZenI18n.t('Adres siedziby'), type: 'textarea' },
                { key: 'status', label: window.ZenI18n.t('Status klienta'), type: 'select' },
                { key: 'notes', label: window.ZenI18n.t('Dodatkowe informacje'), type: 'textarea' },
            ],
            leads: [
                { key: 'title', label: window.ZenI18n.t('Tytuł szansy / leadu'), type: 'text', systemRequired: true },
                { key: 'client_id', label: window.ZenI18n.t('Klient powiązany'), type: 'client-select' },
                { key: 'value', label: window.ZenI18n.t('Wartość szansy (zł)'), type: 'number' },
                { key: 'stage', label: window.ZenI18n.t('Etap sprzedaży'), type: 'select' },
                { key: 'source', label: window.ZenI18n.t('Źródło pozyskania'), type: 'text' },
                { key: 'probability', label: window.ZenI18n.t('Prawdopodobieństwo (%)'), type: 'number' },
                { key: 'expected_close_date', label: window.ZenI18n.t('Przewidywane zamknięcie'), type: 'date' },
                { key: 'notes', label: window.ZenI18n.t('Notatki'), type: 'textarea' },
            ],
            contacts: [
                { key: 'first_name', label: window.ZenI18n.t('Imię'), type: 'text', systemRequired: true },
                { key: 'last_name', label: window.ZenI18n.t('Nazwisko'), type: 'text' },
                { key: 'is_primary', label: window.ZenI18n.t('Główna osoba kontaktowa'), type: 'checkbox' },
                { key: 'email', label: window.ZenI18n.t('Adres e-mail'), type: 'email' },
                { key: 'phone', label: window.ZenI18n.t('Numer telefonu'), type: 'text' },
                { key: 'position', label: window.ZenI18n.t('Stanowisko / Rola'), type: 'text' },
                { key: 'client_id', label: window.ZenI18n.t('Przypisany klient'), type: 'client-select' },
                { key: 'notes', label: window.ZenI18n.t('Notatki o kontakcie'), type: 'textarea' },
            ],
            tasks: [
                { key: 'title', label: window.ZenI18n.t('Tytuł zadania'), type: 'text', systemRequired: true },
                { key: 'description', label: window.ZenI18n.t('Opis zadania'), type: 'textarea' },
                { key: 'status', label: window.ZenI18n.t('Status realizacji'), type: 'select' },
                { key: 'priority', label: window.ZenI18n.t('Priorytet'), type: 'select' },
                { key: 'due_date', label: window.ZenI18n.t('Termin wykonania'), type: 'datetime-local' },
                { key: 'client_id', label: window.ZenI18n.t('Powiązany klient'), type: 'client-select' },
                { key: 'project_id', label: window.ZenI18n.t('Powiązany projekt'), type: 'project-select' },
            ],
        },

        loadStandardRequiredFields() {
            try {
                if (this.settingsForm?.required_standard_fields) {
                    const parsed = JSON.parse(this.settingsForm.required_standard_fields);
                    if (parsed && typeof parsed === 'object') {
                        this.standardRequiredFields = { ...this.standardRequiredFields, ...parsed };
                    }
                }
            } catch (_) {}
            try {
                if (this.settingsForm?.standard_field_labels) {
                    const parsedLabels = JSON.parse(this.settingsForm.standard_field_labels);
                    if (parsedLabels && typeof parsedLabels === 'object') {
                        this.standardFieldLabels = parsedLabels;
                    }
                }
            } catch (_) {}
        },

        getAllStandardFields() {
            const list = [];
            const labels = this.standardFieldLabels || {};
            const filterMod = this.standardFieldsFilter || '';
            const search = (this.standardFieldsSearch || '').toLowerCase().trim();

            for (const ent of this.standardRequiredEntities) {
                if (filterMod && ent.key !== filterMod) continue;
                const defs = this.standardFieldDefinitions[ent.key] || [];
                for (const d of defs) {
                    const customLabel = (labels[ent.key] && labels[ent.key][d.key]) || '';
                    const effectiveLabel = customLabel || d.label;
                    if (search) {
                        const match = effectiveLabel.toLowerCase().includes(search)
                            || d.key.toLowerCase().includes(search)
                            || ent.label.toLowerCase().includes(search);
                        if (!match) continue;
                    }
                    const isReq = !!d.systemRequired || this.isStandardFieldRequired(ent.key, d.key);
                    list.push({
                        entity: ent.key,
                        entityLabel: ent.label,
                        key: d.key,
                        defaultLabel: d.label,
                        label: effectiveLabel,
                        customLabel: customLabel,
                        type: d.type || 'text',
                        systemRequired: !!d.systemRequired,
                        required: isReq,
                    });
                }
            }
            return list;
        },

        openEditStandardField(f) {
            this.editingStandardField = {
                entity: f.entity,
                entityLabel: f.entityLabel,
                key: f.key,
                defaultLabel: f.defaultLabel,
                customLabel: f.customLabel || '',
                label: f.customLabel || f.defaultLabel,
                required: f.required,
                systemRequired: f.systemRequired,
            };
        },

        cancelEditStandardField() {
            this.editingStandardField = null;
        },

        async saveEditStandardField() {
            if (!this.editingStandardField) return;
            const item = this.editingStandardField;
            const ent = item.entity;
            const key = item.key;

            if (!this.standardFieldLabels[ent]) this.standardFieldLabels[ent] = {};
            const trimmedLabel = (item.label || '').trim();
            if (trimmedLabel && trimmedLabel !== item.defaultLabel) {
                this.standardFieldLabels[ent][key] = trimmedLabel;
            } else {
                delete this.standardFieldLabels[ent][key];
            }

            if (!item.systemRequired) {
                if (!this.standardRequiredFields[ent]) this.standardRequiredFields[ent] = [];
                const idx = this.standardRequiredFields[ent].indexOf(key);
                if (item.required && idx === -1) {
                    this.standardRequiredFields[ent].push(key);
                } else if (!item.required && idx > -1) {
                    this.standardRequiredFields[ent].splice(idx, 1);
                }
            }

            this.editingStandardField = null;
            await this.saveAllStandardFields();
        },

        resetStandardFieldLabel() {
            if (!this.editingStandardField) return;
            const { entity, key, defaultLabel } = this.editingStandardField;
            this.editingStandardField.label = defaultLabel;
            this.editingStandardField.customLabel = '';
            if (this.standardFieldLabels[entity]) {
                delete this.standardFieldLabels[entity][key];
            }
        },

        isStandardFieldRequired(entity, key) {
            const defs = this.standardFieldDefinitions[entity] || [];
            const d = defs.find(x => x.key === key);
            if (d && d.systemRequired) return true;
            return (this.standardRequiredFields[entity] || []).includes(key);
        },

        async toggleStandardFieldRequired(entity, key) {
            const defs = this.standardFieldDefinitions[entity] || [];
            const d = defs.find(x => x.key === key);
            if (d && d.systemRequired) return;

            if (!this.standardRequiredFields[entity]) this.standardRequiredFields[entity] = [];
            const idx = this.standardRequiredFields[entity].indexOf(key);
            if (idx > -1) {
                this.standardRequiredFields[entity].splice(idx, 1);
            } else {
                this.standardRequiredFields[entity].push(key);
            }
            await this.saveAllStandardFields();
        },

        async saveAllStandardFields() {
            try {
                this.settingsForm.required_standard_fields = JSON.stringify(this.standardRequiredFields);
                this.settingsForm.standard_field_labels = JSON.stringify(this.standardFieldLabels);
                await this.saveSettings();
                this.notify(window.ZenI18n.t('Zaktualizowano pola standardowe'));
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            }
        },

        async loadCustomFieldDefs() {
            try {
                const list = await this.api('/custom-fields');
                this.customFieldDefs = Array.isArray(list) ? list : [];
                this.loadStandardRequiredFields();
            } catch (e) {
                console.warn('Błąd wczytywania pól własnych:', e.message);
            }
        },

        async createCustomField() {
            if (!this.newCustomField.label || !this.newCustomField.label.trim()) {
                this.notify(window.ZenI18n.t('Podaj nazwę pola własnego'));
                return;
            }
            try {
                await this.api('/custom-fields', {
                    method: 'POST',
                    body: JSON.stringify(this.newCustomField)
                });
                this.newCustomField.label = '';
                this.newCustomField.required = false;
                await this.loadCustomFieldDefs();
                this.notify(window.ZenI18n.t('Dodano pole własne'));
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            }
        },

        openEditCustomField(field) {
            this.editingCustomField = {
                id: field.id,
                entity: field.entity,
                label: field.label,
                kind: field.kind,
                required: !!field.required
            };
        },

        cancelEditCustomField() {
            this.editingCustomField = null;
        },

        async saveEditCustomField() {
            if (!this.editingCustomField || !this.editingCustomField.label?.trim()) {
                this.notify(window.ZenI18n.t('Podaj nazwę pola własnego'));
                return;
            }
            try {
                await this.api(`/custom-fields/${this.editingCustomField.id}`, {
                    method: 'PUT',
                    body: JSON.stringify(this.editingCustomField)
                });
                this.editingCustomField = null;
                await this.loadCustomFieldDefs();
                this.notify(window.ZenI18n.t('Zaktualizowano pole własne'));
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            }
        },

        async deleteCustomField(id) {
            if (!confirm(window.ZenI18n.t('Usunąć to pole własne i wszystkie jego wartości?'))) return;
            try {
                await this.api(`/custom-fields/${id}`, { method: 'DELETE' });
                await this.loadCustomFieldDefs();
                this.notify(window.ZenI18n.t('Usunięto pole własne'));
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            }
        },

        async onCustomValuesEntityChange() {
            this.customValuesSelectedRecord = '';
            this.customValuesRecordData = {};
            this.customValuesFields = [];
            if (!this.customValuesEntity) return;
            try {
                const ep = this.customValuesEntity.replace('service_catalog', 'service-catalog');
                const res = await this.api('/' + ep);
                const rows = Array.isArray(res) ? res : (res.items || res.clients || res.leads || res.tasks || []);
                this.customValuesRecords = rows;
            } catch (e) {
                this.customValuesRecords = [];
            }
        },

        async onCustomValuesRecordChange() {
            this.customValuesRecordData = {};
            this.customValuesFields = [];
            this.customValuesError = '';
            this.customValuesSuccess = '';
            if (!this.customValuesEntity || !this.customValuesSelectedRecord) return;
            try {
                const all = await this.api('/custom-fields');
                this.customValuesFields = (all || []).filter(f => f.entity === this.customValuesEntity);
                if (this.customValuesFields.length > 0) {
                    const vals = await this.api(`/custom-fields/${this.customValuesEntity}/${this.customValuesSelectedRecord}`);
                    this.customValuesRecordData = vals || {};
                }
            } catch (e) {
                this.customValuesError = e.message;
            }
        },

        async saveCustomValues() {
            if (!this.customValuesEntity || !this.customValuesSelectedRecord) return;
            this.customValuesSaving = true;
            this.customValuesSuccess = '';
            this.customValuesError = '';
            try {
                await this.api(`/custom-fields/${this.customValuesEntity}/${this.customValuesSelectedRecord}`, {
                    method: 'PUT',
                    body: JSON.stringify(this.customValuesRecordData)
                });
                this.customValuesSuccess = window.ZenI18n.t('Zapisano wartości pól własnych');
                setTimeout(() => { this.customValuesSuccess = ''; }, 2500);
            } catch (e) {
                this.customValuesError = e.message;
            } finally {
                this.customValuesSaving = false;
            }
        },

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

        // ═══════════════════════════════════════════════════════════
        // SZABLONY E-MAIL & SMTP
        // ═══════════════════════════════════════════════════════════
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
            const fullLogoUrl = rawLogo.startsWith('http') ? rawLogo : (window.location.origin + rawLogo);
            const logoTag = `<img src="${fullLogoUrl}" alt="${compName}" style="max-height: 46px; max-width: 220px; object-fit: contain; display: inline-block;" onerror="this.style.display='none'" />`;
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
                portal_url: window.location.origin + '/portal',
                login_url: window.location.origin,
                crm_ticket_url: window.location.origin + '/#tickets',
                crm_task_url: window.location.origin + '/#tasks',
                crm_client_url: window.location.origin + '/#clients/1',
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
