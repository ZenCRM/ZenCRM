window.ZenModules = window.ZenModules || {};
window.ZenModules.documents = function () { return {
        async openGenerate(offer, type) {
            if (!this.templates.length) {
                try { this.templates = await this.api('/templates'); }
                catch (e) { this.notify(e.message); return; }
            }
            const template = this.templates.find(t => t.id === Number(offer.template_id) && t.type === type && t.is_active)
                || this.templates.find(t => t.type === type && t.is_active);
            this.generateModal = { open: true, type, item: offer, templateId: template?.id || '', custom: { ...(offer.data?.custom || {}) }, error: '' };
        },

        generationFields() {
            const tpl = this.templates.find(t => t.id === Number(this.generateModal.templateId));
            return Array.isArray(tpl?.variables) ? tpl.variables : [];
        },

        async submitGeneration() {
            const g = this.generateModal;
            const endpoint = g.type === 'offer' ? 'offers' : 'documents';
            try {
                const r = await this.api(`/${endpoint}/${g.item.id}/generate`, { method: 'POST', body: JSON.stringify({
                    template_id: Number(g.templateId), data: { ...(g.item.data || {}), custom: g.custom },
                }) });
                g.open = false;
                await this.reload();
                window.open(`/api/public/${g.type}/${r.public_token}`, '_blank');
            } catch (e) { g.error = e.message; }
        },

        generateOffer(offer) { return this.openGenerate(offer, 'offer'); },

        generateDoc(doc) { return this.openGenerate(doc, 'document'); },

        selectedTemplateFields() {
            const tpl = this.templates.find(t => t.id === Number(this.modal.form.template_id));
            return Array.isArray(tpl?.variables) ? tpl.variables : [];
        },

        async openAttachments(entity, recordId) {
            this.attachmentModal = { open: true, entity, recordId, files: [], busy: false, error: '' };
            await this.loadAttachments();
        },

        async loadAttachments() {
            const a = this.attachmentModal;
            try { a.files = await this.api(`/attachments/${a.entity}/${a.recordId}`); }
            catch (e) { a.error = e.message; }
        },

        async uploadAttachment(event) {
            const a = this.attachmentModal;
            const files = Array.from(event.target.files || []);
            if (!files.length) return;
            a.busy = true;
            a.error = '';
            try {
                for (const file of files) {
                    const body = new FormData();
                    body.append('file', file);
                    const response = await fetch(`/api/attachments/${a.entity}/${a.recordId}`, {
                        method: 'POST', headers: { Authorization: 'Bearer ' + this.token }, body,
                    });
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.error || 'Błąd przesyłania pliku');
                }
                await this.loadAttachments();
                event.target.value = '';
            } catch (e) { a.error = e.message; }
            finally { a.busy = false; }
        },

        async downloadAttachment(file) {
            try {
                const response = await fetch(`/api/attachments/${file.id}`, { headers: { Authorization: 'Bearer ' + this.token } });
                if (!response.ok) throw new Error('Nie udało się pobrać pliku');
                const url = URL.createObjectURL(await response.blob());
                const link = document.createElement('a');
                link.href = url; link.download = file.filename;
                link.click();
                setTimeout(() => URL.revokeObjectURL(url), 1000);
            } catch (e) { this.attachmentModal.error = e.message; }
        },

        async removeAttachment(file) {
            if (!confirm(window.ZenI18n.t('Usunąć ten plik?'))) return;
            try {
                await this.api(`/attachments/${file.id}`, { method: 'DELETE' });
                await this.loadAttachments();
            } catch (e) { this.attachmentModal.error = e.message; }
        },

        async viewOffer(offer) {
            try {
                const r = await this.api(`/offers/${offer.id}/link`, { method: 'POST' });
                window.open(`/api/public/offer/${r.public_token}`, '_blank');
            } catch (e) { this.notify(window.ZenI18n.t('Błąd: ') + e.message); }
        },

        async viewDoc(doc) {
            try {
                const r = await this.api(`/documents/${doc.id}/link`, { method: 'POST' });
                window.open(`/api/public/document/${r.public_token}`, '_blank');
            } catch (e) { this.notify(window.ZenI18n.t('Błąd: ') + e.message); }
        },

        async downloadPdf(mod, item) {
            try {
                const r = await fetch(`/api/${mod}/${item.id}/pdf`, {
                    headers: { 'Authorization': 'Bearer ' + this.token, 'Accept-Language': window.ZenI18n.locale },
                });
                if (!r.ok) {
                    const err = await r.json().catch(() => ({ error: window.ZenI18n.t('Błąd PDF') }));
                    throw new Error(err.error || window.ZenI18n.t('Nie udało się wygenerować PDF'));
                }
                const blob = await r.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = (mod === 'offers' ? item.number : item.title) + '.pdf';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            } catch (e) { this.notify(e.message); }
        },

        async copyLink(mod, item) {
            try {
                const endpoint = mod === 'offers'
                    ? `/offers/${item.id}/link`
                    : `/documents/${item.id}/link`;
                const r = await this.api(endpoint, { method: 'POST' });
                const fullUrl = window.location.origin + r.public_url;
                await navigator.clipboard.writeText(fullUrl);
                this.notify(window.ZenI18n.t('Link skopiowany:\n') + fullUrl);
            } catch (e) { this.notify(window.ZenI18n.t('Błąd: ') + e.message); }
        },

        // ═══════════════════════════════════════════════════════════
        // SZABLONY – edytor z podglądem
        // ═══════════════════════════════════════════════════════════
        openTemplateModal(tpl = null) {
            this.templateModal.editingId = tpl ? tpl.id : null;
            this.templateModal.form = tpl
                ? { name: tpl.name, type: tpl.type, content: tpl.content, variables: (Array.isArray(tpl.variables) ? tpl.variables : []).map(v => ({ ...v })) }
                : {
                    name: '',
                    type: 'offer',
                    content: window.DEFAULT_TEMPLATE || '<h1>{{ title }}</h1>',
                    variables: [],
                };
            this.templateModal.error = '';
            this.templateModal.open = true;
            this.$nextTick(() => this.refreshTemplatePreview());
        },

        addTemplateField() {
            this.templateModal.form.variables.push({ name: '', label: '' });
        },

        async saveTemplate() {
            this.templateModal.error = '';
            try {
                if (this.templateModal.editingId) {
                    await this.api(`/templates/${this.templateModal.editingId}`, {
                        method: 'PUT', body: JSON.stringify(this.templateModal.form),
                    });
                } else {
                    await this.api('/templates', {
                        method: 'POST', body: JSON.stringify(this.templateModal.form),
                    });
                }
                this.templateModal.open = false;
                await this.reload();
            } catch (e) { this.templateModal.error = e.message; }
        },

        async removeTemplate(id) {
            if (!confirm(window.ZenI18n.t('Usunąć ten szablon?'))) return;
            try {
                await this.api(`/templates/${id}`, { method: 'DELETE' });
                await this.reload();
            } catch (e) { this.notify(e.message); }
        },

        async previewTemplate(tpl) {
            this.openTemplateModal(tpl);
        },

        async refreshTemplatePreview() {
            const frame = this.$refs.templatePreviewFrame;
            if (!frame) return;
            try {
                const r = await fetch('/api/templates/preview', {
                    method: 'POST',
                    headers: {
                        'Accept-Language': window.ZenI18n.locale,
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + this.token,
                    },
                    body: JSON.stringify({
                        content: this.templateModal.form.content,
                        type: this.templateModal.form.type,
                        variables: this.templateModal.form.variables,
                    }),
                });
                const html = await r.text();
                frame.srcdoc = html;
            } catch (e) {
                frame.srcdoc = '<pre style="color:red;padding:20px">' + e.message + '</pre>';
            }
        },

}; };
