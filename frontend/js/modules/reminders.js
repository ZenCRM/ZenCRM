window.ZenModules = window.ZenModules || {};
window.ZenModules.reminders = () => {
    let audio, timer, poll, session = 0, loading = false, previousFocus;
    return {
        reminders: [], allReminders: [], remindersOpen: false, reminderAdding: false, reminderActive: null,
        reminderTitle: '', reminderDate: '', reminderLink: '', reminderError: '', reminderBusy: false,
        reminderSnooze: '10', reminderSoundReady: false, allRemindersLoading: false,
        startReminders() {
            this.stopReminders();
            if (!this.token) return;
            this.loadReminders();
            if (this.currentView === 'notifications') this.loadAllReminders();
            poll = setInterval(() => {
                this.loadReminders();
                if (this.currentView === 'notifications') this.loadAllReminders();
            }, 15000);
            timer = setInterval(() => this.checkReminders(), 1000);
        },
        stopReminders() {
            session++; loading = false; clearInterval(timer); clearInterval(poll);
            this.reminders = []; this.allReminders = []; this.reminderActive = null; this.remindersOpen = false;
            this.reminderAdding = false; this.reminderError = ''; this.reminderBusy = false;
            this.reminderSoundReady = false; this.allRemindersLoading = false;
            if (audio) { audio.pause(); audio = null; }
        },
        async enableReminderSound() {
            try {
                if (!audio) { audio = new Audio('/audio/dzwonek.mp3'); audio.preload = 'auto'; }
                if (this.reminderSoundReady) return;
                audio.muted = true;
                await audio.play(); audio.pause(); audio.currentTime = 0; audio.muted = false;
                this.reminderSoundReady = true;
            } catch (_) { if(audio) audio.muted=false; this.reminderSoundReady = false; }
        },
        playReminderSound() {
            if (!audio || !this.reminderSoundReady) return;
            audio.currentTime = 0;
            audio.play().catch(() => { this.reminderSoundReady = false; });
        },
        async loadReminders() {
            if (!this.token || loading || this.reminderBusy) return;
            const generation = session; loading = true;
            try {
                const rows = await this.api('/reminders');
                if (generation !== session) return;
                this.reminders = rows;
                if (this.reminderActive && !rows.some(r => r.id===this.reminderActive.id && Date.parse(r.remind_at)<=Date.now())) this.reminderActive=null;
                this.checkReminders();
            } catch(e) { if (generation===session) this.reminderError=e.message; }
            finally { if (generation===session) loading=false; }
        },
        async loadAllReminders() {
            if (!this.token || this.allRemindersLoading) return;
            this.allRemindersLoading = true;
            try {
                const rows = await this.api('/reminders?include_archived=true');
                this.allReminders = rows;
            } catch (e) {
                console.warn('Błąd ładowania wszystkich przypomnień:', e.message);
            } finally {
                this.allRemindersLoading = false;
            }
        },
        checkReminders() {
            if (!this.token || this.reminderActive || this.reminderBusy) return;
            const next=this.reminders.find(r => Date.parse(r.remind_at)<=Date.now());
            if (!next) return;
            previousFocus = document.activeElement;
            this.reminderActive=next; this.reminderError=''; this.reminderSnooze='10';
            this.playReminderSound();
            this.$nextTick(() => this.$refs.reminderDismiss?.focus());
        },
        toggleReminders() {
            this.enableReminderSound(); this.remindersOpen=!this.remindersOpen;
            this.notificationsOpen=false; this.reminderError='';
            if (this.remindersOpen) this.loadReminders();
        },
        addReminder() {
            this.enableReminderSound(); this.reminderAdding=true; this.reminderTitle=''; this.reminderError='';
            const d=new Date(Date.now()+3600000); d.setMinutes(d.getMinutes()-d.getTimezoneOffset());
            this.reminderDate=d.toISOString().slice(0,16);
            this.reminderLink = location.hash ? location.href : (location.pathname !== '/' ? location.href : '');
            this.$nextTick(() => this.$refs.reminderTitle?.focus());
        },
        async saveReminder() {
            if(this.reminderBusy) return;
            this.enableReminderSound(); this.reminderBusy=true; this.reminderError=''; const generation=++session; loading=false;
            try {
                const date=new Date(this.reminderDate);
                if (!this.reminderTitle.trim() || !Number.isFinite(+date) || +date<=Date.now()) throw new Error('Wpisz treść i wybierz przyszłą datę oraz godzinę.');
                const link = this.reminderLink.trim() || null;
                const row=await this.api('/reminders',{method:'POST',body:JSON.stringify({title:this.reminderTitle,remind_at:date.toISOString(),link})});
                if(generation!==session) return;
                this.reminders=[...this.reminders,row].sort((a,b)=>Date.parse(a.remind_at)-Date.parse(b.remind_at));
                this.allReminders=[row, ...this.allReminders.filter(r=>r.id!==row.id)];
                this.reminderAdding=false;
            } catch(e) { if(generation===session) this.reminderError=e.message; }
            finally { if(generation===session) this.reminderBusy=false; }
        },
        async resolveReminder(row, action) {
            if (!row || this.reminderBusy) return;
            this.enableReminderSound(); this.reminderBusy=true; this.reminderError=''; const generation=++session; loading=false;
            try {
                const saved=await this.api('/reminders/'+row.id,{method:'PUT',body:JSON.stringify({action,minutes:Number(this.reminderSnooze)})});
                if(generation!==session) return;
                this.reminders=this.reminders.filter(r=>r.id!==row.id);
                if(!saved.dismissed) this.reminders.push(saved);
                this.reminders.sort((a,b)=>Date.parse(a.remind_at)-Date.parse(b.remind_at));
                this.allReminders=this.allReminders.map(r => r.id === saved.id ? saved : r);
                if (!this.allReminders.some(r => r.id === saved.id)) this.allReminders.unshift(saved);
                if(this.reminderActive?.id===row.id) { if(audio) { audio.pause(); audio.currentTime=0; } this.reminderActive=null; previousFocus?.focus(); }
            } catch(e) { if(generation===session) this.reminderError=e.message; }
            finally { if(generation===session) { this.reminderBusy=false; this.checkReminders(); } }
        },
        async restoreReminder(row) {
            if (!row || this.reminderBusy) return;
            this.reminderBusy = true;
            try {
                const saved = await this.api('/reminders/' + row.id, { method: 'PUT', body: JSON.stringify({ action: 'restore' }) });
                this.allReminders = this.allReminders.map(r => r.id === saved.id ? saved : r);
                this.reminders = [...this.reminders.filter(r => r.id !== saved.id), saved].sort((a,b)=>Date.parse(a.remind_at)-Date.parse(b.remind_at));
                if (typeof this.notify === 'function') this.notify('Przywrócono przypomnienie do aktywnych');
            } catch (e) {
                if (typeof this.notify === 'function') this.notify(e.message, 'error');
            } finally {
                this.reminderBusy = false;
            }
        },
        async deleteReminder(row) {
            if (!row || this.reminderBusy) return;
            if (!confirm('Czy na pewno chcesz trwale usunąć to przypomnienie?')) return;
            this.reminderBusy = true;
            try {
                await this.api('/reminders/' + row.id, { method: 'DELETE' });
                this.reminders = this.reminders.filter(r => r.id !== row.id);
                this.allReminders = this.allReminders.filter(r => r.id !== row.id);
                if (this.reminderActive?.id === row.id) this.reminderActive = null;
                if (typeof this.notify === 'function') this.notify('Usunięto przypomnienie');
            } catch (e) {
                if (typeof this.notify === 'function') this.notify(e.message, 'error');
            } finally {
                this.reminderBusy = false;
            }
        },
        openLink(url) {
            if (!url) return;
            if (url.startsWith('#')) {
                const targetView = url.slice(1);
                if (typeof this.selectView === 'function') this.selectView(targetView);
                else location.hash = url;
            } else {
                window.open(url, '_blank', 'noopener,noreferrer');
            }
        },
        trapReminderFocus(event) {
            const items=[...event.currentTarget.querySelectorAll('button,select,a[href]')].filter(el=>!el.disabled && el.offsetParent!==null);
            const first=items[0],last=items[items.length-1];
            if(event.shiftKey && document.activeElement===first) { event.preventDefault(); last?.focus(); }
            if(!event.shiftKey && document.activeElement===last) { event.preventDefault(); first?.focus(); }
        },
    };
};
