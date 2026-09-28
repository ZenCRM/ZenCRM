/* Shared portal UI. Portal sessions never use CRM access tokens. */
(() => {
    const manager = document.body.dataset.admin === 'true';
    const isDark = new URLSearchParams(location.search).get('dark') === '1' || localStorage.getItem('darkMode') === 'true';
    if (isDark) { document.documentElement.classList.add('dark'); document.body.classList.add('dark'); }
    const root = document.querySelector('#app');
    const message = document.querySelector('#message');
    const entityNames = {clients:'Klienci', leads:'Leady', contacts:'Kontakty', tasks:'Zadania', meetings:'Spotkania', services:'Usługi', service_catalog:'Katalog usług', documents:'Dokumenty', offers:'Oferty', templates:'Szablony', users:'Użytkownicy'};
    const kinds = {document:'Dokumenty', offer:'Oferty', ticket:'Tickety', service:'Informacje o usługach', info:'Informacje'};
    let configuration = {address:'/portal.html', enabled:true, modules:Object.keys(kinds), logo:'', login_background:''};
    const embed = new URLSearchParams(location.search).get('embed') === '1';
    if (manager && embed) document.body.classList.add('embedded');
    function portalLink() {
        const url = new URL(configuration.address, location.origin);
        return url.href;
    }
    function applyBranding() {
        let logo = document.querySelector('#portal-logo');
        if (!logo) { logo = el('img'); logo.id = 'portal-logo'; logo.alt = 'Logo portalu'; document.querySelector('header').prepend(logo); }
        logo.hidden = !configuration.logo;
        if (configuration.logo) {
            logo.src = configuration.logo;
            logo.onerror = () => { logo.hidden = true; };
            logo.onload = () => { logo.hidden = false; };
        }
        document.body.style.backgroundImage = configuration.login_background ? 'url(' + JSON.stringify(configuration.login_background) + ')' : '';
        document.body.classList.add('portal-login');
    }
    let portalToken = sessionStorage.getItem('portalToken') || '';
    let spaceId = Number(sessionStorage.getItem('portalSpace') || 0);
    let isAdmin = false;
    function el(tag, text, parent) { const node = document.createElement(tag); if (text != null) node.textContent = text; if (parent) parent.append(node); return node; }
    function error(e) { message.textContent = e.message || String(e); }
    async function run(action, button) {
        message.textContent = '';
        if (button) button.disabled = true;
        try { await action(); } catch (e) { error(e); } finally { if (button) button.disabled = false; }
    }
    async function api(path, method = 'GET', data, raw = false) {
        const headers = manager ? {Authorization:'Bearer ' + (localStorage.getItem('token') || '')} : {'X-Portal-Token':portalToken};
        const options = {method, headers};
        if (data instanceof FormData) options.body = data;
        else if (data !== undefined) { headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(data); }
        const response = await fetch('/api' + path, options);
        if (!response.ok) {
            const problem = await response.json().catch(() => ({}));
            if (!manager && response.status === 401 && path !== '/portal/login') { clearSession(); login(); }
            throw new Error(problem.error || (response.status === 401 ? 'Zaloguj się ponownie.' : response.status === 403 ? 'Brak uprawnień.' : 'Nie udało się zapisać lub pobrać danych.'));
        }
        return raw ? response.blob() : response.json();
    }
    function button(parent, label, action, cls = '') { const b = el('button', label, parent); b.type = 'button'; b.className = cls; b.onclick = () => run(() => action(b), b); return b; }
    function input(parent, label, type = 'text', value = '', required = false) {
        const wrap = el('label', label, parent), control = el(type === 'textarea' ? 'textarea' : 'input', null, wrap);
        if (type !== 'textarea') control.type = type;
        control.value = value; control.required = required; return control;
    }
    function select(parent, label, choices, value = '') {
        const control = el('select', null, el('label', label, parent));
        for (const [id, name] of Object.entries(choices)) { const option = el('option', name, control); option.value = id; }
        if (value !== '' || Object.prototype.hasOwnProperty.call(choices, '')) control.value = value;
        return control;
    }
    function form(parent, label, action) {
        const f = el('form', null, parent), submit = el('button', label, f); submit.type = 'submit';
        f.onsubmit = event => { event.preventDefault(); run(() => action(), submit); };
        // Keep submit at the bottom as controls are added.
        const observer = new MutationObserver(() => { if (f.lastChild !== submit) f.append(submit); });
        observer.observe(f, {childList:true});
        return f;
    }
    const base = () => '/portal/spaces/' + spaceId;
    function clearSession() { portalToken = ''; sessionStorage.removeItem('portalToken'); sessionStorage.removeItem('portalSpace'); document.querySelector('#logout').hidden = true; }
    function login() {
        root.replaceChildren();
        applyBranding();
        const section = el('section', null, root); section.className = 'login-card';
        el('span', 'STREFA KLIENTA', section).className = 'eyebrow';
        el('h2', 'Zaloguj się do portalu', section);
        el('p', 'Dokumenty, oferty i kontakt z Twoim opiekunem w jednym miejscu.', section).className = 'section-lead';
        if (!configuration.enabled) { el('p', 'Portal użytkownika jest obecnie wyłączony.', section); return; }
        const f = form(section, 'Zaloguj', async () => {
            const result = await api('/portal/login', 'POST', {email:email.value, password:password.value});
            portalToken = result.token; spaceId = result.space_id;
            sessionStorage.setItem('portalToken', portalToken); sessionStorage.setItem('portalSpace', spaceId);
            await showSpace();
        });
        const email = input(f, 'Email', 'email', '', true); email.autocomplete = 'username';
        const password = input(f, 'Hasło', 'password', '', true); password.autocomplete = 'current-password';
    }
    async function showSpace() {
        const space = await api(base()); root.replaceChildren();
        if (!manager) { document.body.style.backgroundImage = ''; document.body.classList.remove('portal-login'); }
        if (!manager) document.querySelector('#logout').hidden = false;
        const section = el('section', null, root); section.className = 'portal-space';
        const hero = el('div', null, section); hero.className = 'portal-hero';
        const heroCopy = el('div', null, hero); el('span', 'TWOJA PRZESTRZEŃ', heroCopy).className = 'eyebrow';
        el('h2', space.name, heroCopy); el('p', space.description || 'Witaj w portalu klienta.', heroCopy).className = 'content section-lead';
        if (manager) {
            const heroActions = el('div', null, hero); heroActions.className = 'actions';
            button(heroActions, 'Wróć do portali', portalsPanel, 'secondary');
            const link = el('a', 'Otwórz portal', heroActions); link.className = 'button-link'; link.href = portalLink(); link.target = '_blank'; link.rel = 'noopener';
            const edit = el('details', null, section); el('summary', 'Informacje powitalne portalu', edit);
            const ef = form(edit, 'Zapisz', async () => {
                await api(base(), 'PUT', {description:desc.value, ...(!space.client_id ? {name:name.value} : {})});
                await showSpace();
            });
            if (space.client_id) el('p', 'Nazwa portalu jest pobierana z klienta.', ef).className = 'muted';
            const name = space.client_id ? null : input(ef, 'Nazwa', 'text', space.name, true);
            const desc = input(ef, 'Opis powitalny', 'textarea', space.description);
        }
        if (manager) el('p', 'Dokumenty, oferty i usługi pojawiają się automatycznie z karty klienta. Tutaj dodasz ticket lub informację.', section).className = 'section-lead portal-source-note';
        function addItemForm(kind, summary, submit) {
            const add = el('details', null, section); add.className = 'action-panel'; el('summary', summary, add);
            const f = form(add, submit, async () => {
                await api(base() + '/items', 'POST', {kind, title:title.value, content:content.value});
                await showSpace();
            });
            const title = input(f, 'Tytuł', 'text', '', true), content = input(f, 'Treść', 'textarea');
            content.required = kind === 'ticket';
        }
        if (manager || configuration.modules.includes('ticket')) addItemForm('ticket', manager ? 'Dodaj ticket' : 'Zgłoś ticket', manager ? 'Dodaj ticket' : 'Wyślij ticket');
        if (manager) addItemForm('info', 'Dodaj informację', 'Dodaj informację');
        const filters = el('nav', null, section), list = el('div', null, section); filters.className = 'filter-bar'; list.className = 'item-list';
        const draw = filter => { list.replaceChildren(); for (const item of space.items.filter(i => !filter || i.kind === filter)) itemCard(list, item); if (!list.children.length) el('p', 'Brak materiałów.', list); };
        button(filters, 'Wszystko', () => draw(''), 'secondary');
        for (const [key, label] of Object.entries(kinds)) if (manager || configuration.modules.includes(key)) button(filters, label, () => draw(key), 'secondary');
        draw('');
    }
    function itemCard(parent, item) {
        const card = el('article', null, parent), path = base() + '/items/' + item.id;
        card.className = 'item-card';
        const dateStr = item.created_at ? (' · ' + new Date(item.created_at + (item.created_at.endsWith('Z') ? '' : 'Z')).toLocaleString('pl-PL')) : '';
        el('p', kinds[item.kind] + (item.kind === 'ticket' ? ' · ' + ({open:'Otwarte', in_progress:'W realizacji', closed:'Zamknięte'}[item.status] || item.status) : '') + dateStr, card).className = 'badge';
        el('h3', item.title, card); el('p', item.content, card).className = 'content';
        if (item.filename) button(card, 'Pobierz: ' + item.filename, async () => {
            const blob = await api(path + '/file', 'GET', undefined, true), url = URL.createObjectURL(blob), a = el('a');
            a.href = url; a.download = item.filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
        });
        if (manager && item.kind === 'info' && !item.is_client_record) {
            const edit = el('details', null, card); el('summary', 'Edytuj informację', edit);
            const f = form(edit, 'Zapisz zmiany', async () => { await api(path, 'PUT', {title:title.value, content:content.value}); await showSpace(); });
            const title = input(f, 'Tytuł', 'text', item.title, true), content = input(f, 'Treść', 'textarea', item.content);
            button(edit, 'Usuń informację', async () => { if (confirm('Usunąć informację?')) { await api(path, 'DELETE'); await showSpace(); } }, 'danger');
        }
        if (item.kind === 'ticket') {
            const thread = el('details', null, card); el('summary', 'Odpowiedzi', thread);
            const replies = el('div', null, thread);
            const load = async () => { const rows = await api(path + '/replies'); replies.replaceChildren(); for (const r of rows) { const row = el('div', null, replies); row.className = 'reply'; el('p', r.author + ' · ' + new Date(r.created_at + (r.created_at.endsWith('Z') ? '' : 'Z')).toLocaleString('pl-PL'), row).className = 'muted'; el('p', r.content, row).className = 'content'; } };
            thread.addEventListener('toggle', () => { if (thread.open) run(load); });
            if (item.status !== 'closed') {
                const f = form(thread, 'Wyślij odpowiedź', async () => { await api(path + '/replies', 'POST', {content:answer.value}); answer.value = ''; await load(); });
                const answer = input(f, 'Odpowiedź', 'textarea', '', true);
            } else {
                el('p', 'Zgłoszenie zostało zamknięte. Dodawanie odpowiedzi jest zablokowane.', thread).className = 'muted ticket-closed-note';
            }
        }
    }
    async function fieldsPanel() {
        const fields = await api('/custom-fields'); root.replaceChildren();
        const section = el('section', null, root); section.className = 'admin-page fields-page';
        el('span', 'USTAWIENIA CRM', section).className = 'eyebrow'; el('h2', 'Pola własne', section);
        el('p', 'Dodaj własne informacje do klientów, leadów i pozostałych rekordów.', section).className = 'section-lead';
        const f = form(section, 'Dodaj pole', async () => { await api('/custom-fields', 'POST', {entity:entity.value, label:label.value, kind:kind.value}); await fieldsPanel(); });
        f.className = 'form-card form-grid';
        const entity = select(f, 'Element', entityNames), label = input(f, 'Nazwa pola', 'text', '', true), kind = select(f, 'Typ', {text:'Tekst', textarea:'Długi tekst', number:'Liczba', date:'Data', boolean:'Tak / Nie'});
        const list = el('div', null, section); list.className = 'definition-list';
        for (const field of fields) {
            const row = el('article', null, list); row.className = 'definition-row';
            const copy = el('div', null, row); el('strong', field.label, copy); el('p', entityNames[field.entity] + ' · ' + ({text:'Tekst', textarea:'Długi tekst', number:'Liczba', date:'Data', boolean:'Tak / Nie'}[field.kind] || field.kind), copy).className = 'muted';
            button(row, 'Usuń', async () => { if (confirm('Usunąć pole i wszystkie jego wartości?')) { await api('/custom-fields/' + field.id, 'DELETE'); await fieldsPanel(); } }, 'danger ghost-danger');
        }
        if (!fields.length) el('p', 'Nie utworzono jeszcze żadnych pól własnych.', list).className = 'empty-state';
    }
    async function valuesPanel() {
        const fields = await api('/custom-fields'); root.replaceChildren();
        const section = el('section', null, root); section.className = 'admin-page fields-page';
        el('span', 'USTAWIENIA CRM', section).className = 'eyebrow'; el('h2', 'Wartości pól własnych', section);
        el('p', 'Wybierz typ elementu i rekord, aby uzupełnić jego dodatkowe dane.', section).className = 'section-lead';
        const entity = select(section, 'Element', {'':'Wybierz element', ...entityNames});
        const records = el('div', null, section), values = el('div', null, section); let selection = 0;
        entity.onchange = () => run(async () => {
            const version = ++selection; records.replaceChildren(); values.replaceChildren(); if (!entity.value) return;
            const selectedEntity = entity.value;
            const response = await api('/' + selectedEntity.replace('service_catalog', 'service-catalog'));
            if (version !== selection) return;
            const rows = Array.isArray(response) ? response : (response.items || response.clients || []);
            if (selectedEntity === 'clients') {
                for (let page = 2; page <= (response.pages || 1); page++) {
                    const next = await api('/clients?page=' + page);
                    if (version !== selection) return;
                    rows.push(...next.clients);
                }
            }
            const options = {'':'Wybierz rekord'};
            for (const row of rows) options[row.id] = (row.name || row.title || row.email || row.first_name || 'Rekord') + ' (#' + row.id + ')';
            const record = select(records, 'Rekord', options);
            record.onchange = () => run(async () => {
                const version = ++selection; values.replaceChildren(); if (!record.value) return;
                const path = '/custom-fields/' + selectedEntity + '/' + record.value;
                const data = await api(path); if (version !== selection) return;
                const relevant = fields.filter(f => f.entity === selectedEntity);
                if (!relevant.length) { el('p', 'Brak zdefiniowanych pól dla tego elementu.', values); return; }
                const controls = {};
                const f = form(values, 'Zapisz pola', async () => { await api(path, 'PUT', Object.fromEntries(Object.entries(controls).map(([id, control]) => [id, control.value]))); message.textContent = 'Pola zapisane.'; });
                for (const field of relevant) controls[field.id] = field.kind === 'boolean' ? select(f, field.label, {'':'—', true:'Tak', false:'Nie'}, data[field.id] || '') : input(f, field.label, field.kind, data[field.id] || '');
            });
        });
    }
    async function allClients() {
        const first = await api('/clients');
        const rows = first.clients || [];
        for (let page = 2; page <= first.pages; page++) rows.push(...(await api('/clients?page=' + page)).clients);
        return rows;
    }
    function checkbox(parent, label, checked) {
        const control = input(parent, label, 'checkbox'); control.checked = checked;
        control.parentElement.className = 'checkbox-row'; return control;
    }
    const ticketStatuses = {open:'Otwarte', in_progress:'W realizacji', closed:'Zamknięte'};
    async function ticketsPanel() {
        const tickets = await api('/portal/tickets'); root.replaceChildren();
        const section = el('section', null, root); section.className = 'admin-page tickets-page';
        el('span', 'PORTAL UŻYTKOWNIKA', section).className = 'eyebrow'; el('h2', 'Tickety', section);
        el('p', 'Wiadomości i zgłoszenia przesłane przez użytkowników portalu.', section).className = 'section-lead';
        const toolbar = el('div', null, section); toolbar.className = 'ticket-toolbar';
        const statusFilter = select(toolbar, 'Status', {'':'Wszystkie', ...ticketStatuses});
        const clientNames = [...new Set(tickets.map(ticket => ticket.client_name).filter(Boolean))].sort();
        const clientFilter = select(toolbar, 'Klient', {'':'Wszyscy klienci', ...Object.fromEntries(clientNames.map(name => [name, name]))});
        const list = el('div', null, section); list.className = 'ticket-list';
        const draw = () => {
            list.replaceChildren();
            const visible = tickets.filter(ticket => (!statusFilter.value || ticket.status === statusFilter.value) && (!clientFilter.value || ticket.client_name === clientFilter.value));
            for (const ticket of visible) ticketAdminCard(list, ticket);
            if (!visible.length) el('p', 'Brak ticketów dla wybranych filtrów.', list).className = 'empty-state';
        };
        statusFilter.onchange = draw; clientFilter.onchange = draw; draw();
    }
    function ticketAdminCard(parent, ticket) {
        const card = el('article', null, parent); card.className = 'ticket-card';
        const top = el('div', null, card); top.className = 'ticket-card-top';
        const copy = el('div', null, top); el('span', ticket.client_name || ticket.space_name || 'Portal klienta', copy).className = 'eyebrow'; el('h3', ticket.title, copy);
        el('span', ticketStatuses[ticket.status] || ticket.status, top).className = 'status-pill ' + ticket.status;
        el('p', ticket.content || 'Brak opisu.', card).className = 'content';
        el('p', new Date(ticket.created_at + (ticket.created_at.endsWith('Z') ? '' : 'Z')).toLocaleString('pl-PL') + ' · ' + ticket.reply_count + ' odp.', card).className = 'muted';
        const controls = el('div', null, card); controls.className = 'ticket-controls';
        const status = select(controls, 'Status', ticketStatuses, ticket.status);
        button(controls, 'Zapisz status', async () => {
            await api('/portal/spaces/' + ticket.space_id + '/items/' + ticket.id, 'PUT', {status:status.value});
            await ticketsPanel(); message.textContent = 'Status ticketu został zapisany.';
        }, 'secondary');
        button(controls, 'Usuń ticket', async () => {
            if (confirm('Czy na pewno chcesz usunąć ten ticket?')) {
                await api('/portal/spaces/' + ticket.space_id + '/items/' + ticket.id, 'DELETE');
                await ticketsPanel();
                message.textContent = 'Ticket został usunięty.';
            }
        }, 'danger ghost-danger');
        const thread = el('details', null, card); thread.className = 'ticket-thread'; el('summary', 'Odpowiedzi (' + ticket.reply_count + ')', thread);
        const replies = el('div', null, thread);
        const path = '/portal/spaces/' + ticket.space_id + '/items/' + ticket.id + '/replies';
        const loadReplies = async () => {
            const rows = await api(path); replies.replaceChildren();
            for (const reply of rows) {
                const row = el('div', null, replies); row.className = 'reply';
                el('p', reply.author + ' · ' + new Date(reply.created_at + (reply.created_at.endsWith('Z') ? '' : 'Z')).toLocaleString('pl-PL'), row).className = 'muted';
                el('p', reply.content, row).className = 'content';
            }
            if (!rows.length) el('p', 'Brak odpowiedzi.', replies).className = 'muted';
        };
        thread.addEventListener('toggle', () => { if (thread.open) run(loadReplies); });
        if (ticket.status !== 'closed') {
            const f = form(thread, 'Wyślij odpowiedź', async () => {
                await api(path, 'POST', {content:answer.value}); answer.value = ''; await loadReplies();
            });
            const answer = input(f, 'Odpowiedź dla użytkownika', 'textarea', '', true);
        }
    }
    async function portalsPanel() {
        const [spaces, clients] = await Promise.all([api('/portal/spaces'), allClients()]); root.replaceChildren();
        const section = el('section', null, root); section.className = 'admin-page portals-page';
        el('span', 'PORTAL UŻYTKOWNIKA', section).className = 'eyebrow'; el('h2', 'Portale', section);
        el('p', 'Portale pobierają dokumenty, oferty i usługi z kart klientów. Ręcznie dodasz tylko tickety oraz informacje.', section).className = 'section-lead';
        const assigned = new Set(spaces.map(space => space.client_id).filter(Boolean));
        const availableClients = clients.filter(client => !assigned.has(client.id));
        const clientChoices = {'':'Wybierz klienta', ...Object.fromEntries(availableClients.map(client => [client.id, client.name]))};
        const create = el('details', null, section); create.className = 'create-user-card'; el('summary', 'Utwórz portal dla klienta', create);
        const createForm = form(create, 'Utwórz portal', async () => {
            await api('/portal/spaces', 'POST', {client_id:Number(client.value), description:description.value});
            await portalsPanel(); message.textContent = 'Portal klienta został utworzony.';
        });
        createForm.className = 'form-grid';
        const client = select(createForm, 'Klient', clientChoices); client.required = true;
        const description = input(createForm, 'Opis powitalny', 'textarea');
        if (!availableClients.length) {
            client.disabled = true; createForm.querySelector('button[type="submit"]').disabled = true;
            el('p', 'Każdy aktywny klient ma już przypisany portal.', create).className = 'muted';
        }
        const clientsById = Object.fromEntries(clients.map(item => [item.id, item]));
        const grid = el('div', null, section); grid.className = 'portal-grid';
        for (const space of spaces) {
            const card = el('article', null, grid); card.className = 'portal-card';
            el('span', space.client_id ? (clientsById[space.client_id]?.name || 'Klient') : 'Nieprzypisany', card).className = 'eyebrow';
            el('h3', space.name, card); el('p', space.description || 'Bez opisu powitalnego.', card).className = 'muted';
            const actions = el('div', null, card); actions.className = 'actions';
            button(actions, 'Zarządzaj zawartością', async () => { spaceId = space.id; await showSpace(); });
            button(actions, 'Usuń portal', async () => {
                if (confirm('Czy na pewno chcesz usunąć portal „' + space.name + '” wraz ze wszystkimi materiałami i odpowiedziami?')) {
                    await api('/portal/spaces/' + space.id, 'DELETE');
                    await portalsPanel();
                    message.textContent = 'Portal został usunięty.';
                }
            }, 'danger ghost-danger');
            if (!space.client_id) {
                const assign = el('details', null, card); el('summary', 'Przypisz do klienta', assign);
                const assignForm = form(assign, 'Przypisz', async () => {
                    await api('/portal/spaces/' + space.id + '/client', 'PUT', {client_id:Number(target.value)}); await portalsPanel();
                });
                const target = select(assignForm, 'Klient', clientChoices); target.required = true;
            }
        }
        if (!spaces.length) el('p', 'Nie utworzono jeszcze żadnego portalu.', grid).className = 'empty-state';
    }
    async function settingsPanel() {
        configuration = await api('/portal/configuration'); root.replaceChildren();
        const section = el('section', null, root); section.className = 'admin-page settings-page';
        const heading = el('div', null, section); heading.className = 'page-heading';
        const headingCopy = el('div', null, heading); el('span', 'PORTAL UŻYTKOWNIKA', headingCopy).className = 'eyebrow'; el('h2', 'Ustawienia portalu', headingCopy);
        el('p', 'Dopasuj wygląd, adres i zakres informacji dostępnych dla klientów.', headingCopy).className = 'section-lead';
        const openLink = el('a', 'Otwórz portal ↗', heading); openLink.className = 'button-link secondary'; openLink.href = portalLink(); openLink.target = '_blank'; openLink.rel = 'noopener';
        const controls = {}, modules = {};
        const f = form(section, 'Zapisz ustawienia portalu', async () => {
            configuration = await api('/portal/configuration', 'PUT', {
                address:controls.address.value.trim(), logo:controls.logo.value.trim(), login_background:controls.login_background.value.trim(),
                enabled:controls.enabled.checked, modules:Object.entries(modules).filter(([, c]) => c.checked).map(([id]) => id)
            });
            await settingsPanel(); message.textContent = 'Ustawienia portalu zapisane.';
        });
        f.className = 'settings-form';
        const basics = el('div', null, f); basics.className = 'form-card';
        el('h3', 'Dostęp i adres', basics); el('p', 'Włącz portal i ustaw adres używany przez klientów.', basics).className = 'muted';
        controls.enabled = checkbox(basics, 'Portal włączony', configuration.enabled);
        controls.address = input(basics, 'Adres portalu', 'text', configuration.address, true);
        el('p', 'Np. /portal lub https://firma.pl/portal. Własna domena musi kierować na tę aplikację.', basics).className = 'field-help';
        const mediaGrid = el('div', null, f); mediaGrid.className = 'media-grid';
        for (const [key, label] of [['logo', 'Logo'], ['login_background', 'Tło logowania']]) {
            const box = el('div', null, mediaGrid); box.className = 'form-card media-card'; el('h3', label, box);
            el('p', key === 'logo' ? 'Widoczne w nagłówku i na ekranie logowania.' : 'Tło ekranu logowania do portalu.', box).className = 'muted';
            const preview = el('div', null, box); preview.className = 'media-preview ' + (key === 'login_background' ? 'background-preview' : 'logo-preview');
            const image = el('img', null, preview); image.alt = 'Podgląd: ' + label;
            const placeholder = el('span', key === 'logo' ? 'Brak logo' : 'Brak tła', preview);
            const updatePreview = () => { const value = controls[key].value.trim(); image.hidden = !value; placeholder.hidden = !!value; if (value) image.src = value; };
            controls[key] = input(box, 'Adres obrazu', 'text', configuration[key]); controls[key].addEventListener('input', updatePreview);
            const file = input(box, 'Lub wybierz obraz (PNG, JPG, GIF, WEBP; maks. 5 MB)', 'file'); file.accept = 'image/png,image/jpeg,image/gif,image/webp';
            const actions = el('div', null, box); actions.className = 'actions';
            button(actions, 'Wgraj obraz', async () => {
                if (!file.files[0]) throw new Error('Wybierz obraz.');
                if (file.files[0].size > 5 * 1024 * 1024) throw new Error('Maksymalny rozmiar obrazu to 5 MB.');
                const fd = new FormData(); fd.append('file', file.files[0]);
                controls[key].value = (await api('/portal/branding', 'POST', fd)).url;
                updatePreview(); file.value = ''; message.textContent = 'Obraz wgrany i widoczny w podglądzie. Zapisz ustawienia, aby go opublikować.';
            }, 'secondary');
            button(actions, 'Usuń', () => { controls[key].value = ''; updatePreview(); }, 'secondary');
            updatePreview();
        }
        const moduleCard = el('div', null, f); moduleCard.className = 'form-card'; el('h3', 'Dostępne moduły', moduleCard);
        el('p', 'Wybierz rodzaje treści, które zobaczą użytkownicy portalu.', moduleCard).className = 'muted';
        const moduleGrid = el('div', null, moduleCard); moduleGrid.className = 'module-grid';
        for (const [id, label] of Object.entries(kinds)) modules[id] = checkbox(moduleGrid, label, configuration.modules.includes(id));
    }
    async function usersPanel() {
        const [members, clients] = await Promise.all([api('/portal/members'), allClients()]);
        root.replaceChildren();
        const section = el('section', null, root); section.className = 'admin-page users-page';
        el('span', 'PORTAL UŻYTKOWNIKA', section).className = 'eyebrow'; el('h2', 'Użytkownicy portalu', section);
        el('p', 'Zarządzaj dostępem klientów do ich materiałów, dokumentów i ticketów.', section).className = 'section-lead';
        const clientChoices = {'':'Wybierz klienta'};
        for (const c of clients) clientChoices[c.id] = c.name;
        function editor(parent, member = null) {
            const f = form(parent, member ? 'Zapisz użytkownika' : 'Utwórz użytkownika', async () => {
                await api('/portal/members' + (member ? '/' + member.id : ''), member ? 'PUT' : 'POST',
                    {client_id:Number(client.value), email:email.value, password:password.value, active:active.checked});
                await usersPanel(); message.textContent = member ? 'Użytkownik zapisany.' : 'Użytkownik utworzony.';
            });
            f.className = 'form-grid';
            const client = select(f, 'Klient', clientChoices, member?.client_id || ''); client.required = true;
            const email = input(f, 'Email / login', 'email', member?.email || '', true);
            const password = input(f, member ? 'Nowe hasło (puste = bez zmiany)' : 'Hasło (min. 10 znaków)', 'password', '', !member);
            password.minLength = 10; password.autocomplete = 'new-password';
            const active = checkbox(f, 'Konto aktywne', member ? member.active : true);
        }
        const create = el('details', null, section); create.className = 'create-user-card'; create.open = !members.length; el('summary', 'Dodaj użytkownika portalu', create); editor(create);
        const filter = select(section, 'Filtruj według klienta', {'':'Wszyscy klienci', ...Object.fromEntries(clients.map(c => [c.id, c.name]))});
        const list = el('div', null, section);
        const draw = () => {
            list.replaceChildren();
            for (const member of members.filter(m => !filter.value || String(m.client_id) === filter.value)) {
                const row = el('article', null, list); row.className = 'user-row';
                const identity = el('div', null, row); const avatar = el('span', (member.email[0] || '?').toUpperCase(), identity); avatar.className = 'user-avatar';
                const copy = el('div', null, identity); el('h3', member.email, copy); el('p', member.client_name || 'Nie przypisano klienta', copy).className = 'muted'; identity.className = 'user-identity';
                el('span', member.active ? 'Aktywny' : 'Wyłączony', row).className = 'status-pill ' + (member.active ? 'active' : 'inactive');
                const actions = el('div', null, row); actions.className = 'actions';
                const link = el('a', 'Link do logowania', actions); link.href = portalLink(); link.target = '_blank'; link.rel = 'noopener';
                button(actions, 'Materiały klienta', async () => { spaceId = member.space_id; await showSpace(); }, 'secondary');
                const edit = el('details', null, row); edit.className = 'inline-editor'; el('summary', 'Edytuj użytkownika', edit); editor(edit, member);
                button(row, 'Usuń użytkownika', async () => {
                    if (!confirm('Usunąć konto ' + member.email + '? Materiały klienta pozostaną.')) return;
                    await api('/portal/members/' + member.id, 'DELETE'); await usersPanel();
                }, 'danger');
            }
            if (!list.children.length) el('p', 'Brak użytkowników.', list);
        };
        filter.onchange = draw; draw();
    }
    async function route() {
        message.textContent = ''; root.replaceChildren();
        configuration = await api('/portal/configuration');
        if (!manager) {
            applyBranding();
            if (!configuration.enabled) { clearSession(); login(); }
            else if (portalToken && spaceId) await showSpace(); else login(); return;
        }
        const user = await api('/auth/me'); isAdmin = user.role === 'admin';
        if (location.hash === '#values') await valuesPanel();
        else if (!isAdmin) throw new Error('Ta sekcja wymaga uprawnień administratora. Wartości pól są dostępne w sekcji „Wartości pól”.');
        else if (location.hash === '#fields') await fieldsPanel();
        else if (location.hash === '#portal-settings') await settingsPanel();
        else if (location.hash === '#portal-tickets') await ticketsPanel();
        else if (location.hash === '#portal-spaces') await portalsPanel();
        else await usersPanel();
    }
    window.addEventListener('hashchange', () => run(route));
    if (!manager) document.querySelector('#logout').onclick = () => run(async () => { await api('/portal/logout', 'POST'); clearSession(); login(); });
    run(route);
})();
