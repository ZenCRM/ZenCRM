window.ZenModules = window.ZenModules || {};
window.ZenModules.services = function () { return {
        addTaskAssignee(userId) {
            if (!userId) return;
            const uid = parseInt(userId, 10);
            if (this.taskAssigneesUI.some(a => a.user_id === uid)) return;
            const u = this.users.find(x => x.id === uid);
            if (!u) return;
            this.taskAssigneesUI.push({
                user_id: uid,
                user: { id: u.id, first_name: u.first_name, last_name: u.last_name, avatar_url: u.avatar_url },
                status: 'pending',
                comment: '',
            });
        },

        async loadTaskAssignees(taskId) {
            if (!taskId) { this.taskAssigneesUI = []; return; }
            try {
                this.taskAssigneesUI = await this.api(`/task-assignees/task/${taskId}`);
            } catch (_) { this.taskAssigneesUI = []; }
        },

        async saveTaskAssignees(taskId) {
            if (!taskId) return;
            try {
                const userIds = this.taskAssigneesUI.map(a => a.user_id);
                await this.api(`/task-assignees/task/${taskId}/set`, {
                    method: 'POST',
                    body: JSON.stringify({ user_ids: userIds }),
                });
                // Zapisz statusy/komentarze
                const fresh = await this.api(`/task-assignees/task/${taskId}`);
                for (const row of fresh) {
                    const ui = this.taskAssigneesUI.find(a => a.user_id === row.user_id);
                    if (ui && this.canChangeTaskPerson(row) && (ui.status !== row.status || ui.comment !== row.comment)) {
                        await this.api(`/task-assignees/${row.id}`, {
                            method: 'PUT',
                            body: JSON.stringify({ status: ui.status, comment: ui.comment }),
                        });
                    }
                }
            } catch (e) { console.warn('saveTaskAssignees:', e.message); }
        },

        serviceStatusLabel(s) {
            return { exemplary: window.ZenI18n.t('Wzorowa'), good: window.ZenI18n.t('Dobra'),
                     problematic: window.ZenI18n.t('Problematyczna'), critical: window.ZenI18n.t('Krytyczna') }[s] || s;
        },
        serviceStatusClass(s) {
            return { exemplary: 'bg-green-100 text-green-700',
                     good: 'bg-blue-100 text-blue-700',
                     problematic: 'bg-yellow-100 text-yellow-700',
                     critical: 'bg-red-100 text-red-700' }[s] || 'bg-gray-100 text-gray-700';
        },
        catalogName(id) {
            if (!id) return '';
            const c = this.serviceCatalog.find(x => x.id === id);
            return c ? c.name : `#${id}`;
        },


        // ═══════════════════════════════════════════════════════════
        // MAPOWANIE WIDOK -> SCIEZKA API
        // ═══════════════════════════════════════════════════════════
        apiPath(view) {
            const map = {
                serviceCatalog: 'service-catalog',
                sms: 'sms',
            };
            return map[view] || view;
        },


        // ═══════════════════════════════════════════════════════════
        // AKCJE Z POZIOMU USŁUGI
        // ═══════════════════════════════════════════════════════════
        quickAddFromService(type) {
            const serviceId = this.detailView.id;
            const serviceData = this.detailView.data || {};
            const clientId = serviceData.client_id;

            const config = {
                task:     { view: 'tasks',     prefill: { service_id: serviceId, client_id: clientId } },
                document: { view: 'documents', prefill: { service_id: serviceId, client_id: clientId } },
            }[type];

            if (!config) return;

            this.modal.view = config.view;
            this.modal.editingId = null;
            this.modal.form = { ...config.prefill };
            this.modal.error = '';
            this.modal.open = true;
            this.ensureLookups();
        },

        async addServiceComment() {
            const text = (this.detailView.newComment || '').trim();
            if (!text) return;
            try {
                await this.api('/comments', {
                    method: 'POST',
                    body: JSON.stringify({
                        content: text,
                        entity_type: 'service',
                        entity_id: this.detailView.id,
                    }),
                });
                this.detailView.newComment = '';
                await this.loadDetail();
            } catch (e) { this.notify(e.message); }
        },


        // ═══════════════════════════════════════════════════════════
        // MULTI-USER SELECT DLA USŁUG
        // ═══════════════════════════════════════════════════════════
        addServiceAssignee(userId) {
            if (!userId) return;
            const uid = parseInt(userId, 10);
            if (!this.modal.form.assignee_ids) this.modal.form.assignee_ids = [];
            if (this.modal.form.assignee_ids.includes(uid)) return;
            this.modal.form.assignee_ids = [...this.modal.form.assignee_ids, uid];
        },

        removeServiceAssignee(uid) {
            if (!this.modal.form.assignee_ids) return;
            this.modal.form.assignee_ids = this.modal.form.assignee_ids.filter(x => x !== uid);
        },

        // Lista userow wykluczajaca juz wybranych
        availableAssignees() {
            const chosen = this.modal.form.assignee_ids || [];
            return (this.users || []).filter(u => !chosen.includes(u.id));
        },

        // Edycja uslugi z widoku szczegolowego – wymus view='services'
        openServiceEdit() {
            if (!this.detailView.data) return;
            this.openModal(this.detailView.data, null, true, 'services');
        },


        // ═══════════════════════════════════════════════════════════
        // OCENA USŁUGI (szybkie akcje)
        // ═══════════════════════════════════════════════════════════
        async rateServiceStatus(status) {
            if (!this.detailView.data) return;
            const id = this.detailView.id;
            try {
                await this.api(`/services/${id}`, {
                    method: 'PUT',
                    body: JSON.stringify({ status }),
                });
                this.detailView.data.status = status;
                const found = this.services.find(s => s.id === id);
                if (found) found.status = status;
            } catch (e) { this.notify(window.ZenI18n.t('Błąd: ') + e.message); }
        },

        async rateServiceRisk(level) {
            if (!this.detailView.data) return;
            const id = this.detailView.id;
            try {
                await this.api(`/services/${id}`, {
                    method: 'PUT',
                    body: JSON.stringify({ risk_level: level }),
                });
                this.detailView.data.risk_level = level;
                const found = this.services.find(s => s.id === id);
                if (found) found.risk_level = level;
            } catch (e) { this.notify(window.ZenI18n.t('Błąd: ') + e.message); }
        },

        quickSetStatus(service) {
            this.openModal(service, null, false, 'services');
        },


        // ═══════════════════════════════════════════════════════════
        // ZESPOL USLUGI (dodawanie/usuwanie)
        // ═══════════════════════════════════════════════════════════
        usersNotInTeam() {
            const team = this.detailView.data?.assignees || [];
            const ids = team.map(u => u.id);
            return (this.users || []).filter(u => !ids.includes(u.id));
        },

        async addTeamMember(userId) {
            if (!userId || !this.detailView.data) return;
            const uid = parseInt(userId, 10);
            const current = (this.detailView.data.assignee_ids || []).slice();
            if (current.includes(uid)) return;
            current.push(uid);
            await this.saveTeam(current);
        },

        async removeTeamMember(userId) {
            if (!this.detailView.data) return;
            const current = (this.detailView.data.assignee_ids || []).filter(x => x !== userId);
            await this.saveTeam(current);
        },

        async saveTeam(ids) {
            const id = this.detailView.id;
            try {
                await this.api(`/services/${id}`, {
                    method: 'PUT',
                    body: JSON.stringify({ assignee_ids: ids }),
                });
                // Odswiez z serwera (zeby dostac pelne obiekty assignees)
                const fresh = await this.api(`/services/${id}`);
                this.detailView.data = { ...this.detailView.data, ...fresh };
                // Zaktualizuj tez na liscie services
                const found = this.services.find(s => s.id === id);
                if (found) {
                    found.assignee_ids = fresh.assignee_ids;
                    found.assignees = fresh.assignees;
                }
            } catch (e) { this.notify(window.ZenI18n.t('Błąd: ') + e.message); }
        },

        // Stub – sledzenie (bedzie pelne w kolejnym kroku)
        isFollowing(type, id) { return false; },
        async toggleFollow(type, id) { this.notify(window.ZenI18n.t('Funkcja sledzenia bedzie dostepna za chwile.')); },


        // ═══════════════════════════════════════════════════════════
        // ZADANIE – przypisani, komentarze, statusy
        // ═══════════════════════════════════════════════════════════
        async updateTaskAssigneeStatus(taId, status) {
            try {
                await this.api(`/task-assignees/${taId}`, {
                    method: 'PUT',
                    body: JSON.stringify({ status }),
                });
                await this.loadDetail();
            } catch (e) { this.notify(window.ZenI18n.t('Błąd: ') + e.message); }
        },

        async updateTaskAssigneeComment(taId, comment) {
            try {
                await this.api(`/task-assignees/${taId}`, {
                    method: 'PUT',
                    body: JSON.stringify({ comment }),
                });
            } catch (e) { this.notify(window.ZenI18n.t('Błąd: ') + e.message); }
        },

        async addTaskComment() {
            const text = (this.detailView.newComment || '').trim();
            if (!text) return;
            try {
                await this.api('/comments', {
                    method: 'POST',
                    body: JSON.stringify({
                        content: text,
                        entity_type: 'task',
                        entity_id: this.detailView.id,
                    }),
                });
                this.detailView.newComment = '';
                await this.loadDetail();
            } catch (e) { this.notify(e.message); }
        },

        async addTeamMemberToTask(userId) {
            if (!userId || !this.detailView.data) return;
            const uid = parseInt(userId, 10);
            const current = (this.detailView.team || []).map(a => a.user_id);
            if (current.includes(uid)) return;
            current.push(uid);
            try {
                await this.api(`/task-assignees/task/${this.detailView.id}/set`, {
                    method: 'POST',
                    body: JSON.stringify({ user_ids: current }),
                });
                await this.loadDetail();
            } catch (e) { this.notify(window.ZenI18n.t('Błąd: ') + e.message); }
        },

        async removeTeamMemberFromTask(taId) {
            try {
                await this.api(`/task-assignees/${taId}`, { method: 'DELETE' });
                await this.loadDetail();
            } catch (e) { this.notify(window.ZenI18n.t('Błąd: ') + e.message); }
        },

        taskAssigneeStatusLabel(s) {
            return { pending: window.ZenI18n.t('Oczekuje'), in_progress: window.ZenI18n.t('W toku'), done: window.ZenI18n.t('Zrobione') }[s] || s;
        },
        taskAssigneeStatusClass(s) {
            return {
                pending:     'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
                in_progress: 'bg-yellow-100 text-yellow-700',
                done:        'bg-green-100 text-green-700',
            }[s] || 'bg-gray-100 text-gray-700';
        },


}; };
