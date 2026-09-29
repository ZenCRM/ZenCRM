/* ═══════════════════════════════════════════════
   ZenCRM – moduł Telefonia & SMS API
   ═══════════════════════════════════════════════ */
window.ZenModules = window.ZenModules || {};

window.ZenModules.sms = function () {
    return {
        smsTab: 'messages',       // 'messages' | 'calls' | 'stats' | 'devices' | 'queue'
        smsDevices: [],
        smsCalls: [],
        smsMessages: [],
        smsThreads: [],
        smsQueue: [],
        smsStats: null,
        smsLoading: false,
        smsError: '',
        callNoteModal: { open: false, callId: null, note: '', saving: false, error: '' },
        openCallNote(call) {
            this.callNoteModal = { open: true, callId: call.id, note: call.note || '', saving: false, error: '' };
        },
        async saveCallNote() {
            if (this.callNoteModal.saving) return;
            this.callNoteModal.saving = true;
            this.callNoteModal.error = '';
            try {
                const saved = await this.api(`/sms/calls/${this.callNoteModal.callId}/note`, {
                    method: 'PUT', body: JSON.stringify({ note: this.callNoteModal.note })
                });
                for (const calls of [this.smsCalls, this.entityTelephony.calls, this.entityTelephonyModal.calls]) {
                    const call = calls.find(item => item.id === saved.id);
                    if (call) call.note = saved.note;
                }
                this.callNoteModal.open = false;
                this.notify(window.ZenI18n.t('Zapisano opis połączenia'));
            } catch (e) {
                this.callNoteModal.error = e.message;
            } finally {
                this.callNoteModal.saving = false;
            }
        },
        smsFilter: { search: '', type: 'all', deviceId: '' },

        smsComposer: {
            open: false,
            deviceId: '',
            clientId: '',
            phoneNumber: '',
            message: '',
            sending: false,
            error: '',
            success: '',
        },

        deviceModal: {
            open: false,
            editingId: null,
            form: { name: '', phone_number: '', token: '', sync_from: '', is_active: true },
            error: '',
        },

        actionModal: {
            open: false,
            deviceId: null,
            action: '',
            actionTitle: '',
            phone: '',
            limit: 500,
            startDate: '',
            endDate: '',
            loading: false,
            error: '',
        },

        smsThreadModal: {
            open: false,
            address: '',
            client: null,
            messages: [],
            loading: false,
            replyText: '',
            sending: false,
        },

        syncingTelephony: false,

        entityTelephonyModal: {
            open: false,
            loading: false,
            type: '',
            id: null,
            title: '',
            phones: [],
            selectedPhone: '',
            calls: [],
            messages: [],
            replyText: '',
            sending: false,
            tab: 'all',
        },

        entityTelephony: {
            loading: false,
            type: '',
            id: null,
            phones: [],
            selectedPhone: '',
            calls: [],
            messages: [],
            replyText: '',
            sending: false,
        },

        // ═══════ SYNCHRONIZACJA & URZĄDZENIA ═══════
        async loadSmsDevices() {
            try {
                const devData = await this.api('/sms/devices');
                this.smsDevices = Array.isArray(devData) ? devData : [];
                return this.smsDevices;
            } catch (_) {
                return [];
            }
        },

        async syncTelephony() {
            if (this.syncingTelephony) return;
            this.syncingTelephony = true;
            try {
                const res = await this.api('/sms/sync', { method: 'POST' });
                if (res && res.queued_tasks > 0) {
                    this.notify(window.ZenI18n.t('Zlecono synchronizację telefonu'));
                } else {
                    this.notify(window.ZenI18n.t('Brak aktywnych telefonów do synchronizacji'));
                }
                if (this.currentView === 'sms') {
                    await this.loadSmsData();
                }
                if (this.detailView && this.detailView.open && this.detailView.tab === 'telephony') {
                    await this.loadEntityTelephony(this.detailView.type, this.detailView.data?.id, this.detailView.data?.phone);
                }
                if (this.entityTelephonyModal && this.entityTelephonyModal.open) {
                    await this.refreshEntityTelephonyModal();
                }
            } catch (err) {
                this.notify(err.message || window.ZenI18n.t('Błąd synchronizacji telefonu'));
            } finally {
                this.syncingTelephony = false;
            }
        },

        // ═══════ ŁADOWANIE DANYCH ═══════
        async loadSmsData() {
            this.smsLoading = true;
            this.smsError = '';
            try {
                // Załaduj urządzenia
                await this.loadSmsDevices();

                if (this.smsTab === 'messages') {
                    const [msgData, threadData] = await Promise.all([
                        this.api(`/sms/messages?search=${encodeURIComponent(this.smsFilter.search || '')}&type=${this.smsFilter.type || 'all'}&device_id=${this.smsFilter.deviceId || ''}`),
                        this.api('/sms/threads')
                    ]);
                    this.smsMessages = msgData.messages || [];
                    this.smsThreads = threadData || [];
                } else if (this.smsTab === 'calls') {
                    const callData = await this.api(`/sms/calls?search=${encodeURIComponent(this.smsFilter.search || '')}&type=${this.smsFilter.type || 'all'}&device_id=${this.smsFilter.deviceId || ''}`);
                    this.smsCalls = callData.calls || [];
                } else if (this.smsTab === 'stats') {
                    this.smsStats = await this.api('/sms/stats-summary');
                } else if (this.smsTab === 'queue') {
                    const qData = await this.api('/sms/queue');
                    this.smsQueue = Array.isArray(qData) ? qData : [];
                }
            } catch (err) {
                console.error('Błąd ładowania danych SMS:', err);
                this.smsError = err.message || window.ZenI18n.t('Nie udało się pobrać danych SMS');
            } finally {
                this.smsLoading = false;
            }
        },

        switchSmsTab(tab) {
            this.smsTab = tab;
            this.smsFilter.search = '';
            this.smsFilter.type = 'all';
            this.loadSmsData();
        },

        // ═══════ WYSYŁKA SMS ═══════
        sendSmsFromDetail(targetPhone = null, targetName = null) {
            if (!this.smsDevices || this.smsDevices.length === 0) {
                this.notify(window.ZenI18n.t('Musisz najpierw dodać telefon w zakładce Telefonia & SMS'), 'warning');
                return;
            }
            let phone = targetPhone;
            let clientId = null;
            if (this.detailView && this.detailView.type === 'client') {
                clientId = this.detailView.data?.id || null;
                if (!phone) {
                    const firstWithPhone = (this.detailView.contacts || []).find(c => c.phone);
                    if (firstWithPhone) {
                        phone = firstWithPhone.phone;
                    } else if (this.detailView.data?.phone) {
                        phone = this.detailView.data.phone;
                    }
                }
            } else if (this.detailView) {
                clientId = this.detailView.data?.client_id || null;
                if (!phone) {
                    phone = this.detailView.data?.phone || '';
                }
            }
            this.openSmsModal({
                phone: phone || '',
                clientId: clientId || null,
            });
        },

        hasConnectedPhone() {
            return Array.isArray(this.smsDevices) && this.smsDevices.length > 0;
        },

        async makePhoneCall(targetPhone = null, targetName = null) {
            if (!this.smsDevices || this.smsDevices.length === 0) {
                this.notify(window.ZenI18n.t('Musisz najpierw dodać telefon w zakładce Telefonia & SMS'), 'warning');
                return;
            }
            let phone = targetPhone;
            let clientId = null;
            if (this.detailView && this.detailView.type === 'client') {
                clientId = this.detailView.data?.id || null;
                if (!phone) {
                    const firstWithPhone = (this.detailView.contacts || []).find(c => c.phone);
                    if (firstWithPhone) {
                        phone = firstWithPhone.phone;
                    } else if (this.detailView.data?.phone) {
                        phone = this.detailView.data.phone;
                    }
                }
            } else if (this.detailView) {
                clientId = this.detailView.data?.client_id || null;
                if (!phone) {
                    phone = this.detailView.data?.phone || '';
                }
            }

            if (!phone) {
                this.notify(window.ZenI18n.t('Brak numeru telefonu do połączenia'), 'warning');
                return;
            }

            const onlineDev = this.smsDevices.find(d => d.is_online);
            const dev = onlineDev || this.smsDevices[0];

            const confirmMsg = targetName
                ? window.ZenI18n.t('Czy chcesz zlecić telefonowi „{device}” natychmiastowe połączenie z {name} ({phone})?', {device: dev.name, name: targetName, phone})
                : window.ZenI18n.t('Czy chcesz zlecić telefonowi „{device}” natychmiastowe połączenie z numerem {phone}?', {device: dev.name, phone});

            if (!confirm(confirmMsg)) return;

            try {
                const res = await this.api('/sms/call', {
                    method: 'POST',
                    body: JSON.stringify({
                        phone_number: phone,
                        device_id: dev.id,
                        client_id: clientId,
                    }),
                });

                this.notify(res.message || window.ZenI18n.t('Zlecono połączenie na telefonie!'));
                if (this.currentView === 'sms') {
                    await this.loadSmsData();
                }
                if (this.detailView && this.detailView.data?.id) {
                    if (typeof this.loadDetailActivities === 'function') await this.loadDetailActivities();
                    if (this.detailView.tab === 'telephony') {
                        await this.loadEntityTelephony(this.detailView.type, this.detailView.data.id, phone);
                    }
                }
            } catch (err) {
                this.notify(err.message || window.ZenI18n.t('Błąd zlecenia połączenia'), 'error');
            }
        },

        callContact(targetPhone = null, targetName = null) {
            if (this.user?.default_call_method === 'android') {
                if (!this.hasConnectedPhone()) { this.notify(window.ZenI18n.t('Brak podłączonego telefonu Android'), 'warning'); return; }
                return this.makePhoneCall(targetPhone, targetName);
            }
            let phone = targetPhone;
            if (!phone && this.detailView) {
                if (this.detailView.type === 'client') {
                    const firstWithPhone = (this.detailView.contacts || []).find(c => c.phone);
                    phone = firstWithPhone?.phone || this.detailView.data?.phone || '';
                } else {
                    phone = this.detailView.data?.phone || '';
                }
            }
            if (!phone) {
                this.notify(window.ZenI18n.t('Brak numeru telefonu do połączenia'), 'warning');
                return;
            }
            window.location.href = 'tel:' + phone;
        },

        openSmsModal(opts = {}) {
            if (!this.smsDevices || this.smsDevices.length === 0) {
                this.notify(window.ZenI18n.t('Musisz najpierw dodać telefon w zakładce Telefonia & SMS'), 'warning');
                return;
            }
            let initialDevId = '';
            const onlineDev = this.smsDevices.find(d => d.is_online);
            initialDevId = onlineDev ? onlineDev.id : this.smsDevices[0].id;

            let phone = opts.phone || '';
            let clientId = opts.clientId || '';

            // Jeśli przekazano klienta bez numeru, uzupełnij z bazy
            if (clientId && !phone) {
                const c = this.clients.find(x => x.id === clientId);
                if (c && c.phone) phone = c.phone;
            }

            this.smsComposer = {
                open: true,
                deviceId: initialDevId,
                clientId: clientId || '',
                phoneNumber: phone,
                message: opts.message || '',
                sending: false,
                error: '',
                success: '',
            };
        },

        closeSmsModal() {
            this.smsComposer.open = false;
            this.smsComposer.error = '';
            this.smsComposer.success = '';
        },

        onSmsClientSelected() {
            if (!this.smsComposer.clientId) return;
            const c = this.clients.find(x => x.id === Number(this.smsComposer.clientId));
            if (c && c.phone) {
                this.smsComposer.phoneNumber = c.phone;
            }
        },

        async sendSmsSubmit() {
            if (!this.smsComposer.phoneNumber?.trim()) {
                this.smsComposer.error = window.ZenI18n.t('Podaj numer telefonu odbiorcy');
                return;
            }
            if (!this.smsComposer.message?.trim()) {
                this.smsComposer.error = window.ZenI18n.t('Wpisz treść wiadomości SMS');
                return;
            }

            this.smsComposer.sending = true;
            this.smsComposer.error = '';
            try {
                await this.api('/sms/send', {
                    method: 'POST',
                    body: JSON.stringify({
                        device_id: this.smsComposer.deviceId ? Number(this.smsComposer.deviceId) : null,
                        client_id: this.smsComposer.clientId ? Number(this.smsComposer.clientId) : null,
                        phone_number: this.smsComposer.phoneNumber.trim(),
                        message: this.smsComposer.message.trim(),
                    }),
                });

                this.notify(window.ZenI18n.t('Zlecono wysłanie wiadomości SMS'));
                this.closeSmsModal();
                if (this.currentView === 'sms') {
                    await this.loadSmsData();
                }
            } catch (err) {
                this.smsComposer.error = err.message || window.ZenI18n.t('Błąd podczas kolejkowania SMS');
            } finally {
                this.smsComposer.sending = false;
            }
        },

        // ═══════ URZĄDZENIA (TELEFONY) ═══════
        openDeviceModal(dev = null) {
            if (dev) {
                this.deviceModal = {
                    open: true,
                    editingId: dev.id,
                    form: {
                        name: dev.name || '',
                        phone_number: dev.phone_number || '',
                        token: dev.token || '',
                        sync_from: dev.sync_from || '',
                        is_active: dev.is_active !== false,
                    },
                    error: '',
                };
            } else {
                this.deviceModal = {
                    open: true,
                    editingId: null,
                    form: {
                        name: '',
                        phone_number: '',
                        token: '',
                        sync_from: '',
                        is_active: true,
                    },
                    error: '',
                };
            }
        },

        generateDeviceToken() {
            const randomHex = Array.from(crypto.getRandomValues(new Uint8Array(16)))
                .map(b => b.toString(16).padStart(2, '0')).join('');
            this.deviceModal.form.token = `zen_sms_${randomHex}`;
        },

        async saveDeviceSubmit() {
            if (!this.deviceModal.form.name?.trim()) {
                this.deviceModal.error = window.ZenI18n.t('Nazwa telefonu jest wymagana');
                return;
            }
            if (!this.deviceModal.form.token?.trim()) {
                this.generateDeviceToken();
            }

            this.deviceModal.error = '';
            try {
                if (this.deviceModal.editingId) {
                    await this.api(`/sms/devices/${this.deviceModal.editingId}`, {
                        method: 'PUT',
                        body: JSON.stringify(this.deviceModal.form),
                    });
                    this.notify(window.ZenI18n.t('Zaktualizowano telefon'));
                } else {
                    await this.api('/sms/devices', {
                        method: 'POST',
                        body: JSON.stringify(this.deviceModal.form),
                    });
                    this.notify(window.ZenI18n.t('Dodano telefon komórkowy'));
                }
                this.deviceModal.open = false;
                await this.loadSmsData();
            } catch (err) {
                this.deviceModal.error = err.message || window.ZenI18n.t('Błąd zapisu telefonu');
            }
        },

        async deleteDeviceSubmit(id) {
            if (!confirm(window.ZenI18n.t('Czy na pewno chcesz usunąć to urządzenie z systemu?'))) return;
            try {
                await this.api(`/sms/devices/${id}`, { method: 'DELETE' });
                this.notify(window.ZenI18n.t('Usunięto urządzenie'));
                await this.loadSmsData();
            } catch (err) {
                this.notify(err.message);
            }
        },

        // ═══════ WYZWALANIE AKCJI NA TELEFONIE ═══════
        openActionModal(deviceId, action, actionTitle) {
            const dev = this.smsDevices.find(d => d.id === deviceId);
            this.actionModal = {
                open: true,
                deviceId: deviceId,
                action: action,
                actionTitle: actionTitle,
                phone: dev ? (dev.phone_number || '') : '',
                limit: action === 'get_full_history' ? 500 : 100,
                startDate: '',
                endDate: '',
                loading: false,
                error: '',
            };
        },

        async executeActionSubmit() {
            this.actionModal.loading = true;
            this.actionModal.error = '';
            try {
                const payload = {
                    device_id: this.actionModal.deviceId,
                    action: this.actionModal.action,
                    phone_number: this.actionModal.phone,
                    limit: this.actionModal.limit,
                };
                if (this.actionModal.action === 'get_sms_history_by_date') {
                    if (!this.actionModal.startDate || !this.actionModal.endDate) {
                        throw new Error(window.ZenI18n.t('Wybierz zakres dat'));
                    }
                    payload.start_date = new Date(this.actionModal.startDate).getTime();
                    payload.end_date = new Date(this.actionModal.endDate).getTime();
                }

                await this.api('/sms/actions/trigger', {
                    method: 'POST',
                    body: JSON.stringify(payload),
                });

                this.notify(window.ZenI18n.t('Zlecenie zostało dodane do kolejki telefonu'));
                this.actionModal.open = false;
                await this.loadSmsData();
            } catch (err) {
                this.actionModal.error = err.message || window.ZenI18n.t('Błąd zlecenia akcji');
            } finally {
                this.actionModal.loading = false;
            }
        },

        // Szybkie wyzwalanie bez modala (np. Pobierz statystyki)
        async quickTrigger(deviceId, action) {
            try {
                await this.api('/sms/actions/trigger', {
                    method: 'POST',
                    body: JSON.stringify({ device_id: deviceId, action: action }),
                });
                this.notify(window.ZenI18n.t('Zlecono pobranie danych z telefonu'));
                await this.loadSmsData();
            } catch (err) {
                this.notify(err.message);
            }
        },

        // ═══════ PODGLĄD WĄTKU WIADOMOŚCI ═══════
        async viewThread(address, client = null, contact = null) {
            if (!contact && this.contacts) {
                const norm = this.normalizePhone(address);
                const ct = this.contacts.find(c => this.normalizePhone(c.phone) === norm);
                if (ct) {
                    contact = {
                        id: ct.id,
                        name: [ct.first_name, ct.last_name].filter(Boolean).join(' ') || ct.name,
                        position: ct.position,
                        client_id: ct.client_id
                    };
                }
            }
            if (!client && contact && contact.client_id && this.clients) {
                client = this.clients.find(c => c.id === contact.client_id) || null;
            }

            this.smsThreadModal = {
                open: true,
                address: address,
                client: client,
                contact: contact,
                messages: [],
                loading: true,
                replyText: '',
                sending: false,
            };
            try {
                const data = await this.api(`/sms/messages?address=${encodeURIComponent(address)}&per_page=100`);
                // Odwróć, by starsze były na górze, nowsze na dole
                this.smsThreadModal.messages = (data.messages || []).reverse();
            } catch (err) {
                console.error(err);
            } finally {
                this.smsThreadModal.loading = false;
            }
        },

        async sendThreadReply() {
            if (!this.smsThreadModal.replyText?.trim()) return;
            this.smsThreadModal.sending = true;
            try {
                let devId = null;
                if (this.smsDevices && this.smsDevices.length > 0) {
                    const onlineDev = this.smsDevices.find(d => d.is_online);
                    devId = onlineDev ? onlineDev.id : this.smsDevices[0].id;
                }

                await this.api('/sms/send', {
                    method: 'POST',
                    body: JSON.stringify({
                        device_id: devId,
                        phone_number: this.smsThreadModal.address,
                        message: this.smsThreadModal.replyText.trim(),
                        client_id: this.smsThreadModal.client ? this.smsThreadModal.client.id : null,
                    }),
                });

                this.notify(window.ZenI18n.t('Wysłano odpowiedź SMS'));
                this.smsThreadModal.replyText = '';
                // Odśwież wiadomości w wątku
                const data = await this.api(`/sms/messages?address=${encodeURIComponent(this.smsThreadModal.address)}&per_page=100`);
                this.smsThreadModal.messages = (data.messages || []).reverse();
                await this.loadSmsData();
            } catch (err) {
                this.notify(err.message);
            } finally {
                this.smsThreadModal.sending = false;
            }
        },

        // ═══════ ANULOWANIE ZADANIA W KOLEJCE ═══════
        async cancelQueueItem(id) {
            if (!confirm(window.ZenI18n.t('Czy na pewno chcesz anulować to zadanie?'))) return;
            try {
                await this.api(`/sms/queue/${id}`, { method: 'DELETE' });
                this.notify(window.ZenI18n.t('Zadanie anulowane'));
                await this.loadSmsData();
            } catch (err) {
                this.notify(err.message);
            }
        },

        // ═══════ HISTORIA POŁĄCZEŃ I SMS DLA DOWOLNEGO REKORDU ═══════
        async loadEntityTelephony(type, id, phone = '') {
            this.entityTelephony.loading = true;
            this.entityTelephony.type = type;
            this.entityTelephony.id = id;
            try {
                const res = await this.api(`/sms/entity-history?type=${type}&id=${id || ''}&phone=${encodeURIComponent(phone || '')}`);
                this.entityTelephony.calls = res.calls || [];
                this.entityTelephony.messages = res.messages || [];
                this.entityTelephony.phones = res.phones || [];
                if (this.entityTelephony.phones.length > 0 && !this.entityTelephony.selectedPhone) {
                    this.entityTelephony.selectedPhone = this.entityTelephony.phones[0];
                }
            } catch (err) {
                console.error('Błąd ładowania historii połączeń:', err);
                this.entityTelephony.calls = [];
                this.entityTelephony.messages = [];
            } finally {
                this.entityTelephony.loading = false;
            }
        },

        normalizePhone(phone) {
            if (!phone) return '';
            const digits = String(phone).replace(/\D/g, '');
            return digits.length >= 9 ? digits.slice(-9) : digits;
        },

        normalizePhoneVariants(phone) {
            if (!phone) return [];
            const digits = String(phone).replace(/\D/g, '');
            if (!digits) return [];
            const set = new Set([digits]);
            if (digits.startsWith('0048') && digits.length > 4) {
                set.add(digits.slice(4));
                set.add('48' + digits.slice(4));
            } else if (digits.startsWith('48') && digits.length > 2) {
                set.add(digits.slice(2));
            } else if (digits.length === 9) {
                set.add('48' + digits);
            }
            if (digits.startsWith('0') && digits.length === 10) {
                set.add(digits.slice(1));
                set.add('48' + digits.slice(1));
            }
            if (digits.length >= 9) {
                set.add(digits.slice(-9));
            }
            return Array.from(set).filter(v => v.length >= 6);
        },

        phonesMatch(p1, p2) {
            if (!p1 || !p2) return false;
            const v1 = this.normalizePhoneVariants(p1);
            const v2 = new Set(this.normalizePhoneVariants(p2));
            return v1.some(v => v2.has(v));
        },

        getContactByPhone(phone) {
            if (!phone) return null;
            const detailContacts = (this.detailView && this.detailView.contacts) || [];
            const allContacts = this.contacts || [];
            const combined = [...detailContacts, ...allContacts];
            for (const c of combined) {
                if (c.phone && this.phonesMatch(c.phone, phone)) {
                    let clientName = '';
                    if (c.client_id && this.clients) {
                        const cl = this.clients.find(x => x.id === c.client_id);
                        if (cl) clientName = cl.name;
                    }
                    return {
                        id: c.id,
                        name: [c.first_name, c.last_name].filter(Boolean).join(' ') || c.name || '',
                        position: c.position || '',
                        phone: c.phone,
                        client_name: clientName || c.client_name || ''
                    };
                }
            }
            if (this.clients) {
                for (const cl of this.clients) {
                    if (cl.phone && this.phonesMatch(cl.phone, phone)) {
                        return {
                            id: cl.id,
                            name: cl.name,
                            position: '',
                            phone: cl.phone,
                            client_name: cl.name
                        };
                    }
                }
            }
            return null;
        },

        formatPhoneLabel(phone) {
            if (!phone) return '';
            const c = this.getContactByPhone(phone);
            if (c && c.name) {
                return `${c.name} (${phone})`;
            }
            return phone;
        },

        async openEntityTelephonyModal(type, item) {
            if (!item) return;
            let title = '';
            let phone = item.phone || item.number || '';
            let clientId = null;
            if (type === 'client') {
                title = item.name || '';
                clientId = item.id;
            } else if (type === 'lead') {
                title = item.title || '';
                clientId = item.client_id || null;
            } else if (type === 'contact') {
                title = [item.first_name, item.last_name].filter(Boolean).join(' ') || item.name || '';
                clientId = item.client_id || null;
                if (clientId && this.clients) {
                    const cl = this.clients.find(c => c.id === clientId);
                    if (cl) title += ` (${cl.name})`;
                }
            } else {
                title = item.name || item.number || phone;
            }
            this.entityTelephonyModal = {
                open: true,
                loading: true,
                type: type,
                id: item.id || 0,
                clientId: clientId,
                item: item,
                title: title,
                phones: phone ? [phone] : [],
                selectedPhone: phone || '',
                calls: [],
                messages: [],
                replyText: '',
                sending: false,
                tab: 'all',
            };
            try {
                const res = await this.api(`/sms/entity-history?type=${type}&id=${item.id || 0}&phone=${encodeURIComponent(phone)}`);
                this.entityTelephonyModal.calls = res.calls || [];
                this.entityTelephonyModal.messages = res.messages || [];
                const resPhones = res.phones || res.phone_numbers || [];
                this.entityTelephonyModal.phones = resPhones.length ? resPhones : (phone ? [phone] : []);
                if (this.entityTelephonyModal.phones.length > 0 && !this.entityTelephonyModal.selectedPhone) {
                    this.entityTelephonyModal.selectedPhone = this.entityTelephonyModal.phones[0];
                }
            } catch (err) {
                console.error('Błąd modalu telefonii:', err);
            } finally {
                this.entityTelephonyModal.loading = false;
            }
        },

        async refreshEntityTelephonyModal() {
            if (!this.entityTelephonyModal.open || !this.entityTelephonyModal.type) return;
            try {
                const res = await this.api(`/sms/entity-history?type=${this.entityTelephonyModal.type}&id=${this.entityTelephonyModal.id}&phone=${encodeURIComponent(this.entityTelephonyModal.selectedPhone || '')}`);
                this.entityTelephonyModal.calls = res.calls || [];
                this.entityTelephonyModal.messages = res.messages || [];
            } catch (_) {}
        },

        async sendEntityTelephonyModalSms() {
            const targetPhone = this.entityTelephonyModal.selectedPhone || (this.entityTelephonyModal.phones && this.entityTelephonyModal.phones[0]);
            if (!targetPhone) {
                this.notify(window.ZenI18n.t('Brak numeru telefonu odbiorcy'));
                return;
            }
            if (!this.entityTelephonyModal.replyText?.trim()) {
                this.notify(window.ZenI18n.t('Wpisz treść wiadomości SMS'));
                return;
            }
            this.entityTelephonyModal.sending = true;
            try {
                let devId = null;
                if (this.smsDevices && this.smsDevices.length > 0) {
                    const onlineDev = this.smsDevices.find(d => d.is_online);
                    devId = onlineDev ? onlineDev.id : this.smsDevices[0].id;
                }
                const clientId = this.entityTelephonyModal.clientId || (this.entityTelephonyModal.type === 'client' ? this.entityTelephonyModal.id : null);
                await this.api('/sms/send', {
                    method: 'POST',
                    body: JSON.stringify({
                        device_id: devId,
                        phone_number: targetPhone,
                        message: this.entityTelephonyModal.replyText.trim(),
                        client_id: clientId,
                    }),
                });
                this.notify(window.ZenI18n.t('Wysłano wiadomość SMS'));
                this.entityTelephonyModal.replyText = '';
                await this.refreshEntityTelephonyModal();
                if (this.currentView === 'sms') await this.loadSmsData();
            } catch (err) {
                this.notify(err.message || window.ZenI18n.t('Błąd podczas wysyłki SMS'));
            } finally {
                this.entityTelephonyModal.sending = false;
            }
        },

        async sendInlineEntityTelephonySms() {
            const targetPhone = this.entityTelephony.selectedPhone || (this.entityTelephony.phones && this.entityTelephony.phones[0]);
            if (!targetPhone) {
                this.notify(window.ZenI18n.t('Brak numeru telefonu odbiorcy'));
                return;
            }
            if (!this.entityTelephony.replyText?.trim()) {
                this.notify(window.ZenI18n.t('Wpisz treść wiadomości SMS'));
                return;
            }
            this.entityTelephony.sending = true;
            try {
                let devId = null;
                if (this.smsDevices && this.smsDevices.length > 0) {
                    const onlineDev = this.smsDevices.find(d => d.is_online);
                    devId = onlineDev ? onlineDev.id : this.smsDevices[0].id;
                }
                const clientId = this.entityTelephony.type === 'client' ? this.entityTelephony.id : null;
                await this.api('/sms/send', {
                    method: 'POST',
                    body: JSON.stringify({
                        device_id: devId,
                        phone_number: targetPhone,
                        message: this.entityTelephony.replyText.trim(),
                        client_id: clientId,
                    }),
                });
                this.notify(window.ZenI18n.t('Wysłano wiadomość SMS'));
                this.entityTelephony.replyText = '';
                await this.loadEntityTelephony(this.entityTelephony.type, this.entityTelephony.id, targetPhone);
                if (this.currentView === 'sms') await this.loadSmsData();
            } catch (err) {
                this.notify(err.message || window.ZenI18n.t('Błąd podczas wysyłki SMS'));
            } finally {
                this.entityTelephony.sending = false;
            }
        },

        // ═══════ POMOCNICZE ═══════
        copyToClipboard(text, label = window.ZenI18n.t('Skopiowano do schowka')) {
            if (!text) return;
            navigator.clipboard.writeText(text).then(() => {
                this.notify(window.ZenI18n.t(label));
            }).catch(() => {
                const el = document.createElement('textarea');
                el.value = text;
                document.body.appendChild(el);
                el.select();
                document.execCommand('copy');
                document.body.removeChild(el);
                this.notify(window.ZenI18n.t(label));
            });
        },

        formatLastSeen(iso) {
            if (!iso) return window.ZenI18n.t('Nigdy');
            try {
                const diffSec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
                if (diffSec < 15) return window.ZenI18n.t('Przed chwilą (online)');
                if (diffSec < 60) return `${diffSec} ${window.ZenI18n.t('sekund temu')}`;
                const diffMin = Math.floor(diffSec / 60);
                if (diffMin < 60) return `${diffMin} ${window.ZenI18n.t('minut temu')}`;
                const diffHours = Math.floor(diffMin / 60);
                if (diffHours < 24) return `${diffHours} ${window.ZenI18n.t('godzin temu')}`;
                return new Date(iso).toLocaleDateString(window.ZenI18n.locale, {
                    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
                });
            } catch {
                return iso;
            }
        },

        callTypeLabel(t) {
            return {
                incoming: window.ZenI18n.t('Przychodzące'),
                outgoing: window.ZenI18n.t('Wychodzące'),
                missed: window.ZenI18n.t('Nieodebrane'),
                rejected: window.ZenI18n.t('Odrzucone')
            }[t] || t;
        },

        callTypeClass(t) {
            return {
                incoming: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
                outgoing: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
                missed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
                rejected: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
            }[t] || 'bg-gray-100 text-gray-700';
        },

        actionLabel(a) {
            return {
                make_call: window.ZenI18n.t('Zlecenie połączenia'),
                send_sms: window.ZenI18n.t('Wysyłka SMS'),
                get_stats: window.ZenI18n.t('Pobranie statystyk'),
                get_full_history: window.ZenI18n.t('Biling połączeń'),
                get_sms_history: window.ZenI18n.t('Historia SMS numeru'),
                get_sms_history_by_date: window.ZenI18n.t('Historia SMS z zakresu')
            }[a] || a;
        },

        queueStatusClass(s) {
            return {
                pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
                processing: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
                called: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
                sent: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
                completed: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
                failed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
            }[s] || 'bg-gray-100 text-gray-700';
        },
    };
};
