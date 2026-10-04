window.ZenModules = window.ZenModules || {};
window.ZenModules.documents = function () { return {
        async openGenerate(offer, type) {
            if (!this.templates.length) {
                try { this.templates = await this.api('/templates'); }
                catch (e) { this.notify(e.message); return; }
            }
            if (type === 'document' && !this.documentTypes.length) {
                try { this.documentTypes = await this.api('/document-types'); }
                catch (e) { this.notify(e.message); return; }
            }
            const eligible = t => t.type === type && t.is_active && (type !== 'document' || !t.document_type_key || t.document_type_key === offer.type);
            const template = this.templates.find(t => t.id === Number(offer.template_id) && eligible(t))
                || this.templates.find(t => eligible(t) && t.document_type_key === offer.type)
                || this.templates.find(eligible);
            this.generateModal = { open: true, type, item: offer, templateId: template?.id || '', custom: { ...(offer.data?.custom || {}) }, typeFields: { ...(offer.data?.type_fields || {}) }, error: '' };
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
                    template_id: Number(g.templateId), data: { ...(g.item.data || {}), custom: g.custom, type_fields: g.typeFields },
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

        documentTypeLabel(key) {
            return this.documentTypes.find(t => t.key === key)?.name || key || 'Inne';
        },

        selectedDocumentTypeFields() {
            const key = this.modal.form.type || 'other';
            return this.documentTypes.find(t => t.key === key)?.fields || [];
        },

        generationTypeFields() {
            if (this.generateModal.type !== 'document') return [];
            return this.documentTypes.find(t => t.key === (this.generateModal.item?.type || 'other'))?.fields || [];
        },

        openDocumentTypeModal(row = null) {
            this.documentTypeModal = { open: true, editingKey: row?.key || null, error: '', form: row
                ? { key: row.key, name: row.name, is_active: row.is_active, fields: (row.fields || []).map(f => ({ ...f, optionsText: (f.options || []).join('\n') })) }
                : { key: '', name: '', is_active: true, fields: [] } };
        },

        addDocumentTypeField() {
            this.documentTypeModal.form.fields.push({ key: '', label: '', kind: 'text', required: false, optionsText: '' });
        },

        async saveDocumentType() {
            const m = this.documentTypeModal;
            m.error = '';
            const data = { ...m.form, fields: m.form.fields.map(f => ({
                key: f.key.trim(), label: f.label.trim(), kind: f.kind, required: f.required,
                options: f.kind === 'select' ? f.optionsText.split(/\r?\n|,/).map(v => v.trim()).filter(Boolean) : [],
            })) };
            try {
                await this.api(m.editingKey ? `/document-types/${m.editingKey}` : '/document-types', {
                    method: m.editingKey ? 'PUT' : 'POST', body: JSON.stringify(data),
                });
                m.open = false;
                this.documentTypes = await this.api('/document-types');
            } catch (e) { m.error = e.message; }
        },

        async removeDocumentType(row) {
            if (!confirm(`Usunąć typ „${row.name}”?`)) return;
            try {
                await this.api(`/document-types/${row.key}`, { method: 'DELETE' });
                this.documentTypes = await this.api('/document-types');
            } catch (e) { this.notify(e.message); }
        },

        async openAttachments(entity, recordId) {
            if (!recordId) return;
            if (entity === 'project') this.projectTab = 'files';
            else this.detailView.tab = 'files';
            this.attachmentView = { entity, recordId, files: [], busy: false, error: '', editingId: null, editingName: '' };
            await this.loadAttachments();
        },

        async loadAttachments() {
            const a = this.attachmentView;
            try {
                const files = await this.api(`/attachments/${a.entity}/${a.recordId}`);
                if (this.attachmentView === a) a.files = files;
            } catch (e) { if (this.attachmentView === a) a.error = e.message; }
        },

        async uploadAttachment(event) {
            const a = this.attachmentView;
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
            } catch (e) { this.attachmentView.error = e.message; }
        },

        editAttachmentName(file) {
            this.attachmentView.editingId = file.id;
            this.attachmentView.editingName = file.filename;
        },

        async renameAttachment(file) {
            const a = this.attachmentView;
            try {
                await this.api(`/attachments/${file.id}`, { method: 'PUT',
                    body: JSON.stringify({ filename: a.editingName.trim() }) });
                a.editingId = null;
                a.error = '';
                await this.loadAttachments();
            } catch (e) { a.error = e.message; }
        },

        async removeAttachment(file) {
            if (!confirm(window.ZenI18n.t('Usunąć ten plik?'))) return;
            try {
                await this.api(`/attachments/${file.id}`, { method: 'DELETE' });
                await this.loadAttachments();
            } catch (e) { this.attachmentView.error = e.message; }
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
                const fullUrl = (this.settingsForm?.crm_base_url || window.location.origin) + r.public_url;
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
                ? { name: tpl.name, type: tpl.type, document_type_key: tpl.document_type_key || '', content: tpl.content, variables: (Array.isArray(tpl.variables) ? tpl.variables : []).map(v => ({ ...v })) }
                : {
                    name: '',
                    type: 'offer',
                    document_type_key: '',
                    content: window.DEFAULT_TEMPLATE || '<h1>{{ title }}</h1>',
                    variables: [],
                };
            this.templateModal.error = '';
            this.templateModal.previewError = '';
            this.templateStudio.mode = tpl && /{%|<script|<iframe/i.test(tpl.content) ? 'source' : 'visual';
            if (!tpl) this.templateModal.form.content = this.starterTemplate();
            this.templateStudio.original = JSON.stringify(this.templateModal.form);
            this.templateStudio.variableSearch = '';
            this.templateStudio.saving = false;
            this.templateModal.open = true;
            if (!this.documentTypes.length) this.api('/document-types').then(r => { this.documentTypes = r; }).catch(() => {});
            this.$nextTick(() => this.refreshTemplatePreview());
            if (this.templateStudio.mode === 'visual') this.mountVisualTemplate();
        },

        addTemplateField() {
            this.templateModal.form.variables.push({ name: '', label: '' });
        },

        insertTemplateText(value) {
            const area = this.$refs.templateContent;
            const current = this.templateModal.form.content || '';
            const start = area?.selectionStart ?? current.length;
            const end = area?.selectionEnd ?? current.length;
            this.templateModal.form.content = current.slice(0, start) + value + current.slice(end);
            this.$nextTick(() => { area?.focus(); area?.setSelectionRange(start + value.length, start + value.length); });
            this.$nextTick(() => this.refreshTemplatePreview());
        },

        templateTypeFields() {
            return this.documentTypes.find(t => t.key === this.templateModal.form.document_type_key)?.fields || [];
        },

        async saveTemplate() {
            if (this.templateStudio.saving) return;
            this.templateModal.error = '';
            if (!this.templateModal.form.name.trim() || !this.templateModal.form.content.trim()) { this.templateModal.error = window.ZenI18n.t("Podaj nazwę i treść szablonu"); return; }
            this.templateStudio.saving = true;
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
            finally { this.templateStudio.saving = false; }
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
            const requestId = this._templatePreviewRequest = (this._templatePreviewRequest || 0) + 1;
            const frame = this.$refs.templatePreviewFrame;
            if (!frame) return;
            const fitPage = () => {
                const width = Math.max(180, frame.parentElement.clientWidth - 24);
                frame.style.width = '794px'; frame.style.height = '1123px';
                frame.style.zoom = Math.min(1, width / 794);
            };
            fitPage();
            this._templateResizeObserver?.disconnect();
            if (typeof ResizeObserver !== 'undefined') {
                this._templateResizeObserver = new ResizeObserver(fitPage);
                this._templateResizeObserver.observe(frame.parentElement);
            }
            this.templateModal.previewLoading = true;
            this.templateModal.previewError = '';
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
                        document_type_key: this.templateModal.form.document_type_key,
                    }),
                });
                const html = await r.text();
                if (requestId !== this._templatePreviewRequest) return;
                frame.srcdoc = html;
                if (!r.ok) this.templateModal.previewError = window.ZenI18n.t("Sprawdź składnię szablonu. Szczegóły są w podglądzie.");
            } catch (e) {
                if (requestId !== this._templatePreviewRequest) return;
                this.templateModal.previewError = e.message;
            } finally {
                if (requestId === this._templatePreviewRequest) this.templateModal.previewLoading = false;
            }
        },

}; };
