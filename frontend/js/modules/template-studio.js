window.ZenModules = window.ZenModules || {};
window.ZenModules.templateStudio = function () { return {
    templateStudio: { mode: 'visual', saving: false, original: '', variableSearch: '', starter: 'business' },
    templateSearch: '', templateFilter: '',
    get filteredTemplates() { const q = this.templateSearch.toLowerCase(); return this.templates.filter(t => (!this.templateFilter || t.type === this.templateFilter) && t.name.toLowerCase().includes(q)); },
    templateVariables() {
        const labels = { title: window.ZenI18n.t("Tytuł"), number: window.ZenI18n.t("Numer"), date: window.ZenI18n.t("Data"), valid_until: window.ZenI18n.t("Ważna do"), total_amount: window.ZenI18n.t("Łączna kwota"), description: window.ZenI18n.t("Opis"), 'client.name': window.ZenI18n.t("Nazwa klienta"), 'client.email': window.ZenI18n.t("E-mail klienta"), 'client.company': window.ZenI18n.t("Firma klienta"), 'client.address': window.ZenI18n.t("Adres klienta"), 'client.phone': window.ZenI18n.t("Telefon klienta"), 'company.name': window.ZenI18n.t("Twoja firma"), 'company.nip': window.ZenI18n.t("NIP firmy"), 'company.address': window.ZenI18n.t("Adres firmy"), 'company.email': window.ZenI18n.t("E-mail firmy"), 'company.phone': window.ZenI18n.t("Telefon firmy"), 'company.www': window.ZenI18n.t("Strona firmy") };
        return Object.entries(labels).filter(([name, label]) => (name + label).toLowerCase().includes(this.templateStudio.variableSearch.toLowerCase())).map(([name, label]) => ({ name, label }));
    },
    starterTemplate(kind = 'business') {
        const copy = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
        const header = '<header style="border-bottom:3px solid #2563eb;padding-bottom:24px;margin-bottom:32px"><h2 style="margin:0;color:#2563eb">{{ company.name }}</h2><p style="font-size:12px;color:#64748b">{{ company.address }} · {{ company.email }}</p></header>';
        const client = `<table style="width:100%;margin:24px 0"><tr><td><strong>${copy(window.ZenI18n.t("Przygotowano dla"))}</strong><p>{{ client.name }}<br>{{ client.address }}<br>{{ client.email }}</p></td><td style="text-align:right;vertical-align:top">${copy(window.ZenI18n.t("Data: "))}{{ date }}<br>${copy(window.ZenI18n.t("Numer: "))}{{ number }}</td></tr></table>`;
        const content = kind === 'letter' ? `<h1>{{ title }}</h1><p>${copy(window.ZenI18n.t("Szanowni Państwo,"))}</p><p>{{ description }}</p><p>${copy(window.ZenI18n.t("Z poważaniem,"))}<br>{{ company.name }}</p>` : kind === 'agreement' ? `<h1>{{ title }}</h1><h2>${copy(window.ZenI18n.t("1. Strony i przedmiot dokumentu"))}</h2><p>{{ company.name }}${copy(window.ZenI18n.t(" oraz "))}{{ client.name }}.</p><p>{{ description }}</p><h2>${copy(window.ZenI18n.t("2. Warunki współpracy"))}</h2><p>${copy(window.ZenI18n.t("Uzupełnij uzgodnione warunki współpracy."))}</p><table style="width:100%;margin-top:80px"><tr><td>____________________<br>${copy(window.ZenI18n.t("Podpis przedstawiciela firmy"))}</td><td style="text-align:right">____________________<br>${copy(window.ZenI18n.t("Podpis klienta"))}</td></tr></table>` : `<h1>{{ title }}</h1><p style="color:#64748b">{{ description }}</p><h2>${copy(window.ZenI18n.t("Zakres i warunki"))}</h2><p>${copy(window.ZenI18n.t("Opisz zakres, terminy i korzyści dla klienta."))}</p><p><strong>${copy(window.ZenI18n.t("Łączna kwota: "))}{{ total_amount }} zł</strong></p><h2>${copy(window.ZenI18n.t("Kolejne kroki"))}</h2><p>${copy(window.ZenI18n.t("Uzupełnij sposób akceptacji i informacje kontaktowe."))}</p>`;
        return '<!doctype html><html><head><meta charset="utf-8"></head><body style="font-family:Arial,sans-serif;color:#0f172a;padding:40px;line-height:1.6;max-width:794px;margin:auto">' + header + client + content + `<footer style="margin-top:48px;border-top:1px solid #e2e8f0;padding-top:16px;color:#64748b;font-size:11px">{{ company.name }}${copy(window.ZenI18n.t(" · NIP: "))}{{ company.nip }} · {{ company.phone }} · {{ company.www }}</footer></body></html>`;
    },
    applyTemplateStarter(kind) {
        if (JSON.stringify(this.templateModal.form) !== this.templateStudio.original && !confirm(window.ZenI18n.t("Zastąpić aktualną treść wybranym układem?"))) return;
        this.templateModal.form.content = this.starterTemplate(kind);
        this.templateStudio.mode = 'visual'; this.mountVisualTemplate(); this.refreshTemplatePreview();
    },
    async duplicateTemplate(tpl) {
        this.openTemplateModal({ ...tpl, id: null, name: tpl.name + window.ZenI18n.t(" — kopia") });
    },
    closeTemplateStudio() {
        if (this.templateStudio.saving) return;
        if (JSON.stringify(this.templateModal.form) !== this.templateStudio.original && !confirm(window.ZenI18n.t("Zamknąć edytor bez zapisania zmian?"))) return;
        this.templateModal.open = false;
    },
    setTemplateMode(mode) {
        this.templateStudio.mode = mode;
        if (mode === 'visual') this.mountVisualTemplate();
    },
    mountVisualTemplate() {
        this.$nextTick(() => {
            const frame = this.$refs.templateVisualFrame;
            if (!frame) return;
            frame.onload = () => {
                const doc = frame.contentDocument;
                if (!doc?.body) return;
                doc.body.contentEditable = 'true';
                doc.body.setAttribute('aria-label', window.ZenI18n.t("Treść dokumentu"));
                doc.body.addEventListener('input', () => {
                    const copy = doc.documentElement.cloneNode(true);
                    copy.querySelectorAll('[data-editor-only]').forEach(el => el.remove());
                    copy.querySelector('body').removeAttribute('contenteditable');
                    copy.querySelector('body').removeAttribute('aria-label');
                    this.templateModal.form.content = '<!doctype html>\n' + copy.outerHTML;
                    clearTimeout(this._templatePreviewTimer);
                    this._templatePreviewTimer = setTimeout(() => this.refreshTemplatePreview(), 700);
                });
            };
            // Isolate saved HTML, disable scripts, remote assets and links during editing.
            const parsed = new DOMParser().parseFromString(this.templateModal.form.content, 'text/html');
            parsed.querySelectorAll('script,iframe,object,embed,base,meta[http-equiv]').forEach(el => el.remove());
            parsed.querySelectorAll('*').forEach(el => Array.from(el.attributes).filter(a => /^on/i.test(a.name)).forEach(a => el.removeAttribute(a.name)));
            const csp = parsed.createElement('meta'); csp.httpEquiv = 'Content-Security-Policy'; csp.content = "default-src 'none'; style-src 'unsafe-inline'; img-src data:;"; csp.dataset.editorOnly = 'true'; parsed.head.prepend(csp);
            frame.srcdoc = '<!doctype html>' + parsed.documentElement.outerHTML;
        });
    },
    templateFormat(command, value = null) {
        const doc = this.$refs.templateVisualFrame?.contentDocument;
        doc?.body.focus(); doc?.execCommand(command, false, value); doc?.body.dispatchEvent(new Event('input'));
    },
    insertStudioText(value) {
        if (this.templateStudio.mode === 'source') { this.insertTemplateText(value); return; }
        this.templateFormat('insertText', value);
    },
    insertStudioBlock(kind) {
        const copy = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
        const blocks = { heading: `<h2>${copy(window.ZenI18n.t("Nowa sekcja"))}</h2><p>${copy(window.ZenI18n.t("Treść sekcji"))}</p>`, paragraph: `<p>${copy(window.ZenI18n.t("Wpisz treść akapitu…"))}</p>`, table: `<table style="width:100%;border-collapse:collapse"><tr><th style="border:1px solid #cbd5e1;padding:10px">${copy(window.ZenI18n.t("Opis"))}</th><th style="border:1px solid #cbd5e1;padding:10px">${copy(window.ZenI18n.t("Wartość"))}</th></tr><tr><td style="border:1px solid #cbd5e1;padding:10px">${copy(window.ZenI18n.t("Pozycja"))}</td><td style="border:1px solid #cbd5e1;padding:10px">${copy(window.ZenI18n.t("0,00 zł"))}</td></tr></table><p><br></p>`, signature: `<table style="width:100%;margin-top:60px"><tr><td>____________________<br>${copy(window.ZenI18n.t("Podpis firmy"))}</td><td>____________________<br>${copy(window.ZenI18n.t("Podpis klienta"))}</td></tr></table><p><br></p>` };
        if (this.templateStudio.mode === 'source') this.insertTemplateText(blocks[kind]);
        else this.templateFormat('insertHTML', blocks[kind]);
    },
}; };
