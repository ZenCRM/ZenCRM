/* Settings component section; state is created for each CRM instance. */
window.ZenSettings = window.ZenSettings || {};
window.ZenSettings.appearance = function () { return {
        get darkSidebar() {
            return this.settingsForm?.ui_template === 'modern' || this.settingsForm?.ui_classic_sidebar === 'dark';
        },
        classicPalettes: [
            {id: 'blue', label: 'Niebieski', primary: '#007fce', secondary: '#009fb9'},
            {id: 'green', label: 'Zielony', primary: '#16886e', secondary: '#0891b2'},
            {id: 'violet', label: 'Fioletowy', primary: '#7e3af2', secondary: '#6366f1'},
            {id: 'amber', label: 'Bursztynowy', primary: '#b45309', secondary: '#c2410c'},
            {id: 'graphite', label: 'Grafitowy', primary: '#475569', secondary: '#64748b'},
        ],
        isClassicPaletteSelected(palette) {
            return this.settingsForm.brand_color_primary?.toLowerCase() === palette.primary && this.settingsForm.brand_color_secondary?.toLowerCase() === palette.secondary;
        },
        selectClassicPalette(palette) {
            this.settingsForm.brand_color_primary = palette.primary;
            this.settingsForm.brand_color_secondary = palette.secondary;
            this.applyTheme();
        },
        async saveSettings() {
            if (this.settingsTab === 'clients') { await this.saveClientSettings(); return; }
            if (this.settingsTab === 'helpdesk') {
                await this.saveHelpdeskSettings();
                return;
            }
            this.settingsSaved = '';
            this.settingsError = '';
            try {
                const appearanceKeys = ['ui_template','ui_classic_sidebar','ui_hero_background','brand_color_primary','brand_color_secondary'];
                const values = this.settingsTab === 'appearance'
                    ? Object.fromEntries(appearanceKeys.filter(key => key in this.settingsForm).map(key => [key,this.settingsForm[key]]))
                    : this.settingsForm;
                const updated = await this.api('/settings', {
                    method: 'PUT',
                    body: JSON.stringify(values),
                });
                this.settingsForm = { ...updated };
                this.applyTheme();
                this.settingsSaved = window.ZenI18n.t('Ustawienia zapisane');
                setTimeout(() => { this.settingsSaved = ''; }, 2000);
            } catch (e) {
                this.settingsError = window.ZenI18n.t('Błąd: ') + e.message;
            }
        },

        async resetSettings() {
            if (!confirm(window.ZenI18n.t('Przywrócić domyślne ustawienia?'))) return;
            try {
                await this.api('/settings/reset', { method: 'POST' });
                await this.loadSettings();
            } catch (e) { this.notify(e.message); }
        },

        chooseModernHeroBackground() {
            const backgrounds = ['mountains', 'forest', 'coast'];
            const selected = this.settingsForm?.ui_hero_background || 'random';
            let next = backgrounds.includes(selected) ? selected : backgrounds[Math.floor(Math.random() * backgrounds.length)];
            if (selected === 'random' && next === this.modernHeroBackground) {
                next = backgrounds[(backgrounds.indexOf(next) + 1 + Math.floor(Math.random() * (backgrounds.length - 1))) % backgrounds.length];
            }
            this.modernHeroBackground = next;
            document.documentElement.style.setProperty('--modern-hero-image', `url('/images/hero-${next}-photo.webp')`);
        },

        async uploadBrandFile(event, variant) {
            const file = event.target.files && event.target.files[0];
            if (!file) return;
            const fd = new FormData();
            fd.append('file', file);
            fd.append('variant', variant);
            try {
                const r = await fetch('/api/settings/upload-logo', {
                    method: 'POST',
                    headers: { 'Authorization': 'Bearer ' + this.token, 'Accept-Language': window.ZenI18n.locale },
                    body: fd,
                });
                const data = await r.json();
                if (!r.ok) throw new Error(data.error || window.ZenI18n.t('Blad uploadu'));
                const keyMap = { light: 'brand_logo_light', dark: 'brand_logo_dark', favicon: 'brand_favicon' };
                this.settingsForm[keyMap[variant]] = data.url + '?t=' + Date.now();
                this.applyTheme();
            } catch (e) { this.notify(window.ZenI18n.t('Błąd: ') + e.message); }
            event.target.value = '';
        },

        applyTheme() {
            const s = this.settingsForm || {};
            this.chooseModernHeroBackground();

            // Kolor glowny jako CSS variable
            const primary = s.brand_color_primary || '#007fce';
            const secondary = s.brand_color_secondary || '#009fb9';
            document.documentElement.style.setProperty('--brand-primary', primary);
            document.documentElement.style.setProperty('--brand-secondary', secondary);

            // Zamien kolor w przyciskach bg-brand-600 (inline override)
            let styleTag = document.getElementById('zen-theme-override');
            if (!styleTag) {
                styleTag = document.createElement('style');
                styleTag.id = 'zen-theme-override';
                document.head.appendChild(styleTag);
            }
            styleTag.textContent = `
                html:not(.theme-modern) .windmill-app {
                    --wm-accent: ${primary}; --wm-accent-hover: ${this._darken(primary, 15)};
                    --wm-tint: ${this._lighten(primary, 92)}; --wm-accent-text: ${this._darken(primary, 15)};
                }
                html.dark:not(.theme-modern) .windmill-app { --wm-tint: ${this._darken(primary, 65)}; --wm-accent-text: ${this._lighten(primary, 65)}; }
                html.classic-sidebar-light .zen-app-sidebar { --sidebar-active: ${this._lighten(primary, 92)}; --sidebar-active-text: ${this._darken(primary, 15)}; }
                html.classic-sidebar-dark .zen-app-sidebar { --sidebar-active: ${this._darken(primary, 65)}; --sidebar-active-text: ${this._lighten(primary, 65)}; }
                html:not(.theme-modern) .windmill-app .zen-client-card { --client-blue: ${primary}; --client-cyan: ${secondary}; }
                html:not(.theme-modern) .windmill-app .zen-contacts { --metric: ${primary}; --metric-tint: ${this._lighten(primary, 92)}; }
                html:not(.theme-modern) .windmill-app .zen-tasks { --metric: ${secondary}; --metric-tint: ${this._lighten(secondary, 92)}; }
                html:not(.theme-modern) .windmill-app .zen-client-card .detail-hero { border-top-color: ${primary}; }
                html:not(.theme-modern) .windmill-app .zen-section-icon { color: ${primary}; background: ${this._lighten(primary, 92)}; }
                html:not(.theme-modern) .windmill-app .zen-client-card .ux-button,
                html:not(.theme-modern) .windmill-app .detail-shell.zen-client-card .ux-next-step .ux-button,
                html:not(.theme-modern) .windmill-app .detail-shell .detail-hero .zen-convert-button { background: ${primary}!important; }

                .bg-brand-600 { background-color: ${primary} !important; }
                .bg-brand-700 { background-color: ${this._darken(primary, 15)} !important; }
                .hover\\:bg-brand-700:hover { background-color: ${this._darken(primary, 15)} !important; }
                .text-brand-600 { color: ${primary} !important; }
                .text-brand-700 { color: ${this._darken(primary, 20)} !important; }
                .bg-brand-100 { background-color: ${this._lighten(primary, 85)} !important; }
                .bg-brand-50 { background-color: ${this._lighten(primary, 93)} !important; }
                .border-brand-200 { border-color: ${this._lighten(primary, 75)} !important; }
                .focus\\:ring-brand-500:focus { --tw-ring-color: ${primary} !important; }

            `;

            const lightLogo = s.brand_logo_light || '/logo.png';
            const darkLogo = s.brand_logo_dark || lightLogo;

            // Logo na ekranie logowania
            const loginLogo = document.getElementById('zen-login-logo');
            if (loginLogo) {
                loginLogo.style.display = (s.login_show_logo === 'false') ? 'none' : '';
                loginLogo.src = this.darkMode ? darkLogo : lightLogo;
            }

            // Logo w sidebarze
            const sidebarLogo = document.getElementById('zen-sidebar-logo');
            if (sidebarLogo) {
                sidebarLogo.src = this.darkSidebar ? darkLogo : lightLogo;
                sidebarLogo.style.filter = this.darkSidebar && darkLogo === '/logo.png' ? 'brightness(0) invert(1)' : '';
                if (s.brand_logo_size) {
                    sidebarLogo.style.height = `${s.brand_logo_size}px`;
                    sidebarLogo.style.maxHeight = `${s.brand_logo_size}px`;
                }
            }

            // Favicon
            const favicon = document.querySelector('link[rel="icon"]');
            if (favicon) {
                favicon.href = s.brand_favicon || '/icon.png';
            }
        },

        previewBranding() {
            if (this.settingsForm.brand_name) {
                document.title = this.settingsForm.brand_name;
            }
            this.applyTheme();
        },

        _darken(hex, percent) {
            return this._shift(hex, -percent);
        },
        _lighten(hex, percent) {
            hex = (hex || '#007fce').replace('#', '');
            if (hex.length === 3) hex = hex.split('').map(c => c + c).join('');
            const num = parseInt(hex, 16);
            let r = num >> 16;
            let g = (num >> 8) & 0x00FF;
            let b = num & 0x0000FF;
            const factor = Math.max(0, Math.min(100, percent)) / 100;
            // Mix channels towards 255 (white) to produce clean tint without hue shifting into neon colors like #74feff
            r = Math.round(r + (255 - r) * factor);
            g = Math.round(g + (255 - g) * factor);
            b = Math.round(b + (255 - b) * factor);
            return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0');
        },
        _shift(hex, percent) {
            hex = (hex || '#007fce').replace('#', '');
            if (hex.length === 3) hex = hex.split('').map(c => c + c).join('');
            const num = parseInt(hex, 16);
            let r = (num >> 16) + Math.round(2.55 * percent);
            let g = ((num >> 8) & 0x00FF) + Math.round(2.55 * percent);
            let b = (num & 0x0000FF) + Math.round(2.55 * percent);
            r = Math.max(0, Math.min(255, r));
            g = Math.max(0, Math.min(255, g));
            b = Math.max(0, Math.min(255, b));
            return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0');
        },

}; };
