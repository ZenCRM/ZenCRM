window.ZenModules = window.ZenModules || {};
window.ZenModules.mailboxes = function () { return {
    unreadMailCount: 0,
    mailCountTimer: null,
    mailCountRequest: 0,
    async loadUnreadMailCount() {
        const session = this.token, request = ++this.mailCountRequest;
        if (!session) { this.unreadMailCount = 0; return; }
        try {
            const data = await this.api('/mailboxes/unread');
            if (session === this.token && request === this.mailCountRequest)
                this.unreadMailCount = Math.max(0, Number(data.total) || 0);
        } catch (_) { /* Preserve the last count during a temporary network failure. */ }
    },
    startMailCount() {
        this.stopMailCount();
        if (!this.token) return;
        this.loadUnreadMailCount();
        this.mailCountTimer = setInterval(() => {
            if (!document.hidden) {
                if (['mailboxes','mailSent'].includes(this.currentView) && this.mail.boxId && !this.mail.busy && !this.mail.loading && !this.mail.composing)
                    this.loadMailMessages(true);
                else this.loadUnreadMailCount();
            }
        }, 60000);
    },
    stopMailCount() {
        clearInterval(this.mailCountTimer);
        this.mailCountTimer = null; this.mailCountRequest++; this.unreadMailCount = 0;
    },
    clientMail: {clientId:null,items:[],total:0,pages:0,page:1,emails:[],loading:false,error:'',request:0},
    async writeEmail(address) {
        if (!address) return;
        if (this.user?.default_email_method !== 'crm') { window.location.href = 'mailto:' + encodeURIComponent(address.trim()); return; }
        await this.selectView('mailboxes');
        if (!this.mail.boxes.length) {
            await this.selectView('mailSettings');
            this.openMailboxConnect();
            this.mail.pendingRecipient = address;
            return;
        }
        this.composeMail(); this.addMailRecipients('to', address);
        this.$nextTick?.(() => document.getElementById('mail-compose-subject')?.focus());
    },
    clientMailDate(value) {
        const date = new Date(value + 'Z');
        return date.toLocaleDateString(this.locale, {day:'numeric',month:'short',year:'numeric'});
    },
    mailIcon(name) {
        const paths = {inbox:'M4 4h16v16H4zM4 13h5l2 3h2l2-3h5',send:'m3 3 18 9-18 9 4-9-4-9Zm4 9h14',reply:'m9 5-6 6 6 6M3 11h10a7 7 0 0 1 7 7',replyAll:'m8 5-6 6 6 6m6-12-6 6 6 6m-6-6h7a6 6 0 0 1 6 6',forward:'m15 5 6 6-6 6M21 11H11a7 7 0 0 0-7 7',download:'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5',paperclip:'m8 13 7-7a3 3 0 0 1 4 4L9 20a5 5 0 0 1-7-7L13 2',refresh:'M20 7a9 9 0 0 0-15-2L2 8m0-6v6h6m-4 9a9 9 0 0 0 15 2l3-3m0 6v-6h-6',code:'m8 6-6 6 6 6m8-12 6 6-6 6m-3-14-2 16',image:'M3 3h18v18H3zM3 17l6-6 5 5 3-3 4 4M16 7h.01',mail:'M3 5h18v14H3zM3 5l9 8 9-8'};
        return '<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="' + (paths[name] || paths.mail) + '"></path></svg>';
    },
    async loadClientMail(clientId, page = 1) {
        const state = this.clientMail, session = this.token;
        const request = ++state.request;
        if (state.clientId !== clientId) { state.items = []; state.total = 0; state.emails = []; }
        state.clientId = clientId; state.page = page; state.loading = true; state.error = '';
        try {
            const data = await this.api(`/mailboxes/clients/${clientId}/messages?page=${page}`);
            if (request !== state.request || session !== this.token) return;
            Object.assign(state, data);
        } catch (e) { if (request === state.request && session === this.token) state.error = e.message; }
        finally { if (request === state.request) state.loading = false; }
    },
    async openClientMailMessage(message) {
        await this.selectView(message.folder === 'sent' ? 'mailSent' : 'mailboxes');
        if (!this.mail.boxes.some(box => box.id === message.mailbox_id)) return;
        this.mail.boxId = message.mailbox_id; this.mail.folder = message.folder; this.mail.page = 1; this.mail.search = ''; this.mail.readFilter = '';
        await this.loadMailMessages(); await this.selectMailMessage(message);
    },
    mail: { boxes: [], teams: [], boxId: '', folder: 'inbox', items: [], selected: null, search: '', readFilter: '', unread: 0, page: 1, pages: 0, total: 0, busy: false, loading: false, error: '', connecting: false, settings: false, settingsTab: 'signature', signature: '', signatureFormat: 'text', password: '', connection: {}, composing: false, recipientInputs: {to:'',cc:'',bcc:''}, recipientErrors: {to:'',cc:'',bcc:''}, recipientFocus: '', recipientIndex: 0, showCc: false, showBcc: false, composeMode: 'new', compose: { to: '', cc: '', bcc: '', subject: '', body: '', include_signature: true }, form: {}, htmlView: true, remoteImages: false, downloading: '', syncingAll: false, cancelSync: false, syncProgress: { processed: 0, imported: 0, total: 0 } },
    get activeMailbox() { return this.mail.boxes.find(b => b.id === Number(this.mail.boxId)); },
    get mailPageTitle() { return {mailboxes:window.ZenI18n.t("Poczta: Odebrane"),mailSent:window.ZenI18n.t("Wysłane"),mailAccounts:window.ZenI18n.t("Skrzynki"),mailSettings:window.ZenI18n.t("Ustawienia poczty")}[this.currentView]; },
    get mailPageDescription() { return {mailboxes:window.ZenI18n.t("Czytaj wiadomości i odpowiadaj swoim klientom."),mailSent:window.ZenI18n.t("Wiadomości wysłane z podpiętych skrzynek w CRM."),mailAccounts:window.ZenI18n.t("Twoje skrzynki osobiste i skrzynki współdzielone z zespołem."),mailSettings:window.ZenI18n.t("Połączenia, podpisy i automatyczne sprawdzanie poczty.")}[this.currentView]; },
    async openMailAccount(boxId, view = 'mailboxes') {
        this.mail.boxId = boxId;
        await this.selectView(view);
    },
    get canManageMailbox() { const b = this.activeMailbox; return b && (!b.team_id || this.user?.role === 'admin' || this.mail.teams.find(t => t.id === b.team_id)?.leader_id === this.user?.id); },
    get mailComposeTitle() { return {new: window.ZenI18n.t("Nowa wiadomość"), reply: window.ZenI18n.t("Odpowiedź"), replyAll: window.ZenI18n.t("Odpowiedz wszystkim"), forward: window.ZenI18n.t("Przekaż wiadomość")}[this.mail.composeMode]; },
    mailRecipientList(field) { return (this.mail.compose[field] || '').split(',').map(v => v.trim()).filter(Boolean); },
    addMailRecipients(field, value = this.mail.recipientInputs[field]) {
        const valid = [], invalid = [];
        for (const token of value.split(/[,;\n\r]+/).map(v => v.trim()).filter(Boolean)) {
            const address = (token.match(/<([^<>]+)>$/)?.[1] || token).trim().toLowerCase();
            if (/^[^\s@<>;,]+@[^\s@<>;,]+\.[^\s@<>;,]+$/.test(address)) valid.push(address);
            else invalid.push(token);
        }
        this.mail.compose[field] = [...new Set([...this.mailRecipientList(field), ...valid])].join(', ');
        this.mail.recipientInputs[field] = invalid.join(', ');
        this.mail.recipientErrors[field] = invalid.length ? window.ZenI18n.t("Sprawdź adres: ") + invalid.join(', ') : '';
        this.mail.recipientFocus = ''; this.mail.recipientIndex = 0;
        return !invalid.length;
    },
    removeMailRecipient(field, address) { this.mail.compose[field] = this.mailRecipientList(field).filter(v => v !== address).join(', '); },
    mailRecipientSuggestions(field) {
        const query = (this.mail.recipientInputs?.[field] || '').trim().toLowerCase();
        if (!query) return [];
        const added = new Set(['to','cc','bcc'].flatMap(key => this.mailRecipientList(key)));
        const seen = new Set();
        return [...(this.contacts || []), ...(this.clients || [])].map(person => ({email:(person.email || '').trim().toLowerCase(),name:person.name || [person.first_name,person.last_name].filter(Boolean).join(' ')}))
            .filter(person => person.email && !added.has(person.email) && !seen.has(person.email) && (person.email.includes(query) || person.name.toLowerCase().includes(query)) && seen.add(person.email)).slice(0,5);
    },
    mailRecipientKey(event, field) {
        const suggestions = this.mailRecipientSuggestions(field);
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            if (suggestions.length) { event.preventDefault(); this.mail.recipientIndex = (this.mail.recipientIndex + (event.key === 'ArrowDown' ? 1 : -1) + suggestions.length) % suggestions.length; }
        } else if (['Enter', ',', ';', 'Tab'].includes(event.key)) {
            if (event.key !== 'Tab') event.preventDefault();
            const suggestion = event.key === 'Enter' && this.mail.recipientFocus === field ? suggestions[this.mail.recipientIndex] : null;
            this.addMailRecipients(field, suggestion?.email || this.mail.recipientInputs[field]);
        } else if (event.key === 'Backspace' && !this.mail.recipientInputs[field]) {
            const addresses = this.mailRecipientList(field); if (addresses.length) this.removeMailRecipient(field, addresses.at(-1));
        } else if (event.key === 'Escape') { event.stopPropagation(); this.mail.recipientFocus = ''; }
    },
    pasteMailRecipients(event, field) {
        const value = event.clipboardData.getData('text');
        if (/[,;\n\r]/.test(value)) { event.preventDefault(); this.addMailRecipients(field, this.mail.recipientInputs[field] + value); }
    },
    mailHTMLDocument(html, images = false) {
        const csp = "default-src 'none'; img-src data:" + (images ? ' https:' : '') + "; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'";
        return '<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="' + csp + '"><style>body{font:14px/1.7 Arial,sans-serif;color:#172b3a;padding:20px;margin:0;overflow-wrap:anywhere}img{max-width:100%;height:auto}table{max-width:100%}pre{white-space:pre-wrap}a{color:#087fa4}</style></head><body>' + (html || '') + '</body></html>';
    },
    mailSignatureDocument(html) {
        const fragment = (html || '').replace(/<!doctype[^>]*>/gi, '').replace(/<\/?(?:html|head|body)\b[^>]*>/gi, '');
        return '<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data: https: http:; style-src \'unsafe-inline\'; font-src data:; base-uri \'none\'; form-action \'none\'"><style>body{margin:0;padding:16px;font-family:Arial,Helvetica,sans-serif}</style></head><body>' + fragment + '</body></html>';
    },
    mailFileSize(bytes) { return bytes >= 1048576 ? (bytes / 1048576).toFixed(1) + ' MB' : bytes >= 1024 ? Math.ceil(bytes / 1024) + ' KB' : bytes + ' B'; },
    mailInitial(address) { return (address || '?').slice(0, 1).toUpperCase(); },
    async loadMailboxes() {
        const session = this.token, view = this.currentView;
        this.mail.error = '';
        try {
            const [boxes, teams] = await Promise.all([this.api('/mailboxes'), this.api('/teams')]);
            if (session !== this.token || view !== this.currentView) return;
            this.mail.boxes = boxes; this.mail.teams = teams;
            this.loadUnreadMailCount();
            if (!boxes.some(b => b.id === Number(this.mail.boxId))) this.mail.boxId = boxes[0]?.id || '';
            if (this.currentView === 'mailSettings') this.editMailboxSettings();
            else if (['mailboxes','mailSent'].includes(this.currentView) && this.mail.boxId) await this.loadMailMessages();
            else { this.mail.items = []; this.mail.selected = null; }
        } catch (e) { if (session === this.token) this.mail.error = e.message; }
    },
    async loadMailMessages(preserveSelection = false) {
        const m = this.mail, box = m.boxId;
        const seq = m.request = (m.request || 0) + 1;
        m.error = ''; if (!preserveSelection) m.selected = null; m.loading = true;
        if (!box) { m.loading = false; return; }
        try {
            const data = await this.api(`/mailboxes/${box}/messages?folder=${m.folder}&status=${m.readFilter}&q=${encodeURIComponent(m.search)}&page=${m.page}`);
            if (seq !== m.request || box !== m.boxId) return;
            m.items = data.items; m.total = data.total; m.pages = data.pages; m.unread = data.unread || 0;
            this.loadUnreadMailCount();
        } catch (e) { if (seq === m.request) m.error = e.message; }
        finally { if (seq === m.request) m.loading = false; }
    },
    changeMailFolder(folder) { return this.selectView(folder === 'sent' ? 'mailSent' : 'mailboxes'); },
    async selectMailMessage(row) {
        const box = this.mail.boxId;
        this.mail.selected = {...row, links:row.links || {clients:[],contacts:[]}}; this.mail.remoteImages = false; this.mail.htmlView = true;
        try {
            const data = await this.api(`/mailboxes/${box}/messages/${row.id}`);
            if (this.mail.boxId !== box || this.mail.selected?.id !== row.id) return;
            this.mail.selected = data;
            if (!data.is_read) await this.setMailRead(this.mail.selected, true);
        } catch (e) { if (this.mail.boxId === box) this.mail.error = e.message; }
    },
    async setMailRead(row, isRead) {
        const box = this.mail.boxId;
        if (row._changingRead) return;
        row._changingRead = true;
        try {
            await this.api(`/mailboxes/${box}/messages/${row.id}/read`, {method:'PUT', body:JSON.stringify({is_read:isRead})});
            if (this.mail.boxId !== box) return;
            if (row.folder === 'inbox' && row.is_read !== isRead) this.mail.unread = Math.max(0, this.mail.unread + (isRead ? -1 : 1));
            row.is_read = isRead;
            const item = this.mail.items.find(v => v.id === row.id);
            if (item) item.is_read = isRead;
            if (this.mail.selected?.id === row.id) this.mail.selected.is_read = isRead;
            await this.loadUnreadMailCount();
        } catch (e) { if (this.mail.boxId === box) this.mail.error = e.message; }
        finally { row._changingRead = false; }
    },
    async downloadMailAttachment(part) {
        if (this.mail.downloading) return;
        const box = this.mail.boxId, msg = this.mail.selected, state = this.mail, session = this.token;
        const controller = new AbortController();
        state.downloadController = controller;
        let url;
        this.mail.downloading = part.part; this.mail.error = '';
        try {
            const response = await fetch(`/api/mailboxes/${box}/messages/${msg.id}/attachments/${encodeURIComponent(part.part)}`, {signal:controller.signal,headers:{Authorization:'Bearer ' + session, 'Accept-Language':window.ZenI18n.locale}});
            if (session !== this.token || state !== this.mail || controller.signal.aborted) return;
            if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(window.ZenI18n.t(data.error || 'Nie udało się pobrać załącznika')); }
            const blob = await response.blob();
            if (session !== this.token || state !== this.mail || controller.signal.aborted) return;
            url = URL.createObjectURL(blob);
            const link = document.createElement('a'); link.href = url; link.download = part.filename; link.click();
        } catch (e) { if (session === this.token && state === this.mail && e.name !== 'AbortError') state.error = e.message; }
        finally {
            if (url) setTimeout(() => URL.revokeObjectURL(url), 1000);
            state.downloading = ''; state.downloadController = null;
        }
    },
    async syncMailbox(allMessages = false) {
        if (this.mail.busy || !this.mail.boxId) return;
        const box = this.mail.boxId, session = this.token;
        this.mail.busy = true; this.mail.syncingAll = allMessages; this.mail.cancelSync = false;
        this.mail.syncProgress = {processed:0,imported:0,total:0}; this.mail.error = '';
        let before = null;
        try {
            do {
                const result = await this.api(`/mailboxes/${box}/sync`, {method:'POST',body:JSON.stringify({all_messages:allMessages,before_uid:before})});
                if (session !== this.token || box !== this.mail.boxId) return;
                const i = this.mail.boxes.findIndex(b => b.id === result.mailbox.id);
                if (i >= 0) this.mail.boxes[i] = result.mailbox;
                this.mail.syncProgress.processed += result.processed;
                this.mail.syncProgress.imported += result.imported;
                this.mail.syncProgress.total = result.total;
                before = result.next_before_uid;
            } while (allMessages && before && !this.mail.cancelSync);
            await this.loadMailMessages();
            this.notify((this.mail.cancelSync ? window.ZenI18n.t("Zatrzymano synchronizację. ") : '') + window.ZenI18n.t('Pobrano {count} nowych wiadomości', {count:this.mail.syncProgress.imported}));
        } catch (e) { if (session === this.token) this.mail.error = e.message; }
        finally { this.mail.busy = false; this.mail.syncingAll = false; }
    },
    openMailboxConnect() {
        this.mail.error = '';
        this.mail.form = {name:'',email:'',team_id:'',username:'',password:'',imap_host:'',imap_port:993,smtp_host:'',smtp_port:587,smtp_security:'starttls'};
        this.mail.connecting = true;
    },
    async connectMailbox() {
        const session = this.token;
        if (this.mail.busy) return;
        this.mail.busy = true; this.mail.error = '';
        try {
            const b = await this.api('/mailboxes', {method:'POST',body:JSON.stringify(this.mail.form)});
            if (session !== this.token) return;
            this.mail.boxes.push(b); this.mail.boxId = b.id; this.mail.connecting = false; this.mail.form.password = '';
            if (this.currentView === 'mailSettings') this.editMailboxSettings();
            else await this.loadMailMessages();
            this.notify(window.ZenI18n.t("Skrzynka podłączona. Kliknij Synchronizuj, aby pobrać pocztę."));
            if (this.mail.pendingRecipient) { const address = this.mail.pendingRecipient; this.mail.pendingRecipient = ''; this.composeMail(); this.addMailRecipients('to', address); }
        } catch (e) { this.mail.error = e.message; }
        finally { this.mail.busy = false; }
    },
    openMailboxSettings() { this.selectView('mailSettings'); },
    editMailboxSettings() {
        const b = this.activeMailbox;
        this.mail.signature = b?.signature || ''; this.mail.signatureFormat = b?.signature_format || 'text';
        this.mail.connection = Object.fromEntries(['name','username','imap_host','imap_port','smtp_host','smtp_port','smtp_security','sync_interval_minutes'].map(k => [k,b?.[k]]));
        this.mail.password = ''; this.mail.settingsTab = 'signature'; this.mail.settings = true; this.mail.error = '';
    },
    async saveMailboxSettings() {
        const session = this.token;
        if (this.mail.busy) return;
        this.mail.busy = true; this.mail.error = '';
        try {
            const b = await this.api(`/mailboxes/${this.mail.boxId}`, {method:'PUT',body:JSON.stringify({...this.mail.connection,signature:this.mail.signature,signature_format:this.mail.signatureFormat,password:this.mail.password})});
            if (session !== this.token) return;
            this.mail.boxes[this.mail.boxes.findIndex(v => v.id === b.id)] = b;
            this.mail.password = ''; this.mail.settings = false; this.notify(window.ZenI18n.t("Ustawienia skrzynki zapisane"));
        } catch (e) { this.mail.error = e.message; }
        finally { this.mail.busy = false; }
    },
    async disconnectMailbox() {
        if (this.mail.busy || !confirm(window.ZenI18n.t("Odłączyć skrzynkę i usunąć jej lokalną historię? Poczta na serwerze pozostanie."))) return;
        this.mail.busy = true;
        try {
            await this.api(`/mailboxes/${this.mail.boxId}`, {method:'DELETE'});
            this.mail.settings = false; this.mail.boxId = ''; await this.loadMailboxes();
        } catch (e) { this.mail.error = e.message; }
        finally { this.mail.busy = false; }
    },
    composeMail(mode = 'new') {
        if (mode === true) mode = 'reply';
        if (mode === false) mode = 'new';
        const row = mode === 'new' ? null : this.mail.selected;
        const replying = mode === 'reply' || mode === 'replyAll';
        const own = (this.activeMailbox?.email || '').trim().toLowerCase();
        const unique = values => [...new Set(values.filter(Boolean).map(v => v.trim().toLowerCase()).filter(v => v !== own))];
        const sender = unique([row?.sender]);
        const to = replying ? unique(sender.length ? (mode === 'replyAll' ? [...sender, ...(row?.recipients || [])] : sender) : (row?.recipients || [])) : [];
        const cc = mode === 'replyAll' ? unique(row?.cc || []).filter(v => !to.includes(v)) : [];
        this.mail.composeMode = mode;
        this.mail.compose = {to:to.join(', '),cc:cc.join(', '),bcc:'',subject:row ? (mode === 'forward' ? (/^Fwd:/i.test(row.subject) ? row.subject : 'Fwd: ' + row.subject) : (/^Re:/i.test(row.subject) ? row.subject : 'Re: ' + row.subject)) : '',body:'',include_signature:true,reply_to_id:replying ? row?.id : null,forward_message_id:mode === 'forward' ? row?.id : null};
        this.mail.recipientInputs = {to:'',cc:'',bcc:''}; this.mail.recipientErrors = {to:'',cc:'',bcc:''};
        this.mail.showCc = !!cc.length; this.mail.showBcc = false; this.mail.recipientFocus = ''; this.mail.recipientIndex = 0;
        this.mail.error = ''; this.mail.composing = true;
        this.$nextTick?.(() => document.getElementById(to.length ? 'mail-compose-body' : 'mail-recipient-to')?.focus());
    },
    async sendMail() {
        const session = this.token;
        if (this.mail.busy) return;
        let valid = true;
        for (const field of ['to','cc','bcc']) if (!this.addMailRecipients(field)) valid = false;
        if (!valid) {
            if (this.mail.recipientErrors.cc) this.mail.showCc = true;
            if (this.mail.recipientErrors.bcc) this.mail.showBcc = true;
            const field = ['to','cc','bcc'].find(key => this.mail.recipientErrors[key]);
            this.$nextTick?.(() => document.getElementById('mail-recipient-' + field)?.focus());
            return;
        }
        if (!['to','cc','bcc'].some(field => this.mailRecipientList(field).length)) { this.mail.recipientErrors.to = window.ZenI18n.t("Dodaj przynajmniej jednego odbiorcę."); return; }
        this.mail.busy = true; this.mail.error = '';
        try {
            const result = await this.api(`/mailboxes/${this.mail.boxId}/send`, {method:'POST',body:JSON.stringify(this.mail.compose)});
            if (session !== this.token) return;
            this.mail.composing = false;
            await this.selectView('mailSent');
            this.notify(result.refused.length ? window.ZenI18n.t("Wiadomość wysłana częściowo. Odrzuceni odbiorcy: ") + result.refused.join(', ') : window.ZenI18n.t("Wiadomość wysłana"));
        } catch (e) { this.mail.error = e.message; }
        finally { this.mail.busy = false; }
    },
}; };
