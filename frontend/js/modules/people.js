window.ZenModules = window.ZenModules || {};
window.ZenModules.people = function () { return {
        userStatusFilter: '',
        employeeAvatar: {open:false, user:null, file:null, preview:'', remove:false, busy:false, error:''},
        openEmployeeAvatar(employee) {
            if (this.user?.role !== 'admin' || !employee?.id || this.employeeAvatar.busy) return;
            this.closeEmployeeAvatar();
            this._employeeAvatarTrigger = typeof document !== 'undefined' ? document.activeElement : null;
            if (typeof document !== 'undefined') { this._employeeAvatarOverflow = document.body.style.overflow; document.body.style.overflow = 'hidden'; }
            this.employeeAvatar = {open:true,user:{...employee},file:null,preview:'',remove:false,busy:false,error:''};
            if (this.$nextTick) this.$nextTick(() => document.querySelector('.employee-avatar-dialog button')?.focus());
        },
        closeEmployeeAvatar() {
            if (this.employeeAvatar.busy) return;
            if (this.employeeAvatar.preview) URL.revokeObjectURL(this.employeeAvatar.preview);
            this.employeeAvatar = {open:false,user:null,file:null,preview:'',remove:false,busy:false,error:''};
            this._employeeAvatarTrigger?.focus(); this._employeeAvatarTrigger = null;
            if (typeof document !== 'undefined' && this._employeeAvatarOverflow !== undefined) { document.body.style.overflow = this._employeeAvatarOverflow; this._employeeAvatarOverflow = undefined; }
        },
        trapEmployeeAvatarFocus(event) {
            const controls = [...event.currentTarget.querySelectorAll('button:not(:disabled),input:not(:disabled)')].filter(node => node.getClientRects().length);
            if (!controls.length) return;
            const first = controls[0], last = controls[controls.length - 1];
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        },
        selectEmployeeAvatar(event) {
            const file = event.target.files?.[0]; event.target.value = '';
            if (!file || this.employeeAvatar.busy) return;
            this.employeeAvatar.error = '';
            if (file.size > 2 * 1024 * 1024 || !['image/png','image/jpeg','image/gif','image/webp'].includes(file.type)) {
                this.employeeAvatar.error = window.ZenI18n.t('Wybierz obraz PNG, JPG, GIF lub WEBP do 2 MB.'); return;
            }
            if (this.employeeAvatar.preview) URL.revokeObjectURL(this.employeeAvatar.preview);
            this.employeeAvatar.file = file;
            this.employeeAvatar.preview = URL.createObjectURL(file);
            this.employeeAvatar.remove = false;
        },
        markEmployeeAvatarRemoved() {
            if (this.employeeAvatar.busy) return;
            if (this.employeeAvatar.preview) URL.revokeObjectURL(this.employeeAvatar.preview);
            this.employeeAvatar.preview = ''; this.employeeAvatar.file = null; this.employeeAvatar.remove = true;
        },
        async saveEmployeeAvatar() {
            const editor = this.employeeAvatar, token = this.token;
            if (this.user?.role !== 'admin' || !editor.user?.id || editor.busy || (!editor.file && !editor.remove)) return;
            editor.busy = true; editor.error = '';
            try {
                const options = {method:editor.remove ? 'DELETE' : 'POST',headers:{Authorization:'Bearer ' + token,'Accept-Language':window.ZenI18n.locale}};
                if (!editor.remove) { const body = new FormData(); body.append('file',editor.file); options.body = body; }
                const response = await fetch(`/api/users/${editor.user.id}/avatar`,options);
                const data = await response.json();
                if (this.token !== token || this.employeeAvatar !== editor) return;
                if (!response.ok) throw new Error(data.error || window.ZenI18n.t('Nie udało się zapisać zdjęcia.'));
                const updated = data.user || {...(this.users.find(u => u.id === editor.user.id) || editor.user),avatar_url:null};
                this.users = this.users.map(u => u.id === updated.id ? {...u,...updated} : u);
                for (const team of this.teams || []) {
                    if (team.leader?.id === updated.id) team.leader = {...team.leader,avatar_url:updated.avatar_url};
                    team.members = (team.members || []).map(u => u.id === updated.id ? {...u,avatar_url:updated.avatar_url} : u);
                }
                if (this.modal.editingId === updated.id && this.modal.view === 'users') this.modal.form.avatar_url = updated.avatar_url;
                if (this.user.id === updated.id) {
                    this.user = {...this.user,...updated}; this.avatarTs = Date.now();
                    this.profile.form.avatar_url = updated.avatar_url || '';
                    localStorage.setItem('user',JSON.stringify(this.user));
                }
                editor.busy = false; this.closeEmployeeAvatar(); this.notify(window.ZenI18n.t('Zdjęcie pracownika zapisane.'));
            } catch (error) { if (this.token === token && this.employeeAvatar === editor) editor.error = error.message; }
            finally { editor.busy = false; }
        },
        async uploadAvatar(event) {
            const file = event.target.files && event.target.files[0];
            if (!file) return;

            if (file.size > 2 * 1024 * 1024) {
                this.notify(window.ZenI18n.t('Plik jest za duży (max 2 MB)'));
                event.target.value = '';
                return;
            }

            const fd = new FormData();
            fd.append('file', file);

            try {
                const r = await fetch(`/api/users/${this.user.id}/avatar`, {
                    method: 'POST',
                    headers: { 'Authorization': 'Bearer ' + this.token, 'Accept-Language': window.ZenI18n.locale },
                    body: fd,
                });
                const data = await r.json();
                if (!r.ok) throw new Error(data.error || window.ZenI18n.t('Błąd wgrywania'));

                this.avatarTs = Date.now();
                if (data.user) {
                    this.user = data.user;
                } else {
                    this.user.avatar_url = data.avatar_url;
                }
                this.profile.form.avatar_url = this.user.avatar_url;
                localStorage.setItem('user', JSON.stringify(this.user));
                this.profile.success = window.ZenI18n.t('Avatar zaktualizowany');
                setTimeout(() => { this.profile.success = ''; }, 2000);
            } catch (e) {
                this.notify(window.ZenI18n.t('Błąd: ') + e.message);
            }
            event.target.value = '';
        },

        async removeAvatar() {
            if (!confirm(window.ZenI18n.t('Usunąć zdjęcie profilowe?'))) return;
            try {
                const r = await fetch(`/api/users/${this.user.id}/avatar`, {
                    method: 'DELETE',
                    headers: { 'Authorization': 'Bearer ' + this.token, 'Accept-Language': window.ZenI18n.locale },
                });
                if (!r.ok) throw new Error(window.ZenI18n.t('Nie udało się usunąć'));
                this.user.avatar_url = null;
                this.profile.form.avatar_url = '';
                localStorage.setItem('user', JSON.stringify(this.user));
                this.profile.success = window.ZenI18n.t('Avatar usunięty');
                setTimeout(() => { this.profile.success = ''; }, 2000);
            } catch (e) { this.notify(e.message); }
        },


        // ═══════════════════════════════════════════════════════════
        // PRZYPISANIE OSOBY ODPOWIEDZIALNEJ (LEAD)
        // ═══════════════════════════════════════════════════════════
        quickAssign(lead, event) {
            // Otwórz mały popup z listą użytkowników
            this.assignPicker.lead = lead;
            this.assignPicker.open = true;
            if (event) {
                const r = event.currentTarget.getBoundingClientRect();
                this.assignPicker.x = r.left;
                this.assignPicker.y = r.bottom + 4;
            }
        },

        async setAssignee(userId) {
            const lead = this.assignPicker.lead;
            if (!lead) return;
            try {
                await this.api(`/leads/${lead.id}`, {
                    method: 'PUT',
                    body: JSON.stringify({ assignee_id: userId || null }),
                });
                // Lokalnie zaktualizuj
                if (userId) {
                    const u = this.users.find(x => x.id === userId);
                    lead.assignee_id = userId;
                    lead.assignee = u ? {
                        id: u.id,
                        first_name: u.first_name,
                        last_name: u.last_name,
                        avatar_url: u.avatar_url,
                    } : null;
                } else {
                    lead.assignee_id = null;
                    lead.assignee = null;
                }
            } catch (e) { this.notify(window.ZenI18n.t('Błąd: ') + e.message); }
            this.assignPicker.open = false;
        },


        // ═══════════════════════════════════════════════════════════
        // SYNCHRONIZACJA DANYCH ZALOGOWANEGO UŻYTKOWNIKA
        // ═══════════════════════════════════════════════════════════
        async loadMe() {
            if (!this.token) return;
            try {
                const me = await this.api('/auth/me');
                this.user = me;
                this.isAdmin = (me?.role === 'admin');
                localStorage.setItem('user', JSON.stringify(me));
            } catch (e) {
                console.warn(window.ZenI18n.t('Nie udało się odświeżyć profilu:'), e.message);
            }
        },


        // ═══════════════════════════════════════════════════════════
        // SZYBKIE AKCJE Z WIDOKU KLIENTA/LEADA
        // ═══════════════════════════════════════════════════════════
        quickAdd(type) {
            const isClient = this.detailView.type === 'client';
            const entityId = this.detailView.id;
            const leadClientId = !isClient ? this.detailView.data?.client_id : null;

            // Notatka = komentarz (przełącz na zakładkę)
            if (type === 'note') {
                this.detailView.tab = 'comments';
                this.$nextTick(() => {
                    const ta = document.querySelector('textarea[x-model="detailView.newComment"]');
                    if (ta) ta.focus();
                });
                return;
            }

            const config = {
                lead:     { view: 'leads',     prefill: { client_id: entityId } },
                contact:  { view: 'contacts',  prefill: isClient ? { client_id: entityId, is_primary: false } : { lead_id: entityId, is_primary: false } },
                task:     { view: 'tasks',     prefill: isClient ? { client_id: entityId } : { lead_id: entityId } },
                meeting:  { view: 'meetings',  prefill: isClient ? { client_id: entityId } : { lead_id: entityId, client_id: leadClientId || null } },
                document: { view: 'documents', prefill: isClient ? { client_id: entityId } : { lead_id: entityId } },
                service:  { view: 'services',  prefill: { client_id: entityId } },
                serviceCatalog: { view: 'serviceCatalog', prefill: {} },
            }[type];

            if (!config) return;
            const lockedRelations = ['client_id', 'lead_id'];
            this.openModal(null, null, true, config.view, { prefill: config.prefill, lockedRelations });
        },

        closeModal() {
            this.modal.open = false;
            this.modal.view = null;
            this.modal.lockedRelations = [];
        },

        // ═══════════════════════════════════════════════════════════
        // ZESPOŁY (TEAMS)
        // ═══════════════════════════════════════════════════════════
        async loadTeams() {
            try {
                this.teams = await this.api('/teams');
            } catch (e) {
                console.warn('Nie udało się pobrać zespołów:', e.message);
            }
        },

        get filteredUsers() {
            const q = (this.userSearch || '').trim().toLowerCase();
            const teamId = this.userTeamFilter ? Number(this.userTeamFilter) : null;
            return (this.users || []).filter(u => {
                const nameMatch = !q || `${u.first_name || ''} ${u.last_name || ''} ${u.email || ''}`.toLowerCase().includes(q);
                if (!nameMatch) return false;
                if (this.userStatusFilter === 'active' && !u.is_active) return false;
                if (this.userStatusFilter === 'inactive' && u.is_active) return false;
                if (teamId) {
                    return (u.teams || []).some(t => t.id === teamId) || (u.team_ids || []).includes(teamId);
                }
                return true;
            });
        },

        openTeamModal(team = null) {
            this.teamModal.editingId = team ? team.id : null;
            this.teamModal.form = team
                ? {
                    name: team.name,
                    description: team.description || '',
                    color: team.color || '#018bfc',
                    leader_id: team.leader_id || null,
                    member_ids: [...(team.member_ids || [])]
                }
                : {
                    name: '',
                    description: '',
                    color: '#018bfc',
                    leader_id: null,
                    member_ids: []
                };
            this.teamModal.error = '';
            this.teamModal.open = true;
        },

        closeTeamModal() {
            this.teamModal.open = false;
            this.teamModal.editingId = null;
            this.teamModal.error = '';
        },

        toggleTeamMember(userId) {
            if (!this.teamModal.form.member_ids) this.teamModal.form.member_ids = [];
            const idx = this.teamModal.form.member_ids.indexOf(userId);
            if (idx > -1) {
                this.teamModal.form.member_ids.splice(idx, 1);
            } else {
                this.teamModal.form.member_ids.push(userId);
            }
        },

        isTeamMember(userId) {
            return (this.teamModal.form.member_ids || []).includes(userId);
        },

        async saveTeamModal() {
            if (this.teamModal.saving) return;
            if (!this.teamModal.form.name?.trim()) {
                this.teamModal.error = window.ZenI18n.t('Nazwa zespołu jest wymagana');
                return;
            }
            this.teamModal.saving = true;
            this.teamModal.error = '';
            try {
                const isEdit = !!this.teamModal.editingId;
                const url = isEdit ? `/teams/${this.teamModal.editingId}` : '/teams';
                const method = isEdit ? 'PUT' : 'POST';
                const savedTeam = await this.api(url, {
                    method,
                    body: JSON.stringify(this.teamModal.form)
                });
                this.teams = isEdit
                    ? this.teams.map(team => team.id === savedTeam.id ? savedTeam : team)
                    : [...this.teams, savedTeam];
                this.teams.sort((a, b) => a.name.localeCompare(b.name));
                this.closeTeamModal();
                this.notify(isEdit ? window.ZenI18n.t('Zaktualizowano zespół') : window.ZenI18n.t('Utworzono zespół'));
                try {
                    this.users = await this.api('/users');
                } catch (e) {
                    console.warn('Nie udało się odświeżyć pracowników:', e.message);
                }
            } catch (e) {
                this.teamModal.error = e.message;
            } finally {
                this.teamModal.saving = false;
            }
        },

        async deleteTeam(teamId) {
            if (!confirm(window.ZenI18n.t('Czy na pewno chcesz usunąć ten zespół?'))) return;
            try {
                await this.api(`/teams/${teamId}`, { method: 'DELETE' });
                await this.loadTeams();
                this.users = await this.api('/users');
                this.notify(window.ZenI18n.t('Usunięto zespół'));
            } catch (e) {
                this.notify(window.ZenI18n.t('Nie udało się usunąć zespołu: ') + e.message);
            }
        },

}; };
