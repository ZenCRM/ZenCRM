/* Platform administration works even while the platform itself is disabled. */
window.pluginOptions = function () { return {
    optionEnabled: false, optionLocked: false, optionReady: false, optionBusy: false,
    optionError: '', optionSaved: '', optionSerial: 0,
    active() { return !!this.token && this.user?.role === 'admin' && this.currentView === 'settings' && this.settingsTab === 'plugins'; },
    init() {
        const update = () => {
            this.optionSerial++; this.optionReady = false; this.optionSaved = ''; this.optionError = '';
            if (this.active()) this.loadOptions();
        };
        this.$watch('token', update); this.$watch('currentView', update); this.$watch('settingsTab', update); update();
    },
    async loadOptions() {
        const session = this.token, serial = ++this.optionSerial;
        try {
            const result = await this.api('/plugins/settings');
            if (session !== this.token || serial !== this.optionSerial || !this.active()) return;
            this.optionEnabled = result.configured_enabled; this.optionLocked = result.server_locked; this.optionReady = true;
        } catch (error) { if (session === this.token && serial === this.optionSerial && this.active()) this.optionError = error.message; }
    },
    async saveOptions() {
        if (!this.optionReady || this.optionBusy || this.optionLocked || !this.active()) return;
        const session = this.token, serial = this.optionSerial;
        this.optionBusy = true; this.optionError = ''; this.optionSaved = '';
        try {
            const result = await this.api('/plugins/settings', {method:'PUT', body:JSON.stringify({enabled:this.optionEnabled})});
            if (session !== this.token || serial !== this.optionSerial || !this.active()) return;
            this.optionEnabled = result.configured_enabled; this.optionLocked = result.server_locked;
            this.optionSaved = window.ZenI18n.t('Ustawienia zapisane'); this.$dispatch('plugins-changed');
        } catch (error) { if (session === this.token && serial === this.optionSerial && this.active()) this.optionError = error.message; }
        finally { this.optionBusy = false; }
    }
}; };
