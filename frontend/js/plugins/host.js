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
            return this.currentView === 'plugins';
        },
        contextKey() { return this.slot === 'client.detail.tab' ? this.detailView.data?.id : null; },
        init() {
            const update = () => { this.closeFrames(); if (this.active()) this.loadSlots(); };
            this.$watch('token', update); this.$watch('currentView', update);
            this.$watch('detailView.open', update);
            this.$watch(() => this.detailView.data?.id, () => { if (this.slot === 'client.detail.tab') update(); });
            this.$watch('detailView.tab', () => { if (this.slot === 'client.detail.tab') update(); });
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
                    for (const placement of app.manifest.placements.filter(p => p.slot === this.slot)) {
                        entries.push({key: app.id + ':' + placement.id, app, placement, result: null, error: ''});
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
        }
    }; };

    window.pluginHub = function () { return {
        enabled: false, hubLoaded: false, hubBusy: false, hubError: '', hubApps: [], catalog: null,
        selected: null, selectedScopes: [], selectedUsers: [], configurationText: '{}', manifestText: '',
        oneTimeSecret: '', diagnostic: '', authorization: null,
        init() {
            const load = () => { this.oneTimeSecret = ''; this.hubApps = []; this.catalog = null; this.selected = null; this.hubError = ''; if (this.token && this.currentView === 'plugins') this.loadHub(); };
            this.$watch('token', () => { load(); if (this.token && this.authorization) this.selectView('plugins'); }); this.$watch('currentView', load); load();
            const query = new URLSearchParams(location.search);
            if (query.has('plugin_authorize')) {
                this.authorization = Object.fromEntries(['response_type','redirect_uri','code_challenge','code_challenge_method','state'].map(key => [key, query.get(key)]));
                this.authorization.app_id = query.get('plugin_authorize');
                if (this.token) this.selectView('plugins');
            }
        },
        async loadHub() {
            const session = this.token;
            try {
                const status = await this.api('/plugins/status');
                if (session !== this.token || this.currentView !== 'plugins') return;
                this.enabled = status.enabled; this.hubLoaded = true;
                if (!status.enabled) return;
                const apps = await this.api('/plugins/apps');
                const catalog = this.user?.role === 'admin' ? await this.api('/plugins/catalog') : null;
                if (session !== this.token || this.currentView !== 'plugins') return;
                this.hubApps = apps; this.catalog = catalog;
            } catch (error) { if (session === this.token) this.hubError = error.message; }
        },
        async hubAction(action) {
            if (this.hubBusy) return;
            const session = this.token; this.hubBusy = true; this.hubError = '';
            try { await action(); if (session === this.token) await this.loadHub(); }
            catch (error) { if (session === this.token) this.hubError = error.message; }
            finally { this.hubBusy = false; }
        },
        editApp(app) {
            this.selected = app; this.selectedScopes = [...(app.approved_scopes.length ? app.approved_scopes : app.manifest.scopes)];
            this.selectedUsers = [...(app.allowed_users?.length ? app.allowed_users : [this.user.id])];
            this.configurationText = JSON.stringify(app.configuration || {}, null, 2);
            this.manifestText = JSON.stringify(app.manifest, null, 2); this.diagnostic = '';
        },
        async installApp() {
            await this.hubAction(async () => {
                const app = await this.api('/plugins/apps/' + this.selected.id + '/install', {method: 'POST', body: JSON.stringify({revision: this.selected.revision, scopes: this.selectedScopes, allowed_users: this.selectedUsers, configuration: JSON.parse(this.configurationText)})});
                this.editApp(app);
            });
        },
        async stateApp(action) {
            await this.hubAction(async () => {
                const app = await this.api('/plugins/apps/' + this.selected.id + '/' + action, {method: 'POST', body: JSON.stringify({revision: this.selected.revision})}); this.editApp(app);
            });
        },
        async registerApp(update = false) {
            await this.hubAction(async () => {
                const app = await this.api(update ? '/plugins/apps/' + this.selected.id + '/manifest' : '/plugins/apps', {method: update ? 'PUT' : 'POST', body: JSON.stringify(JSON.parse(this.manifestText))}); this.editApp(app);
            });
        },
        async consentApp(app, revoke = false) {
            await this.hubAction(() => this.api('/plugins/apps/' + app.id + '/consent', {method: revoke ? 'DELETE' : 'POST', ...(revoke ? {} : {body: JSON.stringify({revision: app.revision, scopes: app.approved_scopes})})}));
            this.$dispatch('plugins-changed');
        },
        async showSecret(app, credentials = false) {
            await this.hubAction(async () => {
                const session = this.token;
                const result = await this.api('/plugins/apps/' + app.id + '/' + (credentials ? 'credentials' : 'personal-token'), {method:'POST', body: JSON.stringify(credentials ? {} : {days: 1})});
                if (session === this.token && this.currentView === 'plugins') this.oneTimeSecret = JSON.stringify(result, null, 2);
                if (credentials) this.selected = null;
            });
        },
        async revokeAppTokens(app) { await this.hubAction(() => this.api('/plugins/apps/' + app.id + '/tokens', {method:'DELETE'})); this.oneTimeSecret = ''; },
        async inspectApp(kind) {
            await this.hubAction(async () => { this.diagnostic = JSON.stringify(await this.api('/plugins/apps/' + this.selected.id + '/' + kind), null, 2); });
        },
        async completeAuthorization(app) {
            await this.hubAction(async () => {
                const {app_id, ...params} = this.authorization;
                const session = this.token;
                const result = await this.api('/plugins/apps/' + app.id + '/authorize', {method:'POST', body:JSON.stringify(params)});
                if (session !== this.token || this.currentView !== 'plugins') return;
                const redirect = new URL(result.redirect_uri);
                if (redirect.protocol !== 'https:' || !app.manifest.redirect_uris.includes(result.redirect_uri)) throw new Error(t('Błąd aplikacji'));
                redirect.searchParams.set('code', result.code); redirect.searchParams.set('state', result.state); location.assign(redirect.href);
            });
        }
    }; };
})();
