window.ZenModules = window.ZenModules || {};
window.ZenModules.details = function () { return {
        async openDetail(type, id, skipHash = false) {
            if (Date.now() - this.lastDragEnd < 300) return;
            if (this.detailView.newComment?.trim() && !confirm(window.ZenI18n.t('Odrzucić niezapisany komentarz?'))) return;
            if (this.settingsForm?.ui_template === 'modern') this.chooseModernHeroBackground();
            if (!this.detailView.open) { this.returnScroll = document.querySelector('main')?.scrollTop || 0; this.returnFocus = document.activeElement; }
            this.detailPanel = this.settingsForm?.ui_template === 'modern' ? false : this.settingsForm?.['ui_detail_' + type] !== 'full';
            this.detailError = '';
            this.detailView = {
                open: true,
                type: type,
                id: id,
                data: null,
                tab: 'overview',
                contacts: [],
                tasks: [],
                documents: [],
                comments: [],
                activities: [],
                team: [],
                clientServices: [],
                clientLeads: [],
                clientTickets: [],
                customFields: [],
                newComment: '',
                loading: true,
            };
            if (!skipHash) {
                const newHash = '#' + type + '/' + id;
                if (location.hash !== newHash) {
                    history.pushState(null, '', newHash);
                }
            }
            await this.loadDetail();
            this.$nextTick(() => document.querySelector('.ux-detail-panel .ux-panel-close')?.focus());
        },

        closeDetail() {
            if (this.detailView.newComment?.trim() && !confirm(window.ZenI18n.t('Odrzucić niezapisany komentarz?'))) return;
            this.detailView.open = false;
            this.detailView.id = null;
            this.detailView.data = null;
            // Wróć do listy
            const v = this.currentView || 'dashboard';
            if (location.hash !== '#' + v) {
                history.replaceState(null, '', '#' + v);
            }
            this.reload().then(() => this.$nextTick(() => {
                this.$refs.kanbanCols?.scrollTo({ left: this.kanbanLeft, behavior: 'instant' });
                document.querySelector('main')?.scrollTo({ top: this.returnScroll, behavior: 'instant' });
                this.recomputeVisibleCols();
                this.returnFocus?.focus({ preventScroll: true });
            }));
        },

        async loadDetail() {
            const view = this.detailView;
            this.detailError = '';
            view.loading = true;
            const t = view.type;
            const id = view.id;

            // ── ZADANIE: dedykowany endpoint ──
            if (t === 'task') {
                try {
                    const data = await this.api(`/tasks/${id}/detail`);
                    view.data = data;
                    view.tasks = [];
                    view.documents = [];
                    view.comments = data.comments || [];
                    view.activities = data.activities || [];
                    view.team = data.assignees_detailed || [];
                    view.contacts = [];
                } catch (e) {
                    if (this.detailView === view) this.detailError = e.message;
                } finally {
                    view.loading = false;
                }
                return;
            }

            // ── USŁUGA: dedykowany endpoint zwraca wszystko ──
            if (t === 'service') {
                try {
                    const data = await this.api(`/services/${id}/detail`);
                    view.data = data;
                    view.tasks = data.tasks || [];
                    view.documents = data.documents || [];
                    view.comments = data.comments || [];
                    view.activities = data.activities || [];
                    view.team = data.team || [];
                    view.contacts = [];
                } catch (e) {
                    if (this.detailView === view) this.detailError = e.message;
                } finally {
                    view.loading = false;
                }
                return;
            }

            // ── KLIENT / LEAD: klasyczna logika ──
            const entityParam = t;
            const ep = t === 'client' ? 'clients' : 'leads';

            try {
                const [data, contacts, tasks, documents, comments, activities] = await Promise.all([
                    this.api(`/${ep}/${id}`),
                    this.api(`/contacts?${entityParam}_id=${id}`),
                    this.api(`/tasks?${entityParam}_id=${id}`),
                    this.api(`/documents?${entityParam}_id=${id}`),
                    this.api(`/comments?entity_type=${entityParam}&entity_id=${id}`),
                    this.api(`/activities?entity_type=${entityParam}&entity_id=${id}`),
                ]);

                view.data = data;
                view.contacts = contacts || [];
                view.tasks = tasks || [];
                view.documents = documents || [];
                view.comments = comments || [];
                view.activities = activities || [];
                view.team = [];

                // Jesli klient – zaladuj jego uslugi i leady
                if (t === 'client') {
                    try {
                        view.clientServices = await this.api(`/services?client_id=${id}`);
                    } catch (_) {
                        view.clientServices = [];
                    }
                    try {
                        view.clientLeads = await this.api(`/leads?client_id=${id}`);
                    } catch (_) {
                        view.clientLeads = [];
                    }
                    try {
                        view.clientTickets = await this.api(`/tickets?client_id=${id}`);
                    } catch (_) {
                        view.clientTickets = [];
                    }
                } else {
                    view.clientServices = [];
                    view.clientLeads = [];
                    view.clientTickets = [];
                }

                if (typeof this.loadEntityTelephony === 'function') {
                    this.loadEntityTelephony(t, id, data?.phone);
                }

                // Wczytaj pola własne dla rekordu
                try {
                    const entityMap = { client: 'clients', lead: 'leads', task: 'tasks', service: 'services', contact: 'contacts' };
                    const entityName = entityMap[t] || t;
                    const allDefs = await this.api('/custom-fields');
                    const relFields = (allDefs || []).filter(f => f.entity === entityName);
                    if (relFields.length > 0) {
                        const valMap = await this.api(`/custom-fields/${entityName}/${id}`).catch(() => ({}));
                        view.customFields = relFields.map(f => ({
                            id: f.id,
                            label: f.label,
                            kind: f.kind,
                            value: (valMap && valMap[f.id] !== undefined) ? valMap[f.id] : ''
                        }));
                    } else {
                        view.customFields = [];
                    }
                } catch (_) {
                    view.customFields = [];
                }
            } catch (e) {
                if (this.detailView === view) this.detailError = e.message;
            } finally {
                view.loading = false;
            }
        },

        async addComment() {
            const text = (this.detailView.newComment || '').trim();
            if (!text) return;
            try {
                await this.api('/comments', {
                    method: 'POST',
                    body: JSON.stringify({
                        content: text,
                        entity_type: this.detailView.type,
                        entity_id: this.detailView.id,
                    }),
                });
                this.detailView.newComment = '';
                await this.loadDetail();
            } catch (e) { this.notify(e.message); }
        },

        async removeComment(cid) {
            if (!confirm(window.ZenI18n.t('Usunąć komentarz?'))) return;
            try {
                await this.api(`/comments/${cid}`, { method: 'DELETE' });
                await this.loadDetail();
            } catch (e) { this.notify(e.message); }
        },

        async addContactToDetail() {
            this.quickAdd('contact');
        },

        async addTaskToDetail() {
            this.quickAdd('task');
        },

        async addDocumentToDetail() {
            this.quickAdd('document');
        },

        async convertLead() {
            if (!confirm(window.ZenI18n.t('Konwertować lead na klienta? Kontakty, zadania i dokumenty zostaną przeniesione.'))) return;
            try {
                const oldLeadId = this.detailView.id;
                const r = await this.api(`/leads/${oldLeadId}/convert`, { method: 'POST' });
                this.notify(window.ZenI18n.t('Lead przekonwertowany na klienta! Otwieram widok nowego klienta.'));

                // Odśwież listę leadów i klientów w tle
                this.currentView = 'clients';
                if (location.hash !== '#clients') {
                    history.replaceState(null, '', '#clients');
                }
                localStorage.setItem('lastView', 'clients');

                // Przełącz detailView na klienta
                this.detailView = {
                    open: true,
                    type: 'client',
                    id: r.client_id,
                    data: null,
                    tab: 'overview',
                    contacts: [],
                    tasks: [],
                    documents: [],
                    comments: [],
                    activities: [],
                    newComment: '',
                    loading: true,
                };
                await this.loadDetail();
                await this.reload();
            } catch (e) { this.notify(e.message); }
        },

}; };
