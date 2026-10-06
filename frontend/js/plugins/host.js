/* Trusted host. This component is deliberately separate from crmApp/ZenModules. */
(function () {
    'use strict';
    const t = key => window.ZenI18n.t(key);

    function bridge(frame, origin, context, invoke, alive) {
        let channel = crypto.randomUUID();
        let closed = false, busy = 0;
        const seen = new Set();
        const send = value => { if (!closed && alive() && value.channel === channel) frame.contentWindow?.postMessage(value, origin); };
        const listener = async event => {
            if (closed || !alive() || event.source !== frame.contentWindow || event.origin !== origin) return;
            const message = event.data;
            if (!message || message.type !== 'zen:request' || message.channel !== channel ||
                typeof message.id !== 'string' || message.id.length > 80 || seen.has(message.id)) return;
            try { if (JSON.stringify(message).length > 32768) return; } catch (_) { return; }
            if (busy >= 8 || seen.size >= 1000) return;
            const requestChannel = channel;
            seen.add(message.id); busy++;
            try {
                let result;
                if (message.method === 'context') result = context;
                else if (message.method === 'resize' && Number.isFinite(message.params?.height)) {
                    frame.style.height = Math.min(800, Math.max(160, message.params.height)) + 'px';
                    result = {ok: true};
                } else if (message.method === 'call' && typeof message.operation === 'string') {
                    result = await invoke(message.operation, message.params || {});
                } else throw new Error(t('Nieobsługiwana operacja aplikacji'));
                send({type: 'zen:response', channel: requestChannel, id: message.id, result});
            } catch (error) {
                send({type: 'zen:response', channel: requestChannel, id: message.id, error: error.message || t('Błąd aplikacji')});
            } finally { if (requestChannel === channel) busy--; }
        };
        window.addEventListener('message', listener);
        const ready = () => { channel = crypto.randomUUID(); seen.clear(); busy = 0; send({type: 'zen:init', channel, context}); };
        frame.addEventListener('load', ready);
        return {close() {
            closed = true;
            window.removeEventListener('message', listener);
            frame.removeEventListener('load', ready);
            frame.remove();
        }};
    }
    window.ZenPluginBridge = {create: bridge};

    window.pluginSlot = function (slot) { return {
        slot, apps: [], entries: [], slotError: '', requestSerial: 0, bridges: [],
        active() {
            if (!this.token) return false;
            if (this.slot === 'dashboard.widget') return this.currentView === 'dashboard' && !this.detailView.open;
            if (this.slot === 'client.detail.tab') return this.detailView.open && this.detailView.type === 'client' && this.detailView.tab === 'plugins';
            return this.currentView === 'plugins' && this.hubTab === 'mine' && !!this.workspaceApp;
        },
        contextKey() { return this.slot === 'client.detail.tab' ? this.detailView.data?.id : null; },
        init() {
            const update = () => { this.closeFrames(); if (this.active()) this.loadSlots(); };
            this.$watch('token', update); this.$watch('currentView', update);
            this.$watch('detailView.open', update);
            this.$watch(() => this.detailView.data?.id, () => { if (this.slot === 'client.detail.tab') update(); });
            this.$watch('detailView.tab', () => { if (this.slot === 'client.detail.tab') update(); });
            if (this.slot === 'app.page') {
                this.$watch('hubTab', update); this.$watch('workspaceApp', update);
            }
            update();
        },
        destroy() { this.closeFrames(); },
        closeFrames() { this.requestSerial++; this.bridges.forEach(item => item.close()); this.bridges = []; this.entries = []; },
        async loadSlots() {
            this.closeFrames(); this.slotError = '';
            const session = this.token, serial = this.requestSerial, entityId = this.contextKey();
            try {
                const status = await this.api('/plugins/status');
                if (!status.enabled) return;
                const apps = await this.api('/plugins/apps');
                if (session !== this.token || serial !== this.requestSerial || !this.active()) return;
                const entries = [];
                for (const app of apps) {
                    if (!app.consented_scopes.length) continue;
                    if (this.slot === 'app.page' && app.id !== this.workspaceApp) continue;
                    for (const placement of app.manifest.placements.filter(p => p.slot === this.slot)) {
                        entries.push({key: app.id + ':' + placement.id, app, placement, result: null, error: '', page: 1, search: '', loading: false});
                    }
                }
                this.entries = entries;
                await this.$nextTick();
                for (const entry of entries) {
                    const alive = () => session === this.token && serial === this.requestSerial && this.active() && entityId === this.contextKey();
                    const invoke = (operation, params) => {
                        if (!alive()) throw new Error(t('Sesja aplikacji zakończona'));
                        return this.api('/plugins/apps/' + entry.app.id + '/invoke', {method: 'POST', body: JSON.stringify({operation, params})});
                    };
                    try {
                        if (entry.app.manifest.type === 'declarative') {
                            const result = await invoke(entry.placement.operation, {});
                            if (alive()) this.entries.find(e => e.key === entry.key).result = result;
                        } else {
                            const url = new URL(entry.placement.url);
                            if (url.protocol !== 'https:' || url.origin === location.origin || url.username || url.password) throw new Error(t('Aplikacja wymaga osobnej domeny HTTPS'));
                            if (!alive()) return;
                            const container = [...this.$el.querySelectorAll('[data-plugin-frame]')].find(el => el.dataset.pluginFrame === entry.key);
                            if (!container) continue;
                            const frame = document.createElement('iframe');
                            frame.title = entry.placement.label;
                            frame.setAttribute('sandbox', 'allow-scripts allow-forms allow-same-origin');
                            frame.setAttribute('referrerpolicy', 'no-referrer');
                            frame.setAttribute('allow', "camera 'none'; microphone 'none'; geolocation 'none'; payment 'none'; clipboard-read 'none'; clipboard-write 'none'");
                            frame.style.cssText = 'width:100%;height:320px;border:0';
                            const port = bridge(frame, url.origin, {app_id: entry.app.id, slot: this.slot, entity_id: entityId}, invoke, alive);
                            this.bridges.push(port); frame.src = url.href; container.appendChild(frame);
                        }
                    } catch (error) { if (alive()) this.entries.find(e => e.key === entry.key).error = error.message; }
                }
            } catch (error) { if (session === this.token && serial === this.requestSerial) this.slotError = error.message; }
        },
        async listPage(entry, page = 1) {
            if (entry.loading) return;
            const session = this.token, serial = this.requestSerial;
            entry.loading = true; entry.error = '';
            try {
                const result = await this.api('/plugins/apps/' + entry.app.id + '/invoke', {method: 'POST', body: JSON.stringify({operation: entry.placement.operation, params: {page, search: entry.search, limit: 25}})});
                if (session === this.token && serial === this.requestSerial && this.active()) { entry.result = result; entry.page = page; }
            } catch (error) { if (session === this.token && serial === this.requestSerial) entry.error = error.message; }
            finally { entry.loading = false; }
        }
    }; };

    window.pluginHub = function () { return {
        enabled: false, hubLoaded: false, hubBusy: false, hubError: '', hubApps: [], storeApps: [], catalog: null,
        hubTab: 'store', storeQuery: '', storeCategory: '', storeDetail: null, workspaceApp: '', loadSerial: 0,
        selected: null, selectedScopes: [], selectedUsers: [], allUsers: false, configurationText: '{}', manifestText: '', newAppOpen: false,
        oneTimeSecret: '', diagnostic: [], diagnosticKind: '', authorization: null,
        ownedApps() { return this.hubApps.filter(app => app.consented_scopes.length); },
        filteredStore() {
            const q = this.storeQuery.trim().toLocaleLowerCase();
            return this.storeApps.filter(app => (!this.storeCategory || app.category === this.storeCategory) &&
                (!q || [this.appName(app), this.appDescription(app), t(app.category)].join(' ').toLocaleLowerCase().includes(q)));
        },
        categories() { return [...new Set(this.storeApps.map(app => app.category))]; },
        appName(app) { return app.bundled ? t(app.manifest.name) : app.manifest.name; },
        appDescription(app) { return app.bundled ? t(app.manifest.description) : app.manifest.description || ''; },
        appStatus(app) { return app.enabled ? t('Włączona') : app.installed ? t('Wyłączona') : t('Odinstalowana'); },
        openApp(app) { this.workspaceApp = app.id; this.hubTab = 'mine'; this.storeDetail = null; },
        tab(value) { this.hubTab = value; this.oneTimeSecret = ''; this.storeDetail = null; },
        init() {
            const load = () => {
                this.loadSerial++; this.oneTimeSecret = ''; this.hubApps = []; this.storeApps = []; this.catalog = null;
                this.selected = null; this.storeDetail = null; this.workspaceApp = ''; this.diagnostic = []; this.manifestText = '';
                this.newAppOpen = false; this.diagnosticKind = ''; this.hubLoaded = false; this.enabled = false; this.hubError = '';
                if (this.user?.role !== 'admin' && this.hubTab === 'manage') this.hubTab = 'store';
                if (this.token && this.currentView === 'plugins') this.loadHub();
            };
            this.$watch('token', () => { load(); if (this.token && this.authorization) this.selectView('plugins'); });
            this.$watch('currentView', load); load();
            const query = new URLSearchParams(location.search);
            if (query.has('plugin_authorize')) {
                this.authorization = Object.fromEntries(['response_type','redirect_uri','code_challenge','code_challenge_method','state'].map(key => [key, query.get(key)]));
                this.authorization.app_id = query.get('plugin_authorize');
                if (this.token) this.selectView('plugins');
            }
        },
        async loadHub() {
            const session = this.token, serial = ++this.loadSerial;
            const alive = () => session === this.token && serial === this.loadSerial && this.currentView === 'plugins';
            this.hubError = '';
            try {
                const status = await this.api('/plugins/status');
                if (!alive()) return;
                this.enabled = status.enabled;
                if (!status.enabled) { this.hubLoaded = true; this.hubApps = []; this.storeApps = []; this.catalog = null; this.workspaceApp = ''; return; }
                const [apps, store, catalog] = await Promise.all([this.api('/plugins/apps'), this.api('/plugins/store'),
                    this.user?.role === 'admin' ? this.api('/plugins/catalog') : Promise.resolve(null)]);
                if (!alive()) return;
                this.hubApps = apps; this.storeApps = store; this.catalog = catalog; this.hubLoaded = true;
                if (this.authorization && !this.storeDetail) this.storeDetail = store.find(app => app.id === this.authorization.app_id) || null;
                if (this.storeDetail) this.storeDetail = store.find(app => app.id === this.storeDetail.id) || null;
                if (this.selected) { const selected = catalog?.apps.find(app => app.id === this.selected.id); if (selected) this.editApp(selected); }
                if (!this.ownedApps().some(app => app.id === this.workspaceApp)) this.workspaceApp = '';
            } catch (error) { if (alive()) { this.hubError = error.message; this.hubLoaded = true; } }
        },
        async hubAction(action) {
            if (this.hubBusy) return;
            const session = this.token; this.hubBusy = true; this.hubError = '';
            const alive = () => session === this.token && this.currentView === 'plugins';
            try { await action(alive); if (alive()) await this.loadHub(); }
            catch (error) { if (alive()) this.hubError = error.message; }
            finally { this.hubBusy = false; }
        },
        editApp(app) {
            this.selected = app; this.selectedScopes = [...(app.approved_scopes.length ? app.approved_scopes : app.manifest.scopes)];
            this.allUsers = !!app.all_users;
            this.selectedUsers = [...(app.allowed_users?.length ? app.allowed_users.filter(id => Number.isInteger(id)) : [this.user.id])];
            this.configurationText = JSON.stringify(app.configuration || {}, null, 2);
            this.manifestText = JSON.stringify(app.manifest, null, 2); this.newAppOpen = false;
        },
        newApp() { this.selected = null; this.newAppOpen = true; this.manifestText = ''; this.diagnostic = []; this.diagnosticKind = ''; },
        async installApp() {
            await this.hubAction(async alive => {
                const id = this.selected.id;
                const app = await this.api('/plugins/apps/' + id + '/install', {method: 'POST', body: JSON.stringify({revision: this.selected.revision, scopes: this.selectedScopes, allowed_users: this.allUsers ? [] : this.selectedUsers, all_users: this.allUsers, configuration: JSON.parse(this.configurationText)})});
                if (alive() && this.selected?.id === id) this.editApp(app);
            });
        },
        async stateApp(action) {
            await this.hubAction(async alive => {
                const id = this.selected.id;
                const app = await this.api('/plugins/apps/' + id + '/' + action, {method: 'POST', body: JSON.stringify({revision: this.selected.revision})});
                if (alive() && this.selected?.id === id) this.editApp(app);
            });
            this.$dispatch('plugins-changed');
        },
        async registerApp(update = false) {
            await this.hubAction(async alive => {
                const app = await this.api(update ? '/plugins/apps/' + this.selected.id + '/manifest' : '/plugins/apps', {method: update ? 'PUT' : 'POST', body: JSON.stringify(JSON.parse(this.manifestText))});
                if (alive()) this.editApp(app);
            });
        },
        async consentApp(app, revoke = false) {
            await this.hubAction(() => this.api('/plugins/apps/' + app.id + '/consent', {method: revoke ? 'DELETE' : 'POST', ...(revoke ? {} : {body: JSON.stringify({revision: app.revision, scopes: app.approved_scopes})})}));
            this.$dispatch('plugins-changed');
        },
        async showSecret(app, credentials = false) {
            await this.hubAction(async alive => {
                const result = await this.api('/plugins/apps/' + app.id + '/' + (credentials ? 'credentials' : 'personal-token'), {method:'POST', body: JSON.stringify(credentials ? {} : {days: 1})});
                if (alive()) this.oneTimeSecret = JSON.stringify(result, null, 2);
            });
        },
        async revokeAppTokens(app) { await this.hubAction(() => this.api('/plugins/apps/' + app.id + '/tokens', {method:'DELETE'})); this.oneTimeSecret = ''; },
        async inspectApp(kind) {
            const id = this.selected.id;
            await this.hubAction(async alive => {
                const result = await this.api('/plugins/apps/' + id + '/' + kind);
                if (alive() && this.selected?.id === id) { this.diagnostic = result; this.diagnosticKind = kind; }
            });
        },
        diagnosticUser(id) { const person = this.catalog?.users.find(user => user.id === id); return person?.name || person?.email || (id ?? '—'); },
        diagnosticLabel(action) {
            const labels = {register: 'Rejestracja', install: 'Zatwierdzenie instalacji', enable: 'Włączenie', disable: 'Wyłączenie', uninstall: 'Odinstalowanie', consent: 'Zgoda użytkownika', revoke_consent: 'Cofnięcie zgody', personal_token: 'Utworzenie tokenu', revoke_tokens: 'Unieważnienie tokenów', update_manifest: 'Zmiana manifestu', rotate_credentials: 'Zmiana sekretów', pending: 'Oczekuje', sending: 'Wysyłanie', delivered: 'Dostarczono', cancelled: 'Anulowano', failed: 'Niepowodzenie'};
            return labels[action] ? t(labels[action]) : action;
        },
        async completeAuthorization(app) {
            await this.hubAction(async alive => {
                const {app_id, ...params} = this.authorization;
                const result = await this.api('/plugins/apps/' + app.id + '/authorize', {method:'POST', body:JSON.stringify(params)});
                if (!alive()) return;
                const redirect = new URL(result.redirect_uri);
                if (redirect.protocol !== 'https:' || !app.manifest.redirect_uris.includes(result.redirect_uri)) throw new Error(t('Błąd aplikacji'));
                redirect.searchParams.set('code', result.code); redirect.searchParams.set('state', result.state); location.assign(redirect.href);
            });
        }
    }; };
})();
