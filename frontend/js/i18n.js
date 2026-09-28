/* Polish source messages are stable catalog keys. User content is never translated. */
window.ZenI18n = {
    stageLabels: {new:'Nowy',contacted:'Kontakt',qualified:'Kwalifikowany',proposal:'Oferta',negotiation:'Negocjacje',won:'Wygrany',lost:'Przegrany'},
    locale: localStorage.getItem('zen-locale') === 'en' ? 'en' : 'pl',
    t(key, params = {}) {
        let message = window.ZenLocales[this.locale]?.[key] ?? window.ZenLocales.pl[key] ?? key;
        for (const [name,value] of Object.entries(params)) message=message.replaceAll('{'+name+'}',String(value));
        return message;
    },
};
if (typeof document !== 'undefined') document.documentElement.lang=window.ZenI18n.locale;
window.ZenModules = window.ZenModules || {};
window.ZenModules.locale = () => ({
    locale: window.ZenI18n.locale,
    t(key,params) { return window.ZenI18n.t(key,params); },
    setLocale(locale) {
        if (!['pl','en'].includes(locale) || locale===this.locale) return;
        if ((this.modal.open || this.journal.open || this.templateModal.open || this.detailView.newComment?.trim()) && !confirm(this.t('Zmiana języka odświeży stronę. Odrzucić niezapisane zmiany?'))) return;
        localStorage.setItem('zen-locale',locale); location.reload();
    },
});
