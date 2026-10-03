/* Settings component section; state is created for each CRM instance. */
window.ZenSettings = window.ZenSettings || {};
window.ZenSettings.fields = function () { return {
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

}; };
