window.ZenModules = window.ZenModules || {};
window.ZenModules.documents = function () { return {
        async generateOffer(offer) {
            try {
                const r = await this.api(`/offers/${offer.id}/generate`, { method: 'POST' });
                await this.reload();
                window.open(`/api/public/offer/${r.public_token}`, '_blank');
            } catch (e) { this.notify(window.ZenI18n.t('Błąd generowania: ') + e.message); }
        },

        async generateDoc(doc) {
            try {
                const r = await this.api(`/documents/${doc.id}/generate`, { method: 'POST' });
                await this.reload();
                window.open(`/api/public/document/${r.public_token}`, '_blank');
            } catch (e) { this.notify(window.ZenI18n.t('Błąd generowania: ') + e.message); }
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
                    headers: { 'Authorization': 'Bearer ' + this.token },
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
                this.notify('Link skopiowany:\n' + fullUrl);
            } catch (e) { this.notify(window.ZenI18n.t('Błąd: ') + e.message); }
        },

        // ═══════════════════════════════════════════════════════════
        // SZABLONY – edytor z podglądem
        // ═══════════════════════════════════════════════════════════
        openTemplateModal(tpl = null) {
            this.templateModal.editingId = tpl ? tpl.id : null;
            this.templateModal.form = tpl
                ? { name: tpl.name, type: tpl.type, content: tpl.content }
                : {
                    name: '',
                    type: 'offer',
                    content: window.DEFAULT_TEMPLATE || '<h1>{{ title }}</h1>',
                };
            this.templateModal.error = '';
            this.templateModal.open = true;
            this.$nextTick(() => this.refreshTemplatePreview());
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
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + this.token,
                    },
                    body: JSON.stringify({
                        content: this.templateModal.form.content,
                        type: this.templateModal.form.type,
                    }),
                });
                const html = await r.text();
                frame.srcdoc = html;
            } catch (e) {
                frame.srcdoc = '<pre style="color:red;padding:20px">' + e.message + '</pre>';
            }
        },

}; };
