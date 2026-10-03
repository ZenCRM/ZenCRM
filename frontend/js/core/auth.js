/* Core component methods; composed before UX and feature modules. */
window.ZenCore = window.ZenCore || {};
window.ZenCore.auth = function () { return {
        async submitSetup() {
            this.setupError = '';
            const form = this.setupForm;
            if (!form.email || !form.email.includes('@')) {
                this.setupError = window.ZenI18n.t('Podaj poprawny adres e-mail');
                return;
            }
            if (!form.password || form.password.length < 10) {
                this.setupError = window.ZenI18n.t('Hasło musi mieć od 10 do 256 znaków');
                return;
            }
            if (form.password !== form.password_confirm) {
                this.setupError = window.ZenI18n.t('Hasła nie są identyczne');
                return;
            }
            this.setupLoading = true;
            try {
                const data = await window.ZenApi.setupAdmin({
                    first_name: form.first_name,
                    last_name: form.last_name,
                    email: form.email,
                    password: form.password
                });
                this.token = data.access_token;
                this.user = data.user;
                this.isAdmin = true;
                this.needsSetup = false;
                localStorage.setItem('token', this.token);
                localStorage.setItem('user', JSON.stringify(this.user));
                await this.init();
            } catch (e) {
                this.setupError = e.message;
            } finally {
                this.setupLoading = false;
            }
        },

        async login() {
            this.loginError = '';
            this.loginLoading = true;
            try {
                const data = await window.ZenApi.login(
                    this.loginForm.email, this.loginForm.password);
                this.token = data.access_token;
                this.user = data.user;
                this.isAdmin = (this.user?.role === 'admin');
                localStorage.setItem('token', this.token);
                localStorage.setItem('user', JSON.stringify(this.user));
                await this.init();
            } catch (e) {
                this.loginError = e.message;
            } finally {
                this.loginLoading = false;
            }
        },

        openForgotPassword() {
            this.forgotModal.code = '';
            this.forgotModal.password = '';
            this.forgotModal.awaitingCode = false;
            this.forgotModal.open = true;
            this.forgotModal.email = this.loginForm.email || '';
            this.forgotModal.loading = false;
            this.forgotModal.success = '';
            this.forgotModal.error = '';
        },

        async submitForgotPassword() {
            if (!this.forgotModal.email) {
                this.forgotModal.error = window.ZenI18n.t('Wpisz swój adres e-mail');
                return;
            }
            this.forgotModal.loading = true;
            this.forgotModal.error = '';
            this.forgotModal.success = '';
            try {
                const res = await window.ZenApi.forgotPassword(this.forgotModal.email);
                this.forgotModal.awaitingCode = true;
                this.forgotModal.success = window.ZenI18n.t(res.message || window.ZenI18n.t('Zgłoszenie zostało wysłane'));
            } catch (e) {
                this.forgotModal.error = e.message;
            } finally {
                this.forgotModal.loading = false;
            }
        },

        async confirmPasswordReset() {
            this.forgotModal.loading = true;
            this.forgotModal.error = '';
            try {
                const res = await window.ZenApi.request('/auth/reset-password', {
                    method: 'POST',
                    body: JSON.stringify({ token: this.forgotModal.code.trim(), password: this.forgotModal.password }),
                });
                this.forgotModal.success = res.message;
                this.forgotModal.awaitingCode = false;
                this.forgotModal.code = '';
                this.forgotModal.password = '';
            } catch (e) {
                this.forgotModal.error = e.message;
            } finally {
                this.forgotModal.loading = false;
            }
        },

        async logout() {
            await this.disablePush();
            this.stopNotifications();
            this.stopReminders();
            this.endLeadDrag();
            this.detailView.open = false;
            this.detailPanel = false;
            this.token = '';
            this.user = null;
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            sessionStorage.removeItem('zen-i18n-catalog');
            this.settingsForm = {};
            await this.loadSettings(true);
            // Nie czyścimy lastView – po ponownym zalogowaniu wróci tam, gdzie byłeś
        },

        // ═══════════════════════════════════════════════════════════
        // API WRAPPER
        // ═══════════════════════════════════════════════════════════
        api(path, options = {}) {
            return window.ZenApi.request(path, options, this.token, () => this.logout());
        },

        // ═══════════════════════════════════════════════════════════
        // NAVIGACJA
        // ═══════════════════════════════════════════════════════════
        openProfile() {
            const notifs = this.user?.email_notifications || {};
            this.profile.form = {
                first_name: this.user?.first_name || '',
                last_name:  this.user?.last_name  || '',
                email:      this.user?.email      || '',
                current_password: '',
                avatar_url: this.user?.avatar_url || '',
                default_call_method: this.user?.default_call_method || 'link',
                email_notifications: {
                    ticket_assigned: notifs.ticket_assigned !== false,
                    ticket_reply: notifs.ticket_reply !== false,
                    task_assigned: notifs.task_assigned !== false,
                    client_assigned: notifs.client_assigned !== false,
                },
            };
            this.profile.error = '';
            this.profile.success = '';
            this.avatarTs = Date.now();
            this.profile.open = true;
        },

        async saveProfile() {
            this.profile.error = '';
            this.profile.success = '';
            try {
                const { current_password, ...profileData } = this.profile.form;
                await this.api(`/users/${this.user.id}`, {
                    method: 'PUT', body: JSON.stringify({ ...profileData, current_password }),
                });
                this.user = { ...this.user, ...profileData };
                localStorage.setItem('user', JSON.stringify(this.user));
                this.profile.success = window.ZenI18n.t('Profil zapisany');
                setTimeout(() => { this.profile.open = false; }, 800);
            } catch (e) { this.profile.error = e.message; }
        },

        // ═══════════════════════════════════════════════════════════
        // ZMIANA HASŁA
        // ═══════════════════════════════════════════════════════════
        openPassword() {
            this.password.form = { current_password: '', new_password: '', confirm: '' };
            this.password.error = '';
            this.password.success = '';
            this.password.open = true;
        },

        async savePassword() {
            this.password.error = '';
            this.password.success = '';
            if (this.password.form.new_password !== this.password.form.confirm) {
                this.password.error = window.ZenI18n.t('Hasła nie są identyczne');
                return;
            }
            if (this.password.form.new_password.length < 10) {
                this.password.error = window.ZenI18n.t('Hasło musi mieć min. 10 znaków');
                return;
            }
            try {
                await this.api(`/users/${this.user.id}`, {
                    method: 'PUT',
                    body: JSON.stringify({ password: this.password.form.new_password, current_password: this.password.form.current_password }),
                });
                this.password.success = window.ZenI18n.t('Hasło zmienione');
                setTimeout(() => { this.logout(); }, 800);
            } catch (e) { this.password.error = e.message; }
        },


        // ═══════════════════════════════════════════════════════════
        // KANBAN – NAWIGACJA (bez brzydkiego scrolla)
        // ═══════════════════════════════════════════════════════════
        // ═══════════════════════════════════════════════════════════
        // DETAIL VIEW – Klient / Lead
        // ═══════════════════════════════════════════════════════════
}; };
