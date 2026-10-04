window.ZenModules = window.ZenModules || {};
window.ZenModules.tickets = function () {
    return {
        tickets: [],
        ticketSearch: '',
        ticketFilter: '',
        ticketCategoryFilter: '',
        ticketPriorityFilter: '',
        ticketAssigneeFilter: '',
        ticketTeamFilter: '',
        ticketCategories: [],
        ticketConfig: null,
        ticketDrawer: {
            open: false,
            ticket: null,
            loading: false,
            replyContent: '',
            isInternal: false,
            savingReply: false,
            error: ''
        },
        ticketModal: {
            open: false,
            editingId: null,
            form: {
                title: '',
                client_id: '',
                contact_name: '',
                contact_email: '',
                contact_phone: '',
                category: 'general',
                priority: 'medium',
                status: 'new',
                assignee_id: '',
                team_id: '',
                description: ''
            },
            error: '',
            saving: false
        },

        ticketStatusLabel(status) {
            return {
                new: window.ZenI18n.t('Nowy'),
                open: window.ZenI18n.t('W toku'),
                pending_client: window.ZenI18n.t('Oczekuje na klienta'),
                resolved: window.ZenI18n.t('Rozwiązany'),
                closed: window.ZenI18n.t('Zamknięty')
            }[status] || status || '—';
        },

        ticketStatusClass(status) {
            return {
                new: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
                open: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
                pending_client: 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300',
                resolved: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
                closed: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
            }[status] || 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300';
        },

        ticketPriorityLabel(p) {
            return {
                low: window.ZenI18n.t('Niski'),
                medium: window.ZenI18n.t('Średni'),
                high: window.ZenI18n.t('Wysoki'),
                urgent: window.ZenI18n.t('Pilny')
            }[p] || p || '—';
        },

        ticketPriorityClass(p) {
            return {
                low: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
                medium: 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300',
                high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
                urgent: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'
            }[p] || 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300';
        },

        ticketCategoryLabel(catId) {
            if (!catId) return '—';
            const found = (this.ticketCategories || []).find(c => c.id === catId);
            if (found) return found.name;
            const defaults = {
                technical: window.ZenI18n.t('Pomoc techniczna'),
                billing: window.ZenI18n.t('Rozliczenia i faktury'),
                bug: window.ZenI18n.t('Zgłoszenie błędu'),
                general: window.ZenI18n.t('Zapytanie ogólne')
            };
            return defaults[catId] || catId;
        },

        get filteredTickets() {
            let list = this.tickets || [];
            if (this.ticketFilter) {
                list = list.filter(t => t.status === this.ticketFilter);
            }
            if (this.ticketCategoryFilter) {
                list = list.filter(t => t.category === this.ticketCategoryFilter);
            }
            if (this.ticketPriorityFilter) {
                list = list.filter(t => t.priority === this.ticketPriorityFilter);
            }
            if (this.ticketAssigneeFilter) {
                list = list.filter(t => String(t.assignee_id) === String(this.ticketAssigneeFilter));
            }
            if (this.ticketTeamFilter) {
                list = list.filter(t => String(t.team_id) === String(this.ticketTeamFilter));
            }
            if (this.ticketSearch) {
                const q = this.ticketSearch.toLowerCase();
                list = list.filter(t =>
                    (t.ticket_number || '').toLowerCase().includes(q) ||
                    (t.title || '').toLowerCase().includes(q) ||
                    (t.contact_name || '').toLowerCase().includes(q) ||
                    (t.contact_email || '').toLowerCase().includes(q) ||
                    (t.description || '').toLowerCase().includes(q)
                );
            }
            return list;
        },

        get ticketStats() {
            const all = this.tickets || [];
            return {
                all: all.length,
                new: all.filter(t => t.status === 'new').length,
                open: all.filter(t => t.status === 'open' || t.status === 'pending_client').length,
                resolved: all.filter(t => t.status === 'resolved' || t.status === 'closed').length
            };
        },

        get activeTicketsCount() {
            const all = this.tickets || [];
            return all.filter(t => t.status && !['resolved', 'closed'].includes(t.status)).length;
        },

        async loadTicketConfig() {
            try {
                const conf = await this.api('/tickets/settings');
                this.ticketConfig = conf;
                const defaults = {technical: 'Pomoc techniczna', billing: 'Rozliczenia i faktury', bug: 'Zgłoszenie błędu', general: 'Zapytanie ogólne'};
                this.ticketCategories = (conf.helpdesk_categories || []).map(category => ({...category,
                    name: category.name === defaults[category.id] ? window.ZenI18n.t(category.name) : category.name}));
            } catch (e) {
                console.warn('Nie udało się załadować konfiguracji ticketów:', e.message);
            }
        },

        openNewTicketModal(defaults = {}) {
            let defClient = '';
            let defName = '';
            let defEmail = '';
            let defPhone = '';
            if (defaults.client_id) {
                defClient = defaults.client_id;
                const c = (this.clients || []).find(item => item.id == defaults.client_id);
                if (c) {
                    defName = c.name || '';
                    defEmail = c.email || '';
                    defPhone = c.phone || '';
                }
            }
            this.ticketModal = {
                open: true,
                editingId: defaults.id || null,
                form: {
                    title: defaults.title || '',
                    client_id: defClient || '',
                    contact_name: defaults.contact_name || defName,
                    contact_email: defaults.contact_email || defEmail,
                    contact_phone: defaults.contact_phone || defPhone,
                    category: defaults.category || 'general',
                    priority: defaults.priority || 'medium',
                    status: defaults.status || 'new',
                    assignee_id: defaults.assignee_id || '',
                    team_id: defaults.team_id || '',
                    description: defaults.description || ''
                },
                error: '',
                saving: false
            };
        },

        closeNewTicketModal() {
            this.ticketModal.open = false;
        },

        async onTicketClientSelect(clientId) {
            if (!clientId) return;
            const c = (this.clients || []).find(item => item.id == clientId);
            if (c) {
                if (!this.ticketModal.form.contact_name) this.ticketModal.form.contact_name = c.name || '';
                if (!this.ticketModal.form.contact_email) this.ticketModal.form.contact_email = c.email || '';
                if (!this.ticketModal.form.contact_phone) this.ticketModal.form.contact_phone = c.phone || '';
                if (!this.ticketModal.form.assignee_id && c.assignee_id) this.ticketModal.form.assignee_id = c.assignee_id;
            }
        },

        async saveNewTicket() {
            const form = this.ticketModal.form;
            if (!form.title || !form.title.trim()) {
                this.ticketModal.error = window.ZenI18n.t('Tytuł ticketu jest wymagany');
                return;
            }
            this.ticketModal.saving = true;
            this.ticketModal.error = '';

            const payload = {
                title: form.title.trim(),
                client_id: form.client_id ? Number(form.client_id) : null,
                contact_name: form.contact_name?.trim() || null,
                contact_email: form.contact_email?.trim() || null,
                contact_phone: form.contact_phone?.trim() || null,
                category: form.category || 'general',
                priority: form.priority || 'medium',
                status: form.status || 'new',
                assignee_id: form.assignee_id ? Number(form.assignee_id) : null,
                team_id: form.team_id ? Number(form.team_id) : null,
                description: form.description?.trim() || null
            };

            try {
                if (this.ticketModal.editingId) {
                    const updated = await this.api(`/tickets/${this.ticketModal.editingId}`, {
                        method: 'PUT',
                        body: JSON.stringify(payload)
                    });
                    const idx = this.tickets.findIndex(t => t.id === updated.id);
                    if (idx !== -1) this.tickets[idx] = updated;
                    if (this.ticketDrawer.ticket?.id === updated.id) this.ticketDrawer.ticket = updated;
                } else {
                    const created = await this.api('/tickets', {
                        method: 'POST',
                        body: JSON.stringify(payload)
                    });
                    this.tickets.unshift(created);
                    if (this.detailView?.open && this.detailView?.type === 'client' && this.detailView?.id == created.client_id) {
                        this.detailView.clientTickets = this.detailView.clientTickets || [];
                        this.detailView.clientTickets.unshift(created);
                    }
                }
                this.ticketModal.open = false;
                this.notify(window.ZenI18n.t('Zapisano ticket'));
            } catch (e) {
                this.ticketModal.error = e.message;
            } finally {
                this.ticketModal.saving = false;
            }
        },

        async openTicketDetails(ticket, skipHash = false) {
            const ticketId = typeof ticket === 'object' ? ticket.id : ticket;
            if (!ticketId) return;
            this.ticketDrawer.open = true;
            this.ticketDrawer.loading = true;
            this.ticketDrawer.error = '';
            this.ticketDrawer.replyContent = '';
            this.ticketDrawer.isInternal = false;
            this.ticketDrawer.ticket = typeof ticket === 'object' ? ticket : { id: ticketId };

            if (!skipHash) {
                const newHash = '#ticket/' + ticketId;
                if (location.hash !== newHash) {
                    history.pushState(null, '', newHash);
                }
            }

            try {
                const fullTicket = await this.api(`/tickets/${ticketId}`);
                this.ticketDrawer.ticket = fullTicket;
                // zaktualizuj na liście
                const idx = (this.tickets || []).findIndex(t => t.id === fullTicket.id);
                if (idx !== -1) this.tickets[idx] = fullTicket;
            } catch (e) {
                this.ticketDrawer.error = e.message;
            } finally {
                this.ticketDrawer.loading = false;
            }
        },

        closeTicketDrawer(skipHash = false) {
            this.ticketDrawer.open = false;
            if (!skipHash && location.hash.startsWith('#ticket/')) {
                history.pushState(null, '', '#tickets');
            }
        },

        async changeTicketStatus(ticket, newStatus) {
            if (!ticket || ticket.status === newStatus) return;
            try {
                const updated = await this.api(`/tickets/${ticket.id}`, {
                    method: 'PUT',
                    body: JSON.stringify({ status: newStatus })
                });
                ticket.status = updated.status;
                const idx = this.tickets.findIndex(t => t.id === ticket.id);
                if (idx !== -1) this.tickets[idx].status = updated.status;
                if (this.detailView?.clientTickets) {
                    const cIdx = this.detailView.clientTickets.findIndex(t => t.id === ticket.id);
                    if (cIdx !== -1) this.detailView.clientTickets[cIdx].status = updated.status;
                }
                this.notify(window.ZenI18n.t('Zmieniono status ticketu'));
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            }
        },

        async changeTicketPriority(ticket, newPriority) {
            if (!ticket || ticket.priority === newPriority) return;
            try {
                const updated = await this.api(`/tickets/${ticket.id}`, {
                    method: 'PUT',
                    body: JSON.stringify({ priority: newPriority })
                });
                ticket.priority = updated.priority;
                const idx = this.tickets.findIndex(t => t.id === ticket.id);
                if (idx !== -1) this.tickets[idx].priority = updated.priority;
                this.notify(window.ZenI18n.t('Zmieniono priorytet'));
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            }
        },

        async changeTicketAssignee(ticket, assigneeId) {
            if (!ticket) return;
            const parsedId = assigneeId ? Number(assigneeId) : null;
            try {
                const updated = await this.api(`/tickets/${ticket.id}`, {
                    method: 'PUT',
                    body: JSON.stringify({ assignee_id: parsedId })
                });
                ticket.assignee_id = updated.assignee_id;
                ticket.assignee_name = updated.assignee_name;
                const idx = this.tickets.findIndex(t => t.id === ticket.id);
                if (idx !== -1) {
                    this.tickets[idx].assignee_id = updated.assignee_id;
                    this.tickets[idx].assignee_name = updated.assignee_name;
                }
                this.notify(window.ZenI18n.t('Zmieniono opiekuna'));
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            }
        },

        async changeTicketTeam(ticket, teamId) {
            if (!ticket) return;
            const parsedId = teamId ? Number(teamId) : null;
            try {
                const updated = await this.api(`/tickets/${ticket.id}`, {
                    method: 'PUT',
                    body: JSON.stringify({ team_id: parsedId })
                });
                ticket.team_id = updated.team_id;
                ticket.team_name = updated.team_name;
                const idx = this.tickets.findIndex(t => t.id === ticket.id);
                if (idx !== -1) {
                    this.tickets[idx].team_id = updated.team_id;
                    this.tickets[idx].team_name = updated.team_name;
                }
                this.notify(window.ZenI18n.t('Zmieniono zespół'));
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            }
        },

        async sendTicketReply() {
            const drawer = this.ticketDrawer;
            if (!drawer.ticket || !drawer.replyContent || !drawer.replyContent.trim()) return;

            drawer.savingReply = true;
            drawer.error = '';

            try {
                const msg = await this.api(`/tickets/${drawer.ticket.id}/messages`, {
                    method: 'POST',
                    body: JSON.stringify({
                        content: drawer.replyContent.trim(),
                        is_internal: drawer.isInternal
                    })
                });
                drawer.ticket.messages = drawer.ticket.messages || [];
                drawer.ticket.messages.push(msg);

                if (!drawer.isInternal && ['new', 'open'].includes(drawer.ticket.status)) {
                    drawer.ticket.status = 'pending_client';
                    const idx = this.tickets.findIndex(t => t.id === drawer.ticket.id);
                    if (idx !== -1) this.tickets[idx].status = 'pending_client';
                }

                drawer.replyContent = '';
                this.notify(drawer.isInternal ? window.ZenI18n.t('Zapisano notatkę') : window.ZenI18n.t('Wysłano odpowiedź do klienta'));
            } catch (e) {
                drawer.error = e.message;
            } finally {
                drawer.savingReply = false;
            }
        },

        async deleteTicket(ticketId) {
            if (!confirm(window.ZenI18n.t('Czy na pewno chcesz usunąć ten ticket?'))) return;
            try {
                await this.api(`/tickets/${ticketId}`, { method: 'DELETE' });
                this.tickets = this.tickets.filter(t => t.id !== ticketId);
                if (this.detailView?.clientTickets) {
                    this.detailView.clientTickets = this.detailView.clientTickets.filter(t => t.id !== ticketId);
                }
                if (this.ticketDrawer.ticket?.id === ticketId) {
                    this.ticketDrawer.open = false;
                }
                this.notify(window.ZenI18n.t('Ticket został usunięty'));
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            }
        },

        getTicketTrackingUrl(token) {
            const helpdeskPath = this.ticketConfig?.helpdesk_path || '/pomoc';
            return `${(this.settingsForm?.crm_base_url || window.location.origin)}${helpdeskPath}?ticket=${encodeURIComponent(token || '')}`;
        },

        copyTrackingLink(token) {
            if (!token) return;
            const url = this.getTicketTrackingUrl(token);
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(url).then(() => {
                    this.notify(window.ZenI18n.t('Skopiowano link do schowka'));
                }).catch(() => {
                    prompt(window.ZenI18n.t('Skopiuj link:'), url);
                });
            } else {
                prompt(window.ZenI18n.t('Skopiuj link:'), url);
            }
        }
    };
};
