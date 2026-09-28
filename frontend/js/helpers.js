/* ═══════════════════════════════════════════════
   ZenCRM – funkcje pomocnicze (formatowanie, etykiety)
   ═══════════════════════════════════════════════ */
window.ZenHelpers = {

    formatNumber(v) {
        if (v === null || v === undefined || v === '') return '0';
        return Number(v).toLocaleString(window.ZenI18n.locale, { maximumFractionDigits: 0 });
    },

    statusLabel(s) {
        return { active: window.ZenI18n.t('Aktywny'), inactive: window.ZenI18n.t('Nieaktywny'), prospect: window.ZenI18n.t('Prospect') }[s] || s;
    },

    priorityLabel(p) {
        return { low: window.ZenI18n.t('Niski'), medium: window.ZenI18n.t('Średni'), high: window.ZenI18n.t('Wysoki') }[p] || p;
    },

    billingLabel(c) {
        return { monthly: window.ZenI18n.t('mies.'), yearly: window.ZenI18n.t('rok'), one_time: window.ZenI18n.t('jednorazowo') }[c] || c;
    },

    offerStatusLabel(s) {
        return { draft: window.ZenI18n.t('Szkic'), sent: window.ZenI18n.t('Wysłana'), accepted: window.ZenI18n.t('Zaakceptowana'), rejected: window.ZenI18n.t('Odrzucona') }[s] || s;
    },

    docTypeLabel(t) {
        return { contract: window.ZenI18n.t('Umowa'), invoice: window.ZenI18n.t('Faktura'), report: window.ZenI18n.t('Raport'), other: window.ZenI18n.t('Inne') }[t] || t;
    },

    roleLabel(r) {
        return { admin: window.ZenI18n.t('Admin'), manager: window.ZenI18n.t('Manager'), employee: window.ZenI18n.t('Pracownik') }[r] || r;
    },

    // Format daty z backendu (ISO) → "DD.MM.YYYY"
    formatDate(iso) {
        if (!iso) return '—';
        try {
            return new Date(iso).toLocaleDateString(window.ZenI18n.locale);
        } catch { return iso; }
    },

    // Format godziny z ISO → "HH:MM"
    formatTime(iso) {
        if (!iso) return '';
        try {
            return new Date(iso).toLocaleTimeString(window.ZenI18n.locale, { hour: '2-digit', minute: '2-digit' });
        } catch { return ''; }
    },
};
