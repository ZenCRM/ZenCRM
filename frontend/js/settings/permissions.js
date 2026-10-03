/* Settings component section; state is created for each CRM instance. */
window.ZenSettings = window.ZenSettings || {};
window.ZenSettings.permissions = function () { return {
        can(permission) {
            return this.user?.role === 'admin' || this.effectivePermissions[permission] !== false;
        },
        canRecordAction(view, action) {
            if (view === 'users' || view === 'teams') return this.user?.role === 'admin';
            const module = view === 'serviceCatalog' ? 'service_catalog' : view;
            return this.can(`${module}.${action}`);
        },
        async loadMyPermissions() {
            if (!this.token) return;
            try { this.effectivePermissions = await this.api('/permissions/me'); }
            catch (e) { console.warn('Nie pobrano uprawnień:', e.message); }
        },
        async loadPermissions() {
            this.permissionError = '';
            try {
                const data = await this.api('/permissions');
                this.permissionCatalog = data.permissions || [];
                this.managedRoles = data.roles || [];
                this.roleRules = data.role_rules || {};
                this.teamRules = data.team_rules || {};
                if (!this.teams.length) await this.loadTeams();
            } catch (e) { this.permissionError = e.message; }
        },
        permissionRule(key) {
            const [kind, id] = this.permissionSubject.split(':');
            const rules = kind === 'role' ? this.roleRules[id] : this.teamRules[id];
            return rules?.[key] === true ? 'allow' : rules?.[key] === false ? 'deny' : 'inherit';
        },
        setPermissionRule(key, value) {
            const [kind, id] = this.permissionSubject.split(':');
            const source = kind === 'role' ? this.roleRules : this.teamRules;
            if (!source[id]) source[id] = {};
            if (value === 'inherit') delete source[id][key];
            else source[id][key] = value === 'allow';
        },
        async savePermissions() {
            const [kind, id] = this.permissionSubject.split(':');
            const rules = kind === 'role' ? this.roleRules[id] || {} : this.teamRules[id] || {};
            this.permissionError = '';
            this.permissionSaved = '';
            try {
                await this.api(kind === 'role' ? `/permissions/roles/${id}/rules` : `/permissions/teams/${id}/rules`, {
                    method: 'PUT', body: JSON.stringify({ rules: Object.fromEntries(this.permissionCatalog.map(p => [p.key, Object.prototype.hasOwnProperty.call(rules, p.key) ? rules[p.key] : null])) }),
                });
                this.permissionSaved = window.ZenI18n.t('Uprawnienia zapisane');
                await this.loadMyPermissions();
            } catch (e) { this.permissionError = e.message; }
        },
        async createManagedRole() {
            this.permissionError = '';
            try {
                const role = await this.api('/permissions/roles', { method: 'POST', body: JSON.stringify({ name: this.newRoleName }) });
                this.newRoleName = '';
                await this.loadPermissions();
                this.permissionSubject = `role:${role.key}`;
                this.roleNameDraft = role.name;
            } catch (e) { this.permissionError = e.message; }
        },
        async renameManagedRole() {
            const [kind, id] = this.permissionSubject.split(':');
            if (kind !== 'role') return;
            this.permissionError = '';
            try {
                await this.api(`/permissions/roles/${id}`, { method: 'PUT', body: JSON.stringify({ name: this.roleNameDraft }) });
                await this.loadPermissions();
                this.permissionSaved = window.ZenI18n.t('Nazwa roli zapisana');
            } catch (e) { this.permissionError = e.message; }
        },
        async deleteManagedRole() {
            const [kind, id] = this.permissionSubject.split(':');
            if (kind !== 'role' || ['admin', 'manager', 'employee'].includes(id)) return;
            if (!confirm(window.ZenI18n.t('Usunąć tę rolę?'))) return;
            try {
                await this.api(`/permissions/roles/${id}`, { method: 'DELETE' });
                this.permissionSubject = 'role:manager';
                await this.loadPermissions();
            } catch (e) { this.permissionError = e.message; }
        },
}; };
