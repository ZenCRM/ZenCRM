/* Core component methods; composed before UX and feature modules. */
window.ZenCore = window.ZenCore || {};
window.ZenCore.navigation = function () { return {
        canAccessView(viewId) {
            if (!viewId) return true;
            if (viewId === 'settings') return this.user?.role === 'admin' || this.isAdmin;
            if (viewId === 'documentTypes') return this.user?.role === 'admin' || this.isAdmin;

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

            if (['users', 'documentTypes', 'portal_group', 'portalSettings', 'portalUsers', 'portalSpaces', 'portalTickets'].includes(viewId)) {
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
            if (this.currentView !== id) return;

            // Jeśli to widok leadów – policz widoczne kolumny po renderze
            if (id === 'leads') {
                this.$nextTick(() => {
                    this.recomputeVisibleCols();
                    this.$refs.kanbanCols?.scrollTo({ left: this.kanbanLeft, behavior: "instant" });
                });
            }
        },

        async reload() {
            const view = this.currentView;
            const requestId = this._reloadRequest = (this._reloadRequest || 0) + 1;
            this.listError = '';
            if (['portalSettings', 'portalUsers', 'portalTickets', 'portalSpaces'].includes(view)) return;
            if (view === 'dashboard') {
                await this.loadStats();
                if (requestId === this._reloadRequest && this.currentView === view) this.renderFunnel();
                return;
            }
            if (view === 'settings') {
                await this.loadSettings();
                return;
            }
            if (view === 'sms') {
                await this.loadSmsData();
                return;
            }
            if (view === 'archive') {
                await this.loadArchive();
                return;
            }
            if (view === 'notifications') {
                await Promise.all([
                    this.loadNotifications(),
                    this.loadAllReminders(),
                    this.loadReminders(),
                    (async () => { if (!this.projects?.length) { try { this.projects = await this.api('/projects'); } catch(_) {} } })()
                ]);
                return;
            }
            try {
                const data = view === 'clients' ? await this.loadClientOptions() : await this.api('/' + this.apiPath(view));
                if (requestId !== this._reloadRequest || this.currentView !== view) return;
                const list = Array.isArray(data)
                    ? data
                    : (data.clients || data.items || data.data || []);
                this[view] = list;
            } catch (e) {
                if (requestId !== this._reloadRequest || this.currentView !== view) return;
                console.error(e);
                this.listError = e.message;
            }

            if (view === 'leads') {
                try { this.boardTasks = await this.api('/tasks'); this.boardTasksLoaded = true; }
                catch (e) { this.boardTasksLoaded = false; this.notify(window.ZenI18n.t('Nie pobrano następnych działań: ') + e.message); }
                if (requestId !== this._reloadRequest || this.currentView !== view) return;
                this.$nextTick(() => this.recomputeVisibleCols());
            }

            if (view === 'tasks') {
                try { this.taskStatusStages = (await this.api('/tasks/board-settings')).stages; }
                catch (e) { this.listError = e.message; }
            }

            if (requestId !== this._reloadRequest || this.currentView !== view) return;
            if (view === 'meetings') {
                try { this.tasks = await this.api('/tasks'); }
                catch (e) { this.listError = window.ZenI18n.t('Nie pobrano zadań do kalendarza: ') + e.message; }
            }

            if (requestId !== this._reloadRequest || this.currentView !== view) return;
            if (view === 'users') {
                try { await this.loadTeams(); }
                catch (e) { console.warn('Nie pobrano zespołów:', e.message); }
                if (this.isAdmin) await this.loadPermissions();
            }

            if (requestId !== this._reloadRequest || this.currentView !== view) return;
            if (view === 'tickets') {
                if (this.teams.length === 0) {
                    try { await this.loadTeams(); } catch (_) {}
                }
                if (typeof this.loadTicketConfig === 'function') {
                    try { await this.loadTicketConfig(); } catch (_) {}
                }
            }

            // Klienci potrzebni do selectów i nazw
            if (requestId !== this._reloadRequest || this.currentView !== view) return;
            if (this.clients.length === 0 && view !== 'clients') {
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

            if (this.documentTypes.length === 0) {
                try { this.documentTypes = await this.api('/document-types'); } catch (_) {}
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

}; };
