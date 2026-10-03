/* Core component methods; composed before UX and feature modules. */
window.ZenCore = window.ZenCore || {};
window.ZenCore.lifecycle = function () { return {
        async init() {
            if (this.token) {
                try {
                    const catalog = await this.api('/translations/catalog');
                    const serialized = JSON.stringify(catalog);
                    if (sessionStorage.getItem('zen-i18n-catalog') !== serialized) {
                        sessionStorage.setItem('zen-i18n-catalog', serialized);
                        location.reload();
                        return;
                    }
                    window.ZenCustomI18n = catalog;
                } catch (e) { console.warn('Nie pobrano tłumaczeń:', e.message); }
            }
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
}; };
