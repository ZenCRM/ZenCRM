/* ═══════════════════════════════════════════════════════════════
   ZenCRM – główny komponent Alpine.js
   Wymaga wcześniej załadowanych: config.js, helpers.js, api.js
   ═══════════════════════════════════════════════════════════════ */

function crmApp() {
    const component = {

        // ═══════════════════════════════════════════════════════════
        // SERVICE HELPERS
        // ═══════════════════════════════════════════════════════════
        serviceStatusLabel(s) {
            return { exemplary: window.ZenI18n.t('Wzorowa'), good: window.ZenI18n.t('Dobra'),
                     problematic: window.ZenI18n.t('Problematyczna'), critical: window.ZenI18n.t('Krytyczna') }[s] || s || '—';
        },
        serviceStatusClass(s) {
            return { exemplary: 'bg-green-100 text-green-700',
                     good: 'bg-blue-100 text-blue-700',
                     problematic: 'bg-yellow-100 text-yellow-700',
                     critical: 'bg-red-100 text-red-700' }[s] || 'bg-gray-100 text-gray-700';
        },
        serviceRiskLabel(r) {
            if (r === null || r === undefined || r === '') return '—';
            const n = Number(r);
            if (isNaN(n)) return '—';
            if (n >= 8) return window.ZenI18n.t('Wysokie');
            if (n >= 5) return window.ZenI18n.t('Średnie');
            return window.ZenI18n.t('Niskie');
        },
        serviceRiskClass(r) {
            if (r === null || r === undefined || r === '') return 'bg-gray-100 text-gray-700';
            const n = Number(r);
            if (isNaN(n)) return 'bg-gray-100 text-gray-700';
            if (n >= 8) return 'bg-red-100 text-red-700';
            if (n >= 5) return 'bg-yellow-100 text-yellow-700';
            return 'bg-green-100 text-green-700';
        },

        // ═══════════════════════════════════════════════════════════
        // AUTH
        // ═══════════════════════════════════════════════════════════
        token: localStorage.getItem('token') || '',
        user: JSON.parse(localStorage.getItem('user') || 'null'),
        loginForm: { email: '', password: '' },
        loginError: '',
        showPassword: false,
        loginLoading: false,
        forgotModal: {
            code: '',
            password: '',
            awaitingCode: false,
            open: false,
            email: '',
            loading: false,
            success: '',
            error: '',
        },
        needsSetup: false,
        setupForm: {
            first_name: '',
            last_name: '',
            email: '',
            password: '',
            password_confirm: '',
        },
        setupLoading: false,
        setupError: '',
        showSetupPassword: false,

        // ═══════════════════════════════════════════════════════════
        // UI
        // ═══════════════════════════════════════════════════════════
        darkMode: localStorage.getItem('darkMode') === 'true',
        sidebarOpen: false,
        currentView: (location.hash.replace('#', '') || localStorage.getItem('lastView') || 'dashboard'),
        search: '',
        taskFilter: '',
        taskViewMode: localStorage.getItem('taskViewMode') || 'table',
        draggedLead: null,
        dragOverStage: null,
        draggedTask: null,
        dragOverTaskStatus: null,
        kanbanMode: 'kanban',
        kanbanScrollIndex: 0,
        calendarMode: 'both',
        settingsTab: 'branding',
        settingsForm: {},
        settingsSaved: '',
        settingsError: '',
        releaseInfo: null,
        releaseLoading: false,
        releaseError: '',
        translationData: window.ZenCustomI18n || {languages:{pl:{name:'Polski',base:'pl'},en:{name:'English',base:'en'}},overrides:{}},
        translationLocale: 'pl',
        translationSearch: '',
        translationLimit: 80,
        translationDraft: {},
        translationOriginal: {},
        translationError: '',
        translationSaved: '',
        newTranslationLanguage: {code:'',name:'',base_locale:'pl'},
        emailTemplates: [],
        selectedEmailTemplate: null,
        emailTemplateForm: { subject: '', body_html: '' },
        emailTemplateSaved: '',
        emailTemplateError: '',
        emailEditorTab: 'edit',
        standardFieldsFilter: '',
        standardFieldsSearch: '',
        editingStandardField: null,
        smtpForm: {
            smtp_host: '',
            smtp_port: 587,
            smtp_user: '',
            smtp_password: '',
            smtp_from_email: '',
            smtp_from_name: '',
            smtp_encryption: 'tls',
            smtp_enabled: false,
            smtp_password_set: false,
        },
        smtpTestEmail: '',
        smtpTestLoading: false,
        smtpTestResult: null,
        smtpSaved: '',
        smtpError: '',
        taskAssigneesUI: [],
        assignPicker: { open: false, lead: null, x: 0, y: 0 },
        avatarTs: Date.now(),
        detailView: {
            open: false,
            type: 'client',       // 'client' | 'lead'
            id: null,
            data: null,
            tab: 'overview',
            contacts: [],
            tasks: [],
            documents: [],
            comments: [],
            activities: [],
            newComment: '',
            loading: false,
        },
        visibleKanbanCols: 5,
        _kanbanResizeHandler: null,

        // ═══════════════════════════════════════════════════════════
        // DANE
        // ═══════════════════════════════════════════════════════════
        stats: { cards: {}, funnel: {}, overdue_tasks: [], today_tasks: [], upcoming_tasks: [], upcoming_meetings: [] },
        dashboardTaskTab: 'today',
        clients: [], leads: [], tasks: [], meetings: [], projects: [], teams: [],
        services: [], serviceCatalog: [], offers: [], documents: [], templates: [], documentTypes: [], users: [], contacts: [],
        archiveItems: [], isAdmin: false,
        archiveSearch: '',
        archiveTypeFilter: '',
        archiveLoading: false,
        archivePreviewModal: { open: false, item: null, loading: false },
        userTab: 'employees',
        userTeamFilter: '',
        userSearch: '',
        listPages: { clients: 1, contacts: 1, projects: 1, tasks: 1, services: 1, offers: 1, documents: 1, serviceCatalog: 1, templates: 1, users: 1, tickets: 1 },
        listPageSizes: { clients: 10, contacts: 10, projects: 10, tasks: 10, services: 10, offers: 10, documents: 10, serviceCatalog: 10, templates: 10, users: 10, tickets: 10 },
        listPageCount(view, count) {
            return Math.max(1, Math.ceil(count / this.listPageSizes[view]));
        },
        listPage(view, count) {
            return Math.min(this.listPages[view], this.listPageCount(view, count));
        },
        pagedItems(view, items) {
            const start = (this.listPage(view, items.length) - 1) * this.listPageSizes[view];
            return items.slice(start, start + this.listPageSizes[view]);
        },
        setListPage(view, page, count) {
            this.listPages[view] = Math.max(1, Math.min(Number(page), this.listPageCount(view, count)));
        },
        setListPageSize(view, size) {
            this.listPageSizes[view] = [10, 20, 50].includes(Number(size)) ? Number(size) : 10;
            this.listPages[view] = 1;
        },

        // ═══════════════════════════════════════════════════════════
        // MODALE
        // ═══════════════════════════════════════════════════════════
        modal:    { open: false, editingId: null, form: {}, error: '', view: null, lockedRelations: [] },
        profile:  { open: false, form: { email_notifications: {} }, error: '', success: '' },
        password: { open: false, form: { current_password: '', new_password: '', confirm: '' }, error: '', success: '' },
        teamModal: {
            open: false,
            editingId: null,
            form: { name: '', description: '', color: '#018bfc', leader_id: null, member_ids: [] },
            error: '',
            saving: false,
        },
        templateModal: {
            open: false,
            editingId: null,
            form: { name: '', type: 'offer', content: '', variables: [] },
            error: '', previewError: '', previewLoading: false,
        },
        documentTypeModal: { open: false, editingKey: null, form: { key: '', name: '', fields: [], is_active: true }, error: '' },
        generateModal: { open: false, type: 'document', item: null, templateId: '', custom: {}, typeFields: {}, error: '' },
        attachmentView: { entity: '', recordId: null, files: [], busy: false, error: '', editingId: null, editingName: '' },

        // ═══════════════════════════════════════════════════════════
        // KALENDARZ
        // ═══════════════════════════════════════════════════════════
        calendarDate: new Date(),

        // ═══════════════════════════════════════════════════════════
        // KONFIGURACJA
        // ═══════════════════════════════════════════════════════════
        menu: window.ZenConfig.MENU,
        openMenuGroups: {
            crm: true,
            services_group: false,
            documents_group: false,
            tickets_group: false,
            portal_group: false,
        },

        toggleMenuGroup(groupId) {
            const willOpen = !this.openMenuGroups[groupId];
            for (const key of Object.keys(this.openMenuGroups)) {
                this.openMenuGroups[key] = false;
            }
            this.openMenuGroups[groupId] = willOpen;
        },

        // ═══════════════════════════════════════════════════════════
        // GETTERS
        // ═══════════════════════════════════════════════════════════
        get dashboardCards() { return window.ZenConfig.DASHBOARD_CARDS; },
        get usersById() {
            const map = {};
            for (const u of this.users) map[u.id] = u;
            return map;
        },
        get leadStages() { return (this.customLeadStages || window.ZenConfig.LEAD_STAGES).map(s => ({...s, label: s.label === window.ZenI18n.stageLabels[s.id] ? this.t(s.label) : s.label})); },

        get filteredClients() {
            if (!this.search) return this.clients;
            const s = this.search.toLowerCase();
            return this.clients.filter(c =>
                (c.name    || '').toLowerCase().includes(s) ||
                (c.email   || '').toLowerCase().includes(s) ||
                (c.company || '').toLowerCase().includes(s));
        },

        get monthLabel() {
            return this.calendarDate.toLocaleDateString(window.ZenI18n.locale, { month: 'long', year: 'numeric' });
        },

        get calendarDays() {
            const year = this.calendarDate.getFullYear();
            const month = this.calendarDate.getMonth();
            const first = new Date(year, month, 1);
            const startDay = (first.getDay() + 6) % 7; // poniedziałek = 0
            const start = new Date(year, month, 1 - startDay);
            const days = [];
            for (let i = 0; i < 42; i++) {
                const d = new Date(start);
                d.setDate(start.getDate() + i);
                const dateStr = this.localDateKey(d);
                const meetings = this.meetings.filter(m =>
                    m.start_time && this.localDateKey(new Date(m.start_time)) === dateStr);
                days.push({ date: d, isCurrentMonth: d.getMonth() === month, meetings });
            }
            return days;
        },

        // ═══════════════════════════════════════════════════════════
        // AUTH
        async loadStats() {
            try { this.stats = await this.api('/stats'); }
            catch (e) { this.listError = e.message; }
        },

        async renderFunnel() { await window.renderZenDashboard(this); },

        // ═══════════════════════════════════════════════════════════
        // CRUD – GENERYCZNY
        // ═══════════════════════════════════════════════════════════
        // ═══════════════════════════════════════════════════════════
        // ZADANIA
        // ═══════════════════════════════════════════════════════════
        async toggleTask(task) {
            // Jesli zadanie ma przypisanych - otworz modal do zmiany statusu
            const assignees = task.assignees || [];
            if (assignees.length > 0) {
                this.openModal(task);
                return;
            }
            const newStatus = task.status === 'done' ? 'todo' : 'done';
            try {
                await this.api(`/tasks/${task.id}`, {
                    method: 'PUT', body: JSON.stringify({ status: newStatus }),
                });
                task.status = newStatus;
            } catch (e) { this.notify(e.message); }
        },

        // ═══════════════════════════════════════════════════════════
        // KANBAN – DRAG & DROP
        // ═══════════════════════════════════════════════════════════
        // ═══════════════════════════════════════════════════════════
        // GENEROWANIE OFERT / DOKUMENTÓW (link + PDF)
        // ═══════════════════════════════════════════════════════════
        // ═══════════════════════════════════════════════════════════
        // HELPERS
        // ═══════════════════════════════════════════════════════════
        clientName(id) {
            if (!id) return '';
            const c = this.clients.find(x => x.id === id);
            return c ? c.name : `#${id}`;
        },
        projectName(id) {
            if (!id) return '';
            const p = (this.projects || []).find(x => x.id === id);
            return p ? p.name : '';
        },

        formatNumber(v)     { return window.ZenHelpers.formatNumber(v); },
        statusLabel(s)      { return window.ZenHelpers.statusLabel(s); },
        priorityLabel(p)    { return window.ZenHelpers.priorityLabel(p); },
        billingLabel(c)     { return window.ZenHelpers.billingLabel(c); },
        offerStatusLabel(s) { return window.ZenHelpers.offerStatusLabel(s); },
        docTypeLabel(t)     { return this.documentTypes.find(x => x.key === t)?.name || window.ZenHelpers.docTypeLabel(t); },
        roleLabel(r)        { return this.managedRoles?.find(role => role.key === r)?.name || window.ZenHelpers.roleLabel(r); },

        // ═══════ KANBAN HELPERS ═══════
        avatarInitials(text) {
            if (!text) return '?';
            const words = String(text).trim().split(/\s+/).filter(Boolean);
            if (words.length === 0) return '?';
            if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
            return (words[0][0] + words[1][0]).toUpperCase();
        },

        // ═══════════════════════════════════════════════════════════
        // KALENDARZ
        // ═══════════════════════════════════════════════════════════
        prevMonth() {
            this.calendarDate = new Date(this.calendarDate.getFullYear(),
                                         this.calendarDate.getMonth() - 1, 1);
            this.calendarSelected = new Date(this.calendarDate);
        },
        nextMonth() {
            this.calendarDate = new Date(this.calendarDate.getFullYear(),
                                         this.calendarDate.getMonth() + 1, 1);
            this.calendarSelected = new Date(this.calendarDate);
        },
        goToToday() {
            this.calendarDate = new Date();
            this.calendarSelected = new Date(this.calendarDate);
        },
        selectCalendarDay(date) {
            this.calendarSelected = new Date(date);
            if (date.getMonth() !== this.calendarDate.getMonth() || date.getFullYear() !== this.calendarDate.getFullYear()) {
                this.calendarDate = new Date(date.getFullYear(), date.getMonth(), 1);
            }
        },

        // ═══════════════════════════════════════════════════════════
        // PROFIL
        // ═══════════════════════════════════════════════════════════
        activityIcon(action) {
            const names = { created: 'plus', updated: 'edit', comment: 'comment', sms: 'comment', call: 'phone', email: 'mail', contact_added: 'user', converted: 'check', archived: 'activity', restored: 'activity' };
            return { icon: window.zenIcon(names[action] || 'activity'), cls: 'zen-activity-badge' };
        },

        relativeTime(iso) {
            if (!iso) return '';
            const date = new Date(iso), seconds=(date.getTime()-Date.now())/1000;
            if (!Number.isFinite(seconds)) return '';
            const formatter=new Intl.RelativeTimeFormat(this.locale,{numeric:'auto'});
            for(const [unit,size] of [['day',86400],['hour',3600],['minute',60]]) {
                if(Math.abs(seconds)>=size) return formatter.format(Math.round(seconds/size),unit);
            }
            return formatter.format(0,'second');
        },

        fullName(u) {
            if (!u) return window.ZenI18n.t('System');
            const fn = u.first_name || '';
            const ln = u.last_name || '';
            const full = (fn + ' ' + ln).trim();
            return full || window.ZenI18n.t('Użytkownik');
        },

        initialsFrom(u) {
            if (!u) return '?';
            const a = (u.first_name || '')[0] || '';
            const b = (u.last_name || '')[0] || '';
            return (a + b).toUpperCase() || '?';
        },

        // ═══════ DASHBOARD HELPERS ═══════
        get greeting() {
            const h = new Date().getHours();
            if (h < 5)  return window.ZenI18n.t('Dobranoc');
            if (h < 12) return window.ZenI18n.t('Dzień dobry');
            if (h < 18) return window.ZenI18n.t('Cześć');
            return window.ZenI18n.t('Dobry wieczór');
        },

        get todayLabel() {
            const d = new Date();
            const opts = { weekday: 'long', day: 'numeric', month: 'long' };
            const s = d.toLocaleDateString(window.ZenI18n.locale, opts);
            return s.charAt(0).toUpperCase() + s.slice(1);
        },

        // ═══════ AVATAR UPLOAD ═══════
        // ═══════════════════════════════════════════════════════════
        // ARCHIWUM / SOFT DELETE
        // ═══════════════════════════════════════════════════════════
        archiveTypeLabel(t) {
            const m = {
                clients: window.ZenI18n.t('Klient'),
                leads: window.ZenI18n.t('Lead'),
                contacts: window.ZenI18n.t('Kontakt'),
                tasks: window.ZenI18n.t('Zadanie'),
                projects: window.ZenI18n.t('Projekt'),
                meetings: window.ZenI18n.t('Spotkanie'),
                services: window.ZenI18n.t('Usługa'),
                service_catalog: window.ZenI18n.t('Katalog usług'),
                offers: window.ZenI18n.t('Oferta'),
                documents: window.ZenI18n.t('Dokument')
            };
            return m[t] || t;
        },

        archiveTypeBadgeClass(t) {
            const map = {
                clients: 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800',
                leads: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-300 dark:border-amber-800',
                projects: 'bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-300 dark:border-purple-800',
                contacts: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-300 dark:border-emerald-800',
                tasks: 'bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-300 dark:border-indigo-800',
                meetings: 'bg-pink-50 text-pink-700 border-pink-200 dark:bg-pink-900/30 dark:text-pink-300 dark:border-pink-800',
                services: 'bg-teal-50 text-teal-700 border-teal-200 dark:bg-teal-900/30 dark:text-teal-300 dark:border-teal-800',
                service_catalog: 'bg-teal-50 text-teal-700 border-teal-200 dark:bg-teal-900/30 dark:text-teal-300 dark:border-teal-800',
                offers: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-900/30 dark:text-rose-300 dark:border-rose-800',
                documents: 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700',
            };
            return map[t] || 'bg-gray-100 text-gray-700 border-gray-200 dark:bg-gray-700 dark:text-gray-300';
        },

        filteredArchiveItems() {
            let list = this.archiveItems || [];
            if (this.archiveTypeFilter) {
                list = list.filter(item => item._type === this.archiveTypeFilter);
            }
            if (this.archiveSearch && this.archiveSearch.trim()) {
                const s = this.archiveSearch.toLowerCase().trim();
                list = list.filter(item => {
                    const title = (item._title || item.title || item.name || item.full_name || '').toLowerCase();
                    const sub = (item._subtitle || item.email || item.company || '').toLowerCase();
                    const by = (item.deleted_by?.name || item.deleted_by?.email || '').toLowerCase();
                    const typeLbl = (this.archiveTypeLabel(item._type) || '').toLowerCase();
                    return title.includes(s) || sub.includes(s) || by.includes(s) || typeLbl.includes(s);
                });
            }
            return list;
        },

        formatArchiveDate(dateStr) {
            if (!dateStr) return '—';
            try {
                const d = new Date(dateStr);
                if (isNaN(d.getTime())) return dateStr;
                return d.toLocaleString(window.ZenI18n.locale || window.ZenI18n.locale, {
                    year: 'numeric', month: '2-digit', day: '2-digit',
                    hour: '2-digit', minute: '2-digit'
                });
            } catch (_) {
                return dateStr;
            }
        },

        formatDate(d) {
            return window.formatDate ? window.formatDate(d) : (d || '—');
        },

        formatDateTime(d) {
            return window.formatDateTime ? window.formatDateTime(d) : (d || '—');
        },

        async loadArchive() {
            this.archiveLoading = true;
            try {
                const r = await this.api('/archive');
                this.archiveItems = r.items || [];
                this.isAdmin = !!r.is_admin;
            } catch (e) {
                console.error(e);
                this.archiveItems = [];
                this.notify(window.ZenI18n.t('Błąd wczytywania archiwum: ') + e.message);
            } finally {
                this.archiveLoading = false;
            }
        },

        openArchivePreview(item) {
            this.archivePreviewModal = {
                open: true,
                item: { ...item },
                loading: false
            };
        },

        closeArchivePreview() {
            this.archivePreviewModal.open = false;
            this.archivePreviewModal.item = null;
        },

        async archiveFromModal() {
            if (!this.canRecordAction(this.modal.view || this.currentView, 'delete')) {
                this.modal.error = window.ZenI18n.t('Brak uprawnienia do tej operacji');
                return;
            }
            if (!this.modal.editingId || !confirm(window.ZenI18n.t('Przenieść do archiwum?'))) return;
            const view = this.modal.view || this.currentView;
            try {
                await this.api(`/${this.apiPath(view)}/${this.modal.editingId}`, { method: 'DELETE' });
                this.modal.open = false;
                if (this.detailView.open) {
                    this.closeDetail();
                } else {
                    await this.reload();
                }
            } catch (e) { this.modal.error = e.message; }
        },

        async permanentDeleteFromModal() {
            if (!this.modal.editingId || !confirm(window.ZenI18n.t('USUNĄĆ TRWALE? Tej operacji nie można cofnąć.'))) return;
            const view = this.modal.view || this.currentView;
            try {
                await this.api(`/${this.apiPath(view)}/${this.modal.editingId}/permanent`, { method: 'DELETE' });
                this.modal.open = false;
                if (this.detailView.open) {
                    this.closeDetail();
                } else {
                    await this.reload();
                }
            } catch (e) { this.modal.error = e.message; }
        },

        async restoreItem(item) {
            try {
                await this.api(`/archive/${item._type}/${item.id}/restore`, { method: 'POST' });
                this.notify(window.ZenI18n.t('Przywrócono element z archiwum'));
                if (this.archivePreviewModal.open && this.archivePreviewModal.item?.id === item.id) {
                    this.closeArchivePreview();
                }
                await this.loadArchive();
            } catch (e) { this.notify(e.message); }
        },

        async permanentDeleteItem(item) {
            if (!confirm(window.ZenI18n.t('USUNĄĆ TRWALE? Nie można cofnąć.'))) return;
            try {
                await this.api(`/archive/${item._type}/${item.id}/permanent`, { method: 'DELETE' });
                this.notify(window.ZenI18n.t('Element został trwale usunięty'));
                if (this.archivePreviewModal.open && this.archivePreviewModal.item?.id === item.id) {
                    this.closeArchivePreview();
                }
                await this.loadArchive();
            } catch (e) { this.notify(e.message); }
        },

        async emptyArchive() {
            if (!confirm(window.ZenI18n.t('Opróżnić CAŁE archiwum? Wszystkie elementy zostaną usunięte na zawsze.'))) return;
            try {
                const r = await this.api('/archive/empty', { method: 'POST' });
                this.notify(window.ZenI18n.t('Usunięto: ') + r.deleted);
                await this.loadArchive();
            } catch (e) { this.notify(e.message); }
        },


        // ═══════════════════════════════════════════════════════════
        // KALENDARZ – zadania + spotkania
        // ═══════════════════════════════════════════════════════════
        calendarEventsFor(day) {
            const dateStr = this.localDateKey(day.date);
            const events = [];

            if (this.calendarMode !== 'tasks') {
                for (const m of this.meetings) {
                    if (m.start_time && this.localDateKey(new Date(m.start_time)) === dateStr) {
                        events.push({
                            ...m, _type: 'meeting', _key: 'm-' + m.id,
                            _time: new Date(m.start_time).toLocaleTimeString(window.ZenI18n.locale,
                                {hour:'2-digit',minute:'2-digit'}),
                        });
                    }
                }
            }
            if (this.calendarMode !== 'meetings') {
                for (const t of this.tasks) {
                    if (t.due_date && this.localDateKey(new Date(t.due_date)) === dateStr) {
                        events.push({
                            ...t, _type: 'task', _key: 't-' + t.id,
                            _time: new Date(t.due_date).toLocaleTimeString(window.ZenI18n.locale,
                                {hour:'2-digit',minute:'2-digit'}),
                        });
                    }
                }
            }
            events.sort((a, b) => (a._time || '').localeCompare(b._time || ''));
            return events;
        },

        openTaskDetail(task) {
            // Otwiera detail view zadania
            this.openDetail('task', task.id);
        },

        // ═══════════════════════════════════════════════════════════
        // TASK ASSIGNEES (wielu wykonawców)
        // ═══════════════════════════════════════════════════════════
        // ═══════════════════════════════════════════════════════════
        // USTAWIENIA
        // ═══════════════════════════════════════════════════════════
        // ═══════════════════════════════════════════════════════════
        // INIT
        // ═══════════════════════════════════════════════════════════
    };
    // Preserve the original precedence: core, UX, then feature modules.
    for (const factory of [window.ZenCore.auth, window.ZenCore.navigation, window.ZenCore.lifecycle]) {
        Object.defineProperties(component, Object.getOwnPropertyDescriptors(factory()));
    }
    Object.defineProperties(component, Object.getOwnPropertyDescriptors(window.ZenUX));
    for (const factory of Object.values(window.ZenModules || {})) Object.defineProperties(component, Object.getOwnPropertyDescriptors(factory()));
    return component;
}

window.crmApp = crmApp;
