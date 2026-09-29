/* ═══════════════════════════════════════════════════════════════
   ZenCRM – główny komponent Alpine.js
   Wymaga wcześniej załadowanych: config.js, helpers.js, api.js
   ═══════════════════════════════════════════════════════════════ */

function crmApp() {
    const component = Object.defineProperties({

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
        services: [], serviceCatalog: [], offers: [], documents: [], templates: [], users: [], contacts: [],
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
        password: { open: false, form: { new_password: '', confirm: '' }, error: '', success: '' },
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
            error: '',
        },
        generateModal: { open: false, type: 'document', item: null, templateId: '', custom: {}, error: '' },
        attachmentModal: { open: false, entity: '', recordId: null, files: [], busy: false, error: '' },

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
        async submitSetup() {
            this.setupError = '';
            const form = this.setupForm;
            if (!form.email || !form.email.includes('@')) {
                this.setupError = window.ZenI18n.t('Podaj poprawny adres e-mail');
                return;
            }
            if (!form.password || form.password.length < 8) {
                this.setupError = window.ZenI18n.t('Hasło musi mieć co najmniej 8 znaków');
                return;
            }
            if (form.password !== form.password_confirm) {
                this.setupError = window.ZenI18n.t('Hasła nie są identyczne');
                return;
            }
            this.setupLoading = true;
            try {
                const data = await window.ZenApi.setupAdmin({
                    first_name: form.first_name,
                    last_name: form.last_name,
                    email: form.email,
                    password: form.password
                });
                this.token = data.access_token;
                this.user = data.user;
                this.isAdmin = true;
                this.needsSetup = false;
                localStorage.setItem('token', this.token);
                localStorage.setItem('user', JSON.stringify(this.user));
                await this.init();
            } catch (e) {
                this.setupError = e.message;
            } finally {
                this.setupLoading = false;
            }
        },

        async login() {
            this.loginError = '';
            this.loginLoading = true;
            try {
                const data = await window.ZenApi.login(
                    this.loginForm.email, this.loginForm.password);
                this.token = data.access_token;
                this.user = data.user;
                this.isAdmin = (this.user?.role === 'admin');
                localStorage.setItem('token', this.token);
                localStorage.setItem('user', JSON.stringify(this.user));
                await this.init();
            } catch (e) {
                this.loginError = e.message;
            } finally {
                this.loginLoading = false;
            }
        },

        openForgotPassword() {
            this.forgotModal.code = '';
            this.forgotModal.password = '';
            this.forgotModal.awaitingCode = false;
            this.forgotModal.open = true;
            this.forgotModal.email = this.loginForm.email || '';
            this.forgotModal.loading = false;
            this.forgotModal.success = '';
            this.forgotModal.error = '';
        },

        async submitForgotPassword() {
            if (!this.forgotModal.email) {
                this.forgotModal.error = window.ZenI18n.t('Wpisz swój adres e-mail');
                return;
            }
            this.forgotModal.loading = true;
            this.forgotModal.error = '';
            this.forgotModal.success = '';
            try {
                const res = await window.ZenApi.forgotPassword(this.forgotModal.email);
                this.forgotModal.awaitingCode = true;
                this.forgotModal.success = window.ZenI18n.t(res.message || window.ZenI18n.t('Zgłoszenie zostało wysłane'));
            } catch (e) {
                this.forgotModal.error = e.message;
            } finally {
                this.forgotModal.loading = false;
            }
        },

        async confirmPasswordReset() {
            this.forgotModal.loading = true;
            this.forgotModal.error = '';
            try {
                const res = await window.ZenApi.request('/auth/reset-password', {
                    method: 'POST',
                    body: JSON.stringify({ token: this.forgotModal.code.trim(), password: this.forgotModal.password }),
                });
                this.forgotModal.success = res.message;
                this.forgotModal.awaitingCode = false;
                this.forgotModal.code = '';
                this.forgotModal.password = '';
            } catch (e) {
                this.forgotModal.error = e.message;
            } finally {
                this.forgotModal.loading = false;
            }
        },

        async logout() {
            await this.disablePush();
            this.stopNotifications();
            this.stopReminders();
            this.endLeadDrag();
            this.detailView.open = false;
            this.detailPanel = false;
            this.token = '';
            this.user = null;
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            this.settingsForm = {};
            await this.loadSettings(true);
            // Nie czyścimy lastView – po ponownym zalogowaniu wróci tam, gdzie byłeś
        },

        // ═══════════════════════════════════════════════════════════
        // API WRAPPER
        // ═══════════════════════════════════════════════════════════
        api(path, options = {}) {
            return window.ZenApi.request(path, options, this.token, () => this.logout());
        },

        // ═══════════════════════════════════════════════════════════
        // NAVIGACJA
        // ═══════════════════════════════════════════════════════════
        canAccessView(viewId) {
            if (!viewId) return true;
            if (viewId === 'settings') return this.user?.role === 'admin' || this.isAdmin;

            let perms = {};
            try {
                if (this.settingsForm?.menu_permissions) {
                    perms = typeof this.settingsForm.menu_permissions === 'string'
                        ? JSON.parse(this.settingsForm.menu_permissions)
                        : this.settingsForm.menu_permissions;
                }
            } catch (_) {}

            const cfg = perms[viewId];
            if (cfg) {
                if (cfg.enabled === false) return false;
                const role = cfg.role || 'all';
                if (role === 'admin') return this.user?.role === 'admin' || this.isAdmin;
                if (role === 'manager') return this.user?.role === 'admin' || this.user?.role === 'manager' || this.isAdmin;
                if (role === 'all') return true;
            }

            if (['users', 'portal_group', 'portalSettings', 'portalUsers', 'portalSpaces', 'portalTickets'].includes(viewId)) {
                return this.user?.role === 'admin' || this.isAdmin;
            }
            return true;
        },

        get visibleMenu() {
            return (this.menu || []).map(item => {
                if (item.children) {
                    const visibleChildren = item.children.filter(c => this.canAccessView(c.id));
                    if (!visibleChildren.length) return null;
                    if (!this.canAccessView(item.id)) return null;
                    return { ...item, children: visibleChildren };
                }
                if (!this.canAccessView(item.id)) return null;
                return item;
            }).filter(Boolean);
        },

        isKnownView(id) {
            if (!id) return false;
            for (const item of this.menu) {
                if (item.id === id) return true;
                if (item.children && item.children.some(c => c.id === id)) return true;
            }
            return false;
        },

        async selectView(id, skipReload = false) {
            if (!id) id = 'dashboard';
            const ticketSettingsSelected = id === 'ticketSettings';
            // Sprawdź, czy to znany widok
            const valid = this.isKnownView(id);
            if (!valid) id = 'dashboard';

            // Sprawdź uprawnienia do widoku w menu
            if (!this.canAccessView(id)) {
                if (id !== 'dashboard') {
                    this.notify(window.ZenI18n.t('Brak dostępu do tego modułu'));
                }
                id = 'dashboard';
            }
            // Zamknij detail view przy zmianie modułu
            if (this.detailView && this.detailView.open) this.detailView.open = false;

            if (id === 'ticketSettings') {
                this.settingsTab = 'helpdesk';
                this.openMenuGroups.tickets_group = true;
                id = 'settings';
                if (typeof this.loadHelpdeskSettings === 'function') {
                    try { await this.loadHelpdeskSettings(); } catch (_) {}
                }
            }

            // Po zmianie widoku pozostaw otwartą tylko jego grupę.
            for (const key of Object.keys(this.openMenuGroups)) this.openMenuGroups[key] = false;
            if (ticketSettingsSelected) this.openMenuGroups.tickets_group = true;
            for (const item of this.menu) {
                if (item.children && item.children.some(c => c.id === id && c.id !== 'ticketSettings')) {
                    this.openMenuGroups[item.id] = true;
                }
            }

            this.currentView = id;
            if (window.innerWidth < 1024) this.sidebarOpen = false;

            // Zapisz do URL hash i localStorage
            if (location.hash !== '#' + id) {
                history.replaceState(null, '', '#' + id);
            }
            localStorage.setItem('lastView', id);

            if (!skipReload) await this.reload();

            // Jeśli to widok leadów – policz widoczne kolumny po renderze
            if (id === 'leads') {
                this.$nextTick(() => {
                    this.recomputeVisibleCols();
                    this.$refs.kanbanCols?.scrollTo({ left: this.kanbanLeft, behavior: "instant" });
                });
            }
        },

        async reload() {
            this.listError = '';
            if (['portalSettings', 'portalUsers', 'portalTickets', 'portalSpaces'].includes(this.currentView)) return;
            if (this.currentView === 'dashboard') {
                await this.loadStats();
                this.renderFunnel();
                return;
            }
            if (this.currentView === 'settings') {
                await this.loadSettings();
                return;
            }
            if (this.currentView === 'sms') {
                await this.loadSmsData();
                return;
            }
            if (this.currentView === 'archive') {
                await this.loadArchive();
                return;
            }
            if (this.currentView === 'notifications') {
                await Promise.all([
                    this.loadNotifications(),
                    this.loadAllReminders(),
                    this.loadReminders(),
                    (async () => { if (!this.projects?.length) { try { this.projects = await this.api('/projects'); } catch(_) {} } })()
                ]);
                return;
            }
            try {
                const data = this.currentView === 'clients' ? await this.loadClientOptions() : await this.api('/' + this.apiPath(this.currentView));
                const list = Array.isArray(data)
                    ? data
                    : (data.clients || data.items || data.data || []);
                this[this.currentView] = list;
            } catch (e) {
                console.error(e);
                this.listError = e.message;
            }

            if (this.currentView === 'leads') {
                try { this.boardTasks = await this.api('/tasks'); this.boardTasksLoaded = true; }
                catch (e) { this.boardTasksLoaded = false; this.notify(window.ZenI18n.t('Nie pobrano następnych działań: ') + e.message); }
                this.$nextTick(() => this.recomputeVisibleCols());
            }

            if (this.currentView === 'tasks') {
                try { this.taskStatusStages = (await this.api('/tasks/board-settings')).stages; }
                catch (e) { this.listError = e.message; }
            }

            if (this.currentView === 'meetings') {
                try { this.tasks = await this.api('/tasks'); }
                catch (e) { this.listError = window.ZenI18n.t('Nie pobrano zadań do kalendarza: ') + e.message; }
            }

            if (this.currentView === 'users') {
                try { await this.loadTeams(); }
                catch (e) { console.warn('Nie pobrano zespołów:', e.message); }
                if (this.isAdmin) await this.loadPermissions();
            }

            if (this.currentView === 'tickets') {
                if (this.teams.length === 0) {
                    try { await this.loadTeams(); } catch (_) {}
                }
                if (typeof this.loadTicketConfig === 'function') {
                    try { await this.loadTicketConfig(); } catch (_) {}
                }
            }

            // Klienci potrzebni do selectów i nazw
            if (this.clients.length === 0 && this.currentView !== 'clients') {
                try {
                    const c = await this.loadClientOptions();
                    this.clients = Array.isArray(c) ? c : (c.clients || []);
                } catch (_) {}
            }

            // Załaduj szablony (dla dropdownów w ofertach/dokumentach)
            if (this.templates.length === 0) {
                try {
                    this.templates = await this.api('/templates');
                } catch (_) {}
            }

            // Załaduj listę użytkowników (dla assignee_id)
            if (this.users.length === 0) {
                try {
                    this.users = await this.api('/users');
                } catch (_) {}
            }
        },

        // ═══════════════════════════════════════════════════════════
        // STATS / DASHBOARD
        // ═══════════════════════════════════════════════════════════
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
        docTypeLabel(t)     { return window.ZenHelpers.docTypeLabel(t); },
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
        },
        nextMonth() {
            this.calendarDate = new Date(this.calendarDate.getFullYear(),
                                         this.calendarDate.getMonth() + 1, 1);
        },

        // ═══════════════════════════════════════════════════════════
        // PROFIL
        // ═══════════════════════════════════════════════════════════
        openProfile() {
            const notifs = this.user?.email_notifications || {};
            this.profile.form = {
                first_name: this.user?.first_name || '',
                last_name:  this.user?.last_name  || '',
                email:      this.user?.email      || '',
                avatar_url: this.user?.avatar_url || '',
                default_call_method: this.user?.default_call_method || 'link',
                email_notifications: {
                    ticket_assigned: notifs.ticket_assigned !== false,
                    ticket_reply: notifs.ticket_reply !== false,
                    task_assigned: notifs.task_assigned !== false,
                    client_assigned: notifs.client_assigned !== false,
                },
            };
            this.profile.error = '';
            this.profile.success = '';
            this.avatarTs = Date.now();
            this.profile.open = true;
        },

        async saveProfile() {
            this.profile.error = '';
            this.profile.success = '';
            try {
                await this.api(`/users/${this.user.id}`, {
                    method: 'PUT', body: JSON.stringify(this.profile.form),
                });
                this.user = { ...this.user, ...this.profile.form };
                localStorage.setItem('user', JSON.stringify(this.user));
                this.profile.success = window.ZenI18n.t('Profil zapisany');
                setTimeout(() => { this.profile.open = false; }, 800);
            } catch (e) { this.profile.error = e.message; }
        },

        // ═══════════════════════════════════════════════════════════
        // ZMIANA HASŁA
        // ═══════════════════════════════════════════════════════════
        openPassword() {
            this.password.form = { new_password: '', confirm: '' };
            this.password.error = '';
            this.password.success = '';
            this.password.open = true;
        },

        async savePassword() {
            this.password.error = '';
            this.password.success = '';
            if (this.password.form.new_password !== this.password.form.confirm) {
                this.password.error = window.ZenI18n.t('Hasła nie są identyczne');
                return;
            }
            if (this.password.form.new_password.length < 6) {
                this.password.error = window.ZenI18n.t('Hasło musi mieć min. 6 znaków');
                return;
            }
            try {
                await this.api(`/users/${this.user.id}`, {
                    method: 'PUT',
                    body: JSON.stringify({ password: this.password.form.new_password }),
                });
                this.password.success = window.ZenI18n.t('Hasło zmienione');
                setTimeout(() => { this.password.open = false; }, 800);
            } catch (e) { this.password.error = e.message; }
        },


        // ═══════════════════════════════════════════════════════════
        // KANBAN – NAWIGACJA (bez brzydkiego scrolla)
        // ═══════════════════════════════════════════════════════════
        // ═══════════════════════════════════════════════════════════
        // DETAIL VIEW – Klient / Lead
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

        async handleHashChange() {
            if (!this.token) return;
            const hashRaw = location.hash.replace('#', '');
            if (!hashRaw) return;

            const detailMatch = hashRaw.match(/^(client|lead|service|task|project|ticket)\/(\d+)$/);
            if (detailMatch) {
                const type = detailMatch[1];
                const id = parseInt(detailMatch[2], 10);
                if (type === 'project') {
                    if (this.currentView !== 'projects') this.currentView = 'projects';
                    if (!this.activeProject || this.activeProject.id !== id) {
                        await this.openProject(id, true);
                    }
                } else if (type === 'ticket') {
                    if (this.currentView !== 'tickets') this.currentView = 'tickets';
                    if (!this.ticketDrawer?.open || this.ticketDrawer?.ticket?.id !== id) {
                        await this.openTicketDetails(id, true);
                    }
                } else {
                    const viewMap = { client: 'clients', lead: 'leads', service: 'services', task: 'tasks' };
                    if (viewMap[type] && this.currentView !== viewMap[type]) {
                        this.currentView = viewMap[type];
                    }
                    if (!this.detailView?.open || this.detailView?.id !== id || this.detailView?.type !== type) {
                        await this.openDetail(type, id, true);
                    }
                }
                return;
            }

            if (this.detailView?.open && !hashRaw.includes('/')) {
                this.detailView.open = false;
            }
            if (this.activeProject && hashRaw === 'projects') {
                this.closeProject(true);
            }
            if (this.ticketDrawer?.open && hashRaw === 'tickets') {
                this.closeTicketDrawer(true);
            }

            if (this.isKnownView(hashRaw) && this.currentView !== hashRaw) {
                this.selectView(hashRaw);
            }
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
        async init() {
            this.startNotifications();
            this.startReminders();
            this.initPush();
            this.$watch('user', (v) => {
                this.isAdmin = (v?.role === 'admin');
            }, { deep: true });
            this.$watch('darkMode', v => {
                if (this.currentView === 'dashboard') this.$nextTick(() => this.renderFunnel());
                localStorage.setItem('darkMode', v);
                this.applyTheme();
            });

            // Załaduj ustawienia publiczne (motyw logowania, sidebar, favicon)
            await this.loadSettings(true);
            if (this.token) await this.loadMyPermissions();

            const updateLayout = () => { this.sidebarOpen = window.innerWidth >= 1024; };
            updateLayout();
            window.addEventListener('resize', updateLayout);

            // Oblicz widoczne kolumny po zmianie rozmiaru i po wejściu w widok
            this._kanbanResizeHandler = () => {
                if (this.currentView === 'leads') {
                    this.$nextTick(() => this.recomputeVisibleCols());
                }
            };
            window.addEventListener('resize', this._kanbanResizeHandler);

            // Nasłuchuj zmian hash (dla back/forward)
            window.addEventListener('hashchange', () => this.handleHashChange());

            if (this.token) {
                if (typeof this.loadSmsDevices === 'function') {
                    this.loadSmsDevices();
                }
                try {
                    const tList = await this.api('/tickets');
                    if (Array.isArray(tList)) {
                        this.tickets = tList;
                    }
                } catch (_) {}
                try {
                    // ── NAJPIERW: sprawdź, czy hash wskazuje na link do rekordu/obiektu ──
                    const hashRaw = location.hash.replace('#', '');
                    const detailMatch = hashRaw.match(/^(client|lead|service|task|project|ticket)\/(\d+)$/);

                    if (detailMatch) {
                        const type = detailMatch[1];
                        const id = parseInt(detailMatch[2], 10);
                        if (type === 'project') {
                            this.currentView = 'projects';
                            localStorage.setItem('lastView', 'projects');
                            await this.openProject(id, true);
                        } else if (type === 'ticket') {
                            this.currentView = 'tickets';
                            localStorage.setItem('lastView', 'tickets');
                            await this.openTicketDetails(id, true);
                        } else {
                            const viewMap = { client: 'clients', lead: 'leads', service: 'services', task: 'tasks' };
                            this.currentView = viewMap[type] || 'leads';
                            localStorage.setItem('lastView', this.currentView);
                            await this.openDetail(type, id, true); // skipHash = true
                        }
                    } else {
                        // Zwykły widok z hash / localStorage
                        const savedView = hashRaw
                                         || localStorage.getItem('lastView')
                                         || 'dashboard';
                        let validView = this.isKnownView(savedView)
                                         ? savedView : 'dashboard';

                        if (validView === 'ticketSettings') {
                            this.settingsTab = 'helpdesk';
                            this.openMenuGroups.tickets_group = true;
                            validView = 'settings';
                            if (typeof this.loadHelpdeskSettings === 'function') {
                                try { await this.loadHelpdeskSettings(); } catch (_) {}
                            }
                        }

                        for (const item of this.menu) {
                            if (item.children && item.children.some(c => c.id === validView || (c.id === 'ticketSettings' && this.settingsTab === 'helpdesk'))) {
                                this.openMenuGroups[item.id] = true;
                            }
                        }

                        this.currentView = validView;
                        if (location.hash !== '#' + validView) {
                            history.replaceState(null, '', '#' + validView);
                        }
                        localStorage.setItem('lastView', validView);

                        // Załaduj dane dla aktywnego widoku
                        if (validView === 'dashboard') {
                            await this.loadStats();
                            await this.renderFunnel();
                        } else {
                            await this.reload();
                        }
                    }
                } catch (e) {
                    console.warn(window.ZenI18n.t('Błąd inicjalizacji:'), e.message);
                }
            }
        },
    }, Object.getOwnPropertyDescriptors(window.ZenUX));
    for (const factory of Object.values(window.ZenModules || {})) Object.defineProperties(component, Object.getOwnPropertyDescriptors(factory()));
    return component;
}

window.crmApp = crmApp;
