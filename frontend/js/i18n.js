/* Polish source messages are stable catalog keys. User content is never translated. */
window.ZenI18n = {
    stageLabels: {new:'Nowy',contacted:'Kontakt',qualified:'Kwalifikowany',proposal:'Oferta',negotiation:'Negocjacje',won:'Wygrany',lost:'Przegrany'},
    taskStageLabels: {todo:'Do zrobienia', in_progress:'W toku', done:'Zrobione'},
    taskStage(stage) {
        return {...stage, label: stage.label === this.taskStageLabels[stage.id] ? this.t(stage.label) : stage.label};
    },
    locale: localStorage.getItem('zen-locale') === 'en' ? 'en' : 'pl',
    t(key, params = {}) {
        if (typeof key !== 'string') return key;
        const own = (catalog, name) => catalog && Object.prototype.hasOwnProperty.call(catalog, name) ? catalog[name] : undefined;
        const message = own(window.ZenLocales[this.locale], key) ?? own(window.ZenLocales.pl, key) ?? key;
        return message.replace(/\{([^{}]+)\}/g, (match, name) => Object.prototype.hasOwnProperty.call(params, name) ? String(params[name]) : match);
    },
};
if (typeof document !== 'undefined') document.documentElement.lang=window.ZenI18n.locale;
window.ZenModules = window.ZenModules || {};
window.ZenModules.locale = () => ({
    locale: window.ZenI18n.locale,
    t(key,params) { return window.ZenI18n.t(key,params); },
    setLocale(locale) {
        if (!['pl','en'].includes(locale) || locale===this.locale) return;
        if ((this.modal?.open || this.journal?.open || this.templateModal?.open || this.detailView?.newComment?.trim()) && !confirm(this.t('Zmiana języka odświeży stronę. Odrzucić niezapisane zmiany?'))) return;
        localStorage.setItem('zen-locale',locale); location.reload();
    },
});
