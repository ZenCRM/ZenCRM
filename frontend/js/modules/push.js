window.ZenModules = window.ZenModules || {};
window.ZenModules.push = () => {
    let registration, listening = false;
    return {
        pushEnabled:false, pushBusy:false, pushError:'',
        get pushSupported() { return window.isSecureContext && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window; },
        async pushRegistration() {
            if (!this.pushSupported) throw new Error('Powiadomienia poza CRM wymagają HTTPS i przeglądarki obsługującej Web Push.');
            registration = await navigator.serviceWorker.register('/sw.js', {scope:'/'});
            await navigator.serviceWorker.ready;
            return registration;
        },
        async bindPushUser(userId) {
            const reg = await this.pushRegistration();
            await new Promise((resolve,reject) => {
                const channel = new MessageChannel();
                const timer = setTimeout(() => { channel.port1.close(); reject(new Error('Nie udało się aktywować powiadomień. Spróbuj ponownie.')); },5000);
                channel.port1.onmessage=()=>{clearTimeout(timer);channel.port1.close();resolve();};
                reg.active.postMessage({type:'PUSH_BIND',userId},[channel.port2]);
            });
        },
        async initPush() {
            this.pushEnabled=false;this.pushError='';
            if(!this.token || !this.pushSupported) return;
            if(!listening) {
                navigator.serviceWorker.addEventListener('message',event=>{
                    if(event.data?.type==='REMINDER_PUSH_OPEN' && this.token) { this.remindersOpen=true;this.loadReminders(); }
                });
                listening=true;
            }
            try {
                // Restore only an existing, explicitly permitted subscription.
                if(Notification.permission!=='granted') return;
                const reg=await this.pushRegistration(), sub=await reg.pushManager.getSubscription();
                if(sub) {
                    const uid=this.user.id;
                    await this.bindPushUser(uid);
                    await this.api('/push/subscriptions',{method:'POST',body:JSON.stringify(sub.toJSON())});
                    if(this.user?.id===uid) this.pushEnabled=true;
                }
            } catch(e) { this.pushError=e.message; }
        },
        async enablePush() {
            if(this.pushBusy) return;
            this.pushBusy=true;this.pushError='';
            try {
                if(!this.pushSupported) throw new Error('Powiadomienia poza CRM wymagają HTTPS i obsługi Web Push.');
                const uid=this.user.id;
                const permission=await Notification.requestPermission();
                if(permission!=='granted') throw new Error('Zezwól na powiadomienia w ustawieniach tej strony w przeglądarce.');
                const config=await this.api('/push/config');
                if(!config.enabled) throw new Error('Powiadomienia push są wyłączone na serwerze.');
                const reg=await this.pushRegistration();
                const raw=atob(config.public_key.replace(/-/g,'+').replace(/_/g,'/'));
                const key=Uint8Array.from(raw,c=>c.charCodeAt(0));
                const sub=await reg.pushManager.getSubscription() || await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:key});
                if(this.user?.id!==uid) { await sub.unsubscribe();return; }
                await this.bindPushUser(uid);
                await this.api('/push/subscriptions',{method:'POST',body:JSON.stringify(sub.toJSON())});
                this.pushEnabled=true;
            } catch(e) { this.pushError=e.message; }
            finally {this.pushBusy=false;}
        },
        async disablePush() {
            this.pushError='';
            if(!this.pushSupported) return;
            this.pushBusy=true;
            try {
                const reg=await navigator.serviceWorker.getRegistration('/');
                if(!reg) return;
                await this.bindPushUser(null);
                const sub=await reg.pushManager.getSubscription();
                if(sub) {
                    try { await this.api('/push/subscriptions',{method:'DELETE',body:JSON.stringify({endpoint:sub.endpoint})}); }
                    finally { await sub.unsubscribe(); }
                }
                const notices=await reg.getNotifications();notices.forEach(n=>n.close());
                this.pushEnabled=false;
            } catch(e) {this.pushError=e.message;}
            finally {this.pushBusy=false;}
        },
    };
};
