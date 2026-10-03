window.ZenModules = window.ZenModules || {};
window.ZenModules.records = function () { return {
        gusLookup: { loading: false, error: '', message: '' },
        get companyProvider() {
            return this.settingsForm?.client_company_provider || (this.settingsForm?.gus_enabled === 'true' ? 'gus' : 'off');
        },
        get gusSearchEnabled() { return ['gus', 'mf'].includes(this.companyProvider); },
        get clientStatuses() {
            let statuses;
            try { statuses = JSON.parse(this.settingsForm?.client_statuses || 'null'); } catch (_) {}
            return Array.isArray(statuses) && statuses.length ? statuses : [
                {id: 'active', label: window.ZenI18n.t('Aktywny'), accent: '#16a34a'},
                {id: 'inactive', label: window.ZenI18n.t('Nieaktywny'), accent: '#64748b'},
                {id: 'prospect', label: window.ZenI18n.t('Potencjalny'), accent: '#ca8a04'},
            ];
        },
        get availableClientMetrics() {
            return [
                {id: 'all', label: window.ZenI18n.t('Wszyscy klienci'), color: '#007fce', icon: 'user'},
                ...this.clientStatuses.map(s => ({id: 'status:' + s.id, label: s.label, color: s.accent, icon: 'flag'})),
                {id: 'assigned', label: window.ZenI18n.t('Z opiekunem'), color: '#16886e', icon: 'user'},
                {id: 'unassigned', label: window.ZenI18n.t('Bez opiekuna'), color: '#64748b', icon: 'user'},
            ];
        },
        get clientMetrics() {
            let selected;
            try { selected = JSON.parse(this.settingsForm?.client_metrics || 'null'); } catch (_) {}
            if (!Array.isArray(selected)) selected = ['all', 'status:active', 'status:prospect', 'assigned'].map(id => ({id}));
            return selected.slice(0, 6).map(metric => {
                const option = this.availableClientMetrics.find(m => m.id === metric.id);
                return option ? {...option, color: /^#[0-9a-fA-F]{6}$/.test(metric.color || '') ? metric.color : option.color} : null;
            }).filter(Boolean);
        },
        clientMetricCount(id) {
            if (id === 'all') return this.clients.length;
            if (id === 'assigned') return this.clients.filter(c => c.assignee_id || c.assignee).length;
            if (id === 'unassigned') return this.clients.filter(c => !c.assignee_id && !c.assignee).length;
            return this.clients.filter(c => c.status === id.slice(7)).length;
        },
        clientMetricStyle(metric) {
            const color = /^#[0-9a-fA-F]{6}$/.test(metric.color || '') ? metric.color : '#007fce';
            const rgb = [1, 3, 5].map(offset => parseInt(color.slice(offset, offset + 2), 16));
            const text = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000 > 155 ? '#14283d' : '#ffffff';
            return {'--client-metric-color': color, '--client-metric-text': text};
        },
        clientStatusLabel(status) { return this.clientStatuses.find(s => s.id === status)?.label || status; },
        clientStatusStyle(status) {
            const color = this.clientStatuses.find(s => s.id === status)?.accent;
            return /^#[0-9a-fA-F]{6}$/.test(color || '') ? {color, backgroundColor: color + '18'} : {};
        },
        async lookupClientGus() {
            if (!this.gusSearchEnabled || this.gusLookup.loading) return;
            const form = this.modal.form;
            const nip = String(form.nip || '').replace(/[\s-]/g, '');
            const state = this.gusLookup = { loading: true, error: '', message: '' };
            try {
                if (!/^\d{10}$/.test(nip)) throw new Error(window.ZenI18n.t('Podaj poprawny NIP (10 cyfr).'));
                const company = await this.api('/clients/company-lookup?nip=' + encodeURIComponent(nip));
                if (!this.modal.open || this.modal.form !== form || String(form.nip || '').replace(/[\s-]/g, '') !== nip) return;
                for (const key of ['company', 'nip', 'regon', 'street', 'building_number', 'apartment_number', 'postal_code', 'city', 'country']) {
                    form[key] = company[key] || '';
                }
                if (company.krs) form.krs = company.krs;
                if (company.address !== undefined) form.address = company.address;
                if (!form.name) form.name = company.company;
                state.message = window.ZenI18n.t('Pobrano dane firmy. Sprawdź dane przed zapisaniem.');
            } catch (error) { state.error = error.message; }
            finally { state.loading = false; }
        },
        leadPicker(field) {
            const app = this;
            const form = this.modal.form;
            return {
                items: [], loading: false, error: '',
                async init() { await this.load(); },
                async load() {
                    this.loading = true;
                    this.error = '';
                    try {
                        const items = await app.api('/leads');
                        const selectedId = Number(form[field.key]);
                        if (selectedId && !items.some(item => item.id === selectedId)) {
                            items.push(await app.api('/leads/' + selectedId));
                        }
                        this.items = items.sort((a, b) => a.title.localeCompare(b.title, app.locale));
                    } catch (error) {
                        this.error = error.message;
                    } finally {
                        this.loading = false;
                    }
                },
            };
        },

        customFields: [],
        customFieldsReady: true,
        customFieldsRequest: 0,
        savingRecord: false,
        customEntity(mod) { return this.apiPath(mod).replace('service-catalog', 'service_catalog'); },
        async loadCustomFields(form, mod, id) {
            const requestId = ++this.customFieldsRequest;
            this.customFields = [];
            this.customFieldsReady = false;
            try {
                const entity = this.customEntity(mod);
                const all = await this.api('/custom-fields');
                const fields = (all || []).filter(f => f.entity === entity);
                let values = {};
                if (id && fields.length > 0) {
                    try {
                        values = await this.api(`/custom-fields/${entity}/${id}`);
                    } catch (_) {}
                }
                if (requestId !== this.customFieldsRequest) return;
                form = this.modal.form;
                for (const f of fields) {
                    form['custom_' + f.id] = (values && values[f.id] !== undefined) ? String(values[f.id]) : '';
                }
                this.customFields = fields;
            } catch (e) {
                if (requestId === this.customFieldsRequest) console.warn('Błąd wczytywania pól własnych:', e.message);
            } finally {
                if (requestId === this.customFieldsRequest) {
                    this.customFieldsReady = true;
                }
            }
        },
        fieldsFor(mod) {
            let reqFields = null;
            let customLabels = null;
            try {
                const s = this.settingsForm || this.settings;
                if (s?.required_standard_fields) {
                    reqFields = typeof s.required_standard_fields === 'string'
                        ? JSON.parse(s.required_standard_fields)
                        : s.required_standard_fields;
                }
                if (s?.standard_field_labels) {
                    customLabels = typeof s.standard_field_labels === 'string'
                        ? JSON.parse(s.standard_field_labels)
                        : s.standard_field_labels;
                }
            } catch (_) {}
            const systemReq = {
                clients: ['name'],
                leads: ['title'],
                contacts: ['first_name'],
                tasks: ['title'],
            };
            return (window.ZenConfig.FIELDS[mod] || []).filter(f => !this.modal.lockedRelations?.includes(f.key)).map(f => {
                let field = mod === 'leads' && f.key === 'stage'
                    ? { ...f, options: this.leadStages.map(s => ({ value: s.id, label: s.label })) }
                    : { ...f };
                if (mod === 'leads' && f.key === 'stage') field.type = 'lead-stage';
                if (mod === 'clients' && f.key === 'status') field.options = this.clientStatuses.map(s => ({value: s.id, label: s.label}));
                if (mod === 'leads' && f.key === 'source') {
                    let sources = [];
                    try {
                        const raw = this.settingsForm?.lead_sources;
                        if (raw) sources = typeof raw === 'string' ? JSON.parse(raw) : raw;
                    } catch (_) {}
                    if (!Array.isArray(sources) || sources.length === 0) {
                        sources = ['Strona WWW', 'Polecenie', 'Telefon', 'Social Media', 'Kampania Google', 'Inne'];
                    }
                    const currentVal = this.modal?.form?.source;
                    const opts = sources.map(s => ({ value: s, label: s }));
                    if (currentVal && !sources.includes(currentVal)) {
                        opts.push({ value: currentVal, label: currentVal });
                    }
                    field.type = 'select';
                    field.options = opts;
                }
                if (mod === 'tasks' && f.key === 'status') {
                    field.options = this.taskBoardStages.map(stage => ({ value: stage.id, label: stage.label }));
                }
                if (mod === 'users' && f.key === 'role' && this.managedRoles?.length) {
                    field.options = this.managedRoles.map(role => ({ value: role.key, label: role.name }));
                }
                if (mod === 'users' && f.key === 'password') {
                    field.required = false;
                    if (this.modal.editingId) {
                        field.label = window.ZenI18n.t('Nowe hasło (puste = bez zmiany)');
                    }
                }
                if (customLabels && customLabels[mod] && customLabels[mod][f.key]) {
                    field.label = customLabels[mod][f.key];
                }
                if (systemReq[mod]) {
                    if (systemReq[mod].includes(f.key)) {
                        field.required = true;
                    } else if (reqFields && Array.isArray(reqFields[mod])) {
                        field.required = reqFields[mod].includes(f.key);
                    } else {
                        field.required = false;
                    }
                }
                if (f.key === 'password' && this.modal.editingId) {
                    field.required = false;
                }
                if (mod === 'users' && f.key === 'password' && !this.modal.editingId) {
                    field.required = true;
                }
                return field;
            }).sort((a, b) => {
                if (!['leads','tasks'].includes(mod)) return 0;
                const order = mod === 'tasks' ? ['title','description','due_date','priority','status','reminder_offset','client_id','project_id','lead_id','service_id'] : ['title', 'client_id', 'source', 'stage', 'value', 'expected_close_date', 'probability', 'assignee_id', 'notes'];
                return order.indexOf(a.key) - order.indexOf(b.key);
            });
        },

        // ═══════════════════════════════════════════════════════════
        // ZARZĄDZANIE WIDOCZNYMI KOLUMNAMI (Klienci, Leady, Kontakty, Zadania, Projekty)
        // ═══════════════════════════════════════════════════════════
        columnPickerOpen: null,
        visibleColumns: {
            clients: JSON.parse(localStorage.getItem('zen_cols_clients') || 'null') || ['name', 'email', 'phone', 'company', 'assignee', 'status', 'actions'],
            leads: JSON.parse(localStorage.getItem('zen_cols_leads') || 'null') || ['title', 'client', 'stage', 'value', 'assignee', 'expected_close_date', 'actions'],
            contacts: JSON.parse(localStorage.getItem('zen_cols_contacts') || 'null') || ['name', 'client', 'position', 'email', 'phone', 'actions'],
            tasks: JSON.parse(localStorage.getItem('zen_cols_tasks') || 'null') || ['title', 'status', 'priority', 'due_date', 'context', 'assignees', 'actions'],
            projects: JSON.parse(localStorage.getItem('zen_cols_projects') || 'null') || ['name', 'status', 'client', 'manager', 'members', 'budget', 'dates', 'progress', 'actions'],
        },
        defaultColumns: {
            clients: ['name', 'email', 'phone', 'company', 'assignee', 'status', 'actions'],
            leads: ['title', 'client', 'stage', 'value', 'assignee', 'expected_close_date', 'actions'],
            contacts: ['name', 'client', 'position', 'email', 'phone', 'actions'],
            tasks: ['title', 'status', 'priority', 'due_date', 'context', 'assignees', 'actions'],
            projects: ['name', 'status', 'client', 'manager', 'members', 'budget', 'dates', 'progress', 'actions'],
        },
        columnLabels: {
            clients: { name: window.ZenI18n.t('Nazwa'), email: window.ZenI18n.t('Email'), phone: window.ZenI18n.t('Telefon'), company: window.ZenI18n.t('Firma'), assignee: window.ZenI18n.t('Opiekun'), status: window.ZenI18n.t('Status'), actions: window.ZenI18n.t('Akcje') },
            leads: { title: window.ZenI18n.t('Tytuł'), client: window.ZenI18n.t('Klient'), stage: window.ZenI18n.t('Etap'), value: window.ZenI18n.t('Wartość'), assignee: window.ZenI18n.t('Opiekun'), expected_close_date: window.ZenI18n.t('Data zamknięcia'), source: window.ZenI18n.t('Źródło'), probability: window.ZenI18n.t('Prawdopodobieństwo'), actions: window.ZenI18n.t('Akcje') },
            contacts: { name: window.ZenI18n.t('Osoba'), client: window.ZenI18n.t('Klient'), position: window.ZenI18n.t('Stanowisko'), email: window.ZenI18n.t('E-mail'), phone: window.ZenI18n.t('Telefon'), actions: window.ZenI18n.t('Akcje') },
            tasks: { title: window.ZenI18n.t('Zadanie'), status: window.ZenI18n.t('Status'), priority: window.ZenI18n.t('Priorytet'), due_date: window.ZenI18n.t('Termin'), context: window.ZenI18n.t('Klient / kontekst'), assignees: window.ZenI18n.t('Wykonawcy'), actions: window.ZenI18n.t('Akcje') },
            projects: { name: window.ZenI18n.t('Nazwa projektu'), status: window.ZenI18n.t('Status'), client: window.ZenI18n.t('Klient'), manager: window.ZenI18n.t('Opiekun'), members: window.ZenI18n.t('Zespół'), budget: window.ZenI18n.t('Budżet'), dates: window.ZenI18n.t('Terminy'), progress: window.ZenI18n.t('Postęp'), actions: window.ZenI18n.t('Akcje') },
        },
        availableColumns(entity) {
            const standard = Object.entries(this.columnLabels[entity] || {}).map(([key, label]) => ({
                key, label: window.ZenI18n.t(label), isCustom: false
            }));
            const custom = (this.allCustomFields || []).filter(f => f.entity === entity).map(f => ({
                key: 'custom_' + f.id, label: f.label, isCustom: true, field: f
            }));
            return [...standard, ...custom];
        },
        isColumnVisible(entity, key) {
            const list = this.visibleColumns[entity];
            if (!list || !Array.isArray(list)) return true;
            return list.includes(key);
        },
        toggleColumn(entity, key) {
            if (!this.visibleColumns[entity]) this.visibleColumns[entity] = [...(this.defaultColumns[entity] || [])];
            const idx = this.visibleColumns[entity].indexOf(key);
            if (idx > -1) {
                if (this.visibleColumns[entity].length > 1) {
                    this.visibleColumns[entity].splice(idx, 1);
                }
            } else {
                this.visibleColumns[entity].push(key);
            }
            localStorage.setItem('zen_cols_' + entity, JSON.stringify(this.visibleColumns[entity]));
        },
        resetColumns(entity) {
            this.visibleColumns[entity] = [...(this.defaultColumns[entity] || [])];
            localStorage.setItem('zen_cols_' + entity, JSON.stringify(this.visibleColumns[entity]));
        },
        customTableValues: {},
        async loadCustomValuesForTable(entity, ids) {
            if (!ids || !ids.length) return;
            try {
                const res = await this.api(`/custom-fields/${entity}/values?ids=${ids.join(',')}`);
                if (!this.customTableValues[entity]) this.customTableValues[entity] = {};
                Object.assign(this.customTableValues[entity], res || {});
            } catch (_) {}
        },
        getCustomFieldValue(entity, recordId, fieldId) {
            const val = this.customTableValues[entity]?.[String(recordId)]?.[String(fieldId)];
            if (val === undefined || val === null || val === '') return '—';
            if (val === 'true') return window.ZenI18n.t('Tak');
            if (val === 'false') return window.ZenI18n.t('Nie');
            return val;
        },
        allCustomFields: [],
        async loadAllCustomFields() {
            try {
                this.allCustomFields = await this.api('/custom-fields') || [];
            } catch (_) {}
        },

        // ═══════════════════════════════════════════════════════════
        // MULTI-USER OBSŁUGA DLA PROJEKTÓW I USŁUG
        // ═══════════════════════════════════════════════════════════
        addMultiUser(key, userId) {
            if (!userId) return;
            const uid = parseInt(userId, 10);
            if (!this.modal.form[key]) this.modal.form[key] = [];
            if (this.modal.form[key].includes(uid)) return;
            this.modal.form[key] = [...this.modal.form[key], uid];
            if (key === 'assignee_ids') this.addServiceAssignee?.(uid);
        },
        removeMultiUser(key, uid) {
            if (!this.modal.form[key]) return;
            this.modal.form[key] = this.modal.form[key].filter(x => x !== uid);
            if (key === 'assignee_ids') this.removeServiceAssignee?.(uid);
        },
        availableMultiUsers(key) {
            const chosen = this.modal.form[key] || [];
            return (this.users || []).filter(u => !chosen.includes(u.id));
        },

        openModal(item = null, defaultStage = null, keepDetail = false, viewOverride = null, context = null) {
            if (this.currentView === 'dashboard' && !keepDetail && !viewOverride) return;
            const actionView = viewOverride || this.currentView;
            if (!this.canRecordAction(actionView, item ? 'edit' : 'create')) {
                this.notify(window.ZenI18n.t('Brak uprawnienia do tej operacji'));
                return false;
            }
            this.modal.view = viewOverride;
            this.modal.keepDetail = keepDetail;
            this.modal.editingId = item ? item.id : null;
            this.modal.form = item
                ? { ...item, is_primary: Boolean(item.is_primary) }
                : (defaultStage ? { stage: defaultStage, is_primary: false } : { is_primary: false });
            if (['documents', 'offers'].includes(actionView)) {
                this.modal.form.data = { ...(this.modal.form.data || {}), custom: { ...(this.modal.form.data?.custom || {}) }, type_fields: { ...(this.modal.form.data?.type_fields || {}) } };
            }
            if (actionView === 'leads' && !this.modal.form.stage) this.modal.form.stage = defaultStage || this.leadStages[0]?.id;
            if (actionView === 'leads' && this.modal.form.probability == null) {
                this.modal.form.probability = 0;
            }
            if (actionView === 'tasks' && !item) Object.assign(this.modal.form, {status:'todo',priority:'medium',due_date:this.taskFormDate(1),reminder_offset:''});
            if (actionView === 'clients' && !item) this.modal.form.status = this.clientStatuses.some(s => s.id === 'active') ? 'active' : this.clientStatuses[0].id;
            this.modal.lockedRelations = context?.lockedRelations || [];
            if (!item && context?.prefill) Object.assign(this.modal.form, context.prefill);
            if (actionView === 'documents') this.syncDocumentTypeSelection();
            if (this.modal.form && !Array.isArray(this.modal.form.assignee_ids)) {
                this.modal.form.assignee_ids = [];
            }
            if (this.modal.form && !Array.isArray(this.modal.form.member_ids)) {
                this.modal.form.member_ids = [];
            }
            if (this.modal.form && !Array.isArray(this.modal.form.team_ids)) {
                this.modal.form.team_ids = item?.teams ? item.teams.map(t => t.id) : (item?.team_ids || []);
            }
            if (actionView === 'users') {
                this.modal.form.password = '';
            }
            this.gusLookup = { loading: false, error: '', message: '' };
            this.modal.error = '';
            this.modal.open = true;
            this.ensureLookups();
            const mod = this.modal.view || this.currentView;
            this.loadCustomFields(this.modal.form, mod, this.modal.editingId);
            if (mod === 'tasks') {
                if (item && item.id) {
                    this.loadTaskAssignees(item.id);
                } else {
                    this.taskAssigneesUI = this.user?.id ? [{user_id:Number(this.user.id),user:{...this.user},status:'pending',comment:''}] : [];
                }
            }
            return true;
        },

        taskFormDate(days, existing = null) {
            const date=new Date();date.setDate(date.getDate()+days);
            const time=typeof existing==='string' && /T\d{2}:\d{2}/.test(existing) ? existing.split('T')[1].slice(0,5) : '09:00';
            return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}T${time}`;
        },
        taskFormSection(key) {
            if(key==='title') return window.ZenI18n.t('Co trzeba zrobić?');
            if(key==='due_date') return window.ZenI18n.t('Termin i organizacja');
            const relations=this.fieldsFor('tasks').filter(field=>['client_id','project_id','lead_id','service_id'].includes(field.key));
            return key===relations[0]?.key ? window.ZenI18n.t('Powiązania zadania') : '';
        },

        syncDocumentTypeSelection() {
            if ((this.modal.view || this.currentView) !== 'documents' || !this.documentTypes.length) return;
            const selected = this.documentTypes.find(t => t.key === this.modal.form.type && (t.is_active || this.modal.editingId));
            if (selected) return;
            this.modal.form.type = this.documentTypes.find(t => t.is_active)?.key || '';
            this.modal.form.template_id = '';
            this.modal.form.data.type_fields = {};
        },

        changeDocumentType() {
            this.modal.form.template_id = '';
            this.modal.form.data.type_fields = {};
        },

        modalTitle() {
            const view = this.modal.view || this.currentView;
            const isEdit = !!this.modal.editingId;
            const titles = {
                clients: { new: window.ZenI18n.t('Nowy klient'), edit: window.ZenI18n.t('Edytuj klienta') },
                contacts: { new: window.ZenI18n.t('Nowy kontakt'), edit: window.ZenI18n.t('Edytuj kontakt') },
                leads: { new: window.ZenI18n.t('Nowy lead'), edit: window.ZenI18n.t('Edytuj lead') },
                tasks: { new: window.ZenI18n.t('Nowe zadanie'), edit: window.ZenI18n.t('Edytuj zadanie') },
                projects: { new: window.ZenI18n.t('Nowy projekt'), edit: window.ZenI18n.t('Edytuj projekt') },
                services: { new: window.ZenI18n.t('Nowa usługa'), edit: window.ZenI18n.t('Edytuj usługę') },
                serviceCatalog: { new: window.ZenI18n.t('Nowa pozycja w katalogu'), edit: window.ZenI18n.t('Edytuj pozycję katalogu') },
                offers: { new: window.ZenI18n.t('Nowa oferta'), edit: window.ZenI18n.t('Edytuj ofertę') },
                documents: { new: window.ZenI18n.t('Nowy dokument'), edit: window.ZenI18n.t('Edytuj dokument') },
                users: { new: window.ZenI18n.t('Nowy użytkownik'), edit: window.ZenI18n.t('Edytuj użytkownika') },
                meetings: { new: window.ZenI18n.t('Nowe spotkanie'), edit: window.ZenI18n.t('Edytuj spotkanie') },
            };
            if (titles[view]) {
                return isEdit ? titles[view].edit : titles[view].new;
            }
            // Fallback: przeszukaj strukturę menu (w tym dzieci podmenu)
            let label = '';
            for (const item of (this.menu || [])) {
                if (item.id === view) { label = item.label; break; }
                if (item.children) {
                    const c = item.children.find(ch => ch.id === view);
                    if (c) { label = c.label; break; }
                }
            }
            const prefix = isEdit ? window.ZenI18n.t('Edytuj: ') : window.ZenI18n.t('Nowy: ');
            return label ? (prefix + label) : (isEdit ? window.ZenI18n.t('Edytuj') : window.ZenI18n.t('Nowy'));
        },

        async ensureLookups() {
            const needUsers = this.users.length === 0;
            const needClients = this.clients.length === 0;
            const needTemplates = this.templates.length === 0;
            const needDocumentTypes = this.documentTypes.length === 0;
            const needProjects = !this.projects || this.projects.length === 0;
            const needTeams = !this.teams || this.teams.length === 0;
            if (!needUsers && !needClients && !needTemplates && !needDocumentTypes && !needProjects && !needTeams) return;
            try {
                if (needUsers) {
                    const u = await this.api('/users');
                    this.users = Array.isArray(u) ? u : [];
                }
            } catch (_) {}
            try {
                if (needTeams) {
                    const t = await this.api('/teams');
                    this.teams = Array.isArray(t) ? t : [];
                }
            } catch (_) {}
            try {
                if (needClients) {
                    const c = await this.loadClientOptions();
                    this.clients = Array.isArray(c) ? c : (c.clients || []);
                }
            } catch (_) {}
            try {
                if (needTemplates) {
                    const t = await this.api('/templates');
                    this.templates = Array.isArray(t) ? t : [];
                }
            } catch (_) {}
            try {
                if (needDocumentTypes) {
                    this.documentTypes = await this.api('/document-types');
                    this.syncDocumentTypeSelection();
                }
            } catch (_) {}
            try {
                if (needProjects) {
                    const pr = await this.api('/projects');
                    this.projects = Array.isArray(pr) ? pr : [];
                }
            } catch (_) {}
        },

        async save() {
            if (this.savingRecord) return;
            this.modal.error = '';
            if (!this.canRecordAction(this.modal.view || this.currentView, this.modal.editingId ? 'edit' : 'create')) {
                this.modal.error = window.ZenI18n.t('Brak uprawnienia do tej operacji');
                return;
            }
            const payload = { ...this.modal.form };
            const customValues = {};
            for (const f of (this.customFields || [])) {
                customValues[f.id] = payload['custom_' + f.id] ?? '';
                delete payload['custom_' + f.id];
            }
            if (payload.password != null && typeof payload.password === 'string' && !payload.password.trim()) {
                delete payload.password;
            } else if (!payload.password) {
                delete payload.password;
            }
            const targetView = this.modal.view || this.currentView;
            const wasQuickAdd = !!this.modal.view;
            this.savingRecord = true;
            try {
                if (targetView === 'tasks' && payload.reminder_offset != null && payload.reminder_offset !== '') {
                    if (payload.reminder_offset === 'off') payload.reminder_at = null;
                    else {
                        const at = new Date(payload.due_date).getTime() - Number(payload.reminder_offset)*60000;
                        if (!Number.isFinite(at) || at <= Date.now()) throw new Error(window.ZenI18n.t('Ustaw termin zadania tak, aby przypomnienie wypadało w przyszłości.'));
                        payload.reminder_at = new Date(at).toISOString();
                        this.enableReminderSound();
                    }
                }
                delete payload.reminder_offset;
                const apiTarget = this.apiPath(targetView);
                let saved;
                if (this.modal.editingId) {
                    saved = await this.api(`/${apiTarget}/${this.modal.editingId}`, {
                        method: 'PUT', body: JSON.stringify(payload),
                    });
                } else {
                    saved = await this.api(`/${apiTarget}`, {
                        method: 'POST', body: JSON.stringify(payload),
                    });
                }
                const recordId = saved?.id || this.modal.editingId;
                this.modal.editingId = recordId;
                if (recordId && this.customFields && this.customFields.length > 0) {
                    try {
                        await this.api(`/custom-fields/${this.customEntity(targetView)}/${recordId}`, {
                            method: 'PUT',
                            body: JSON.stringify(customValues)
                        });
                    } catch (cfErr) {
                        console.warn('Nie udało się zapisać pól własnych:', cfErr);
                    }
                }
                // Zapisz przypisania jesli to zadanie
                if (targetView === 'tasks') {
                    // Po create – musimy znac id; pobierz ostatnio utworzone
                    let tid = this.modal.editingId;
                    if (!tid) {
                        try {
                            const list = await this.api('/tasks');
                            const latest = list[0];
                            tid = latest ? latest.id : null;
                        } catch (_) {}
                    }
                    if (tid) await this.saveTaskAssignees(tid);
                    await this.loadReminders();
                }
                this.modal.open = false;
                this.notify(window.ZenI18n.t('Zapisano zmiany'));
                const keep = this.modal.keepDetail;
                this.modal.view = null;
                this.modal.keepDetail = false;
                this.modal.lockedRelations = [];
                if (this.detailView.open && (wasQuickAdd || keep)) {
                    await this.loadDetail();
                } else {
                    await this.reload();
                }
                if (this.activeProject) {
                    await this.loadProjectTasks();
                }
            } catch (e) { this.modal.error = e.message; } finally { this.savingRecord = false; }
        },

        async remove(id) {
            if (!confirm(window.ZenI18n.t('Usunąć ten element?'))) return;
            try {
                await this.api(`/${this.apiPath(this.currentView)}/${id}`, { method: 'DELETE' });
                await this.reload();
            } catch (e) { this.notify(e.message); }
        },

}; };
