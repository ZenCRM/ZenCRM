/* The menu holds authorized view descriptors, never provider HTML or executable routes. */
(function () {
    'use strict';
    const routePattern = /^plugin\/([a-z][a-z0-9-]{0,39})\/([a-z][a-z0-9-]{0,39})$/;
    let serial = 0, pending = null;
    const state = () => window.Alpine.store('pluginNavigation');
    document.addEventListener('alpine:init', () => {
        window.Alpine.store('pluginNavigation', {entries: [], session: '', ready: false, version: 0, error: ''});
    });
    const isRoute = id => typeof id === 'string' && routePattern.test(id);
    function clear() {
        serial++; pending = null;
        Object.assign(state(), {entries: [], session: '', ready: false, error: '', version: state().version + 1});
    }
    function getView(id) { return state().entries.find(entry => entry.id === id) || null; }
    async function load(ctx, force = false) {
        const token = ctx.token;
        if (!token) { clear(); return; }
        if (pending?.token === token) return pending.promise;
        if (!force && state().session === token && state().ready) return;
        const request = ++serial;
        if (state().session !== token) Object.assign(state(), {entries: [], session: token, ready: false, error: '', version: state().version + 1});
        const alive = () => request === serial && ctx.token === token;
        const promise = (async () => {
            try {
                const status = await ctx.api('/plugins/status');
                const entries = status.enabled ? await ctx.api('/plugins/views') : [];
                if (!alive()) return;
                const safe = entries.filter(entry => isRoute(entry.id) && entry.id === `plugin/${entry.app_id}/${entry.view_id}` &&
                    typeof entry.label === 'string' && typeof entry.app_name === 'string' &&
                    typeof entry.placement_id === 'string' && /^[a-z][a-z0-9-]{0,39}$/.test(entry.placement_id));
                const changed = JSON.stringify(state().entries) !== JSON.stringify(safe);
                Object.assign(state(), {entries: safe, ready: true, error: '', version: state().version + (changed ? 1 : 0)});
            } catch (error) {
                if (alive()) Object.assign(state(), {entries: [], ready: true, error: error.message, version: state().version + 1});
            } finally { if (pending?.request === request) pending = null; }
        })();
        pending = {token, request, promise};
        return promise;
    }
    window.ZenPluginNavigation = {isRoute, getView, hasView: id => isRoute(id) && !!getView(id),
        version: () => state().version, load, clear};
    window.pluginNavigation = () => ({
        menuOpen: true,
        get viewItems() { return state().entries; },
        viewLabel(entry) { return entry.bundled ? window.ZenI18n.t(entry.label) : entry.label; },
        appLabel(entry) { return entry.bundled ? window.ZenI18n.t(entry.app_name) : entry.app_name; },
        init() {
            this.$watch('token', () => { clear(); this.refreshViews(); });
            this.$watch('currentView', () => { if (isRoute(this.currentView)) { this.menuOpen = true; this.refreshViews(); } });
            this.refreshViews();
        },
        async refreshViews() {
            await load(this, true);
            if (this.token && isRoute(this.currentView) && !getView(this.currentView)) this.selectView('plugins');
        }
    });
    window.pluginRoute = () => ({
        get routeEntry() { return getView(this.currentView); },
        get routeReady() { return state().ready; },
        get routeError() { return state().error; },
        routeLabel() { const entry = this.routeEntry; return entry ? (entry.bundled ? window.ZenI18n.t(entry.label) : entry.label) : ''; },
        appLabel() { const entry = this.routeEntry; return entry ? (entry.bundled ? window.ZenI18n.t(entry.app_name) : entry.app_name) : ''; }
    });
})();
