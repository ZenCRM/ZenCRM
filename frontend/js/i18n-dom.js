/* Only explicitly marked system copy is translated. Never scan user content. */
(() => {
    const i18n = window.ZenI18n;
    document.querySelectorAll('[data-i18n]').forEach(node => {
        node.textContent = i18n.t(node.dataset.i18n);
    });
    for (const attr of ['placeholder', 'title', 'aria-label', 'alt']) {
        document.querySelectorAll(`[data-i18n-${attr}]`).forEach(node => {
            node.setAttribute(attr, i18n.t(node.getAttribute(`data-i18n-${attr}`)));
        });
    }
    const title = document.querySelector('title[data-i18n-title]');
    if (title) document.title = i18n.t(title.dataset.i18nTitle);
    if (new URLSearchParams(location.search).get('embed') === '1') return;
    const label = document.createElement('label');
    label.textContent = i18n.t('Język') + ' ';
    const select = document.createElement('select');
    select.setAttribute('aria-label', i18n.t('Język'));
    for (const [value, name] of [['pl', 'Polski'], ['en', 'English']]) {
        const option = document.createElement('option');
        option.value = value; option.textContent = i18n.t(name); select.append(option);
    }
    select.value = i18n.locale;
    select.addEventListener('change', () => {
        if (!confirm(i18n.t('Zmiana języka odświeży stronę. Odrzucić niezapisane zmiany?'))) {
            select.value = i18n.locale; return;
        }
        localStorage.setItem('zen-locale', select.value); location.reload();
    });
    label.append(select);
    document.querySelector('header')?.append(label);
})();
