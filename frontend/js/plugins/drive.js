/* Reviewed native connector. Google credentials never enter this component. */
(function () {
    'use strict';
    const t = key => window.ZenI18n.t(key);
    function safeURL(value) {
        try { const url = new URL(value); return url.protocol === 'https:' && url.hostname === 'drive.google.com' && !url.port && !url.username && !url.password && !url.search && !url.hash &&
            /^\/(file\/d\/[A-Za-z0-9_-]+\/view|drive\/folders\/[A-Za-z0-9_-]+)$/.test(url.pathname) ? url.href : ''; } catch (_) { return ''; }
    }
    async function upload(ctx, blob, name) {
        const token = ctx.token;
        if (!token || !ctx.active()) throw Error(t('Sesja aplikacji zakończona'));
        const form = new FormData(); form.append('file', blob, name);
        const response = await fetch('/api/plugins/google-drive/files', {method:'POST', body:form,
            headers:{Authorization:'Bearer ' + token, 'Accept-Language':window.ZenI18n.locale}});
        if (ctx.token !== token || !ctx.active()) throw Error(t('Sesja aplikacji zakończona'));
        if (response.status === 401) { ctx.logout(); throw Error(t('Sesja wygasła – zaloguj się ponownie')); }
        if (!response.headers.get('Content-Type')?.includes('application/json')) throw Error(t('Błąd API'));
        const result = await response.json();
        if (ctx.token !== token || !ctx.active()) throw Error(t('Sesja aplikacji zakończona'));
        if (!response.ok) throw Error(t(result.error || 'Błąd API'));
        if (!safeURL(result.url)) throw Error(t('Nieprawidłowa odpowiedź Google Drive.'));
        return result;
    }
    window.ZenDrive = {safeURL, upload};
    window.pluginDrive = () => ({
        driveStatus:null, files:[], search:'', nextPage:'', pages:[''], pageIndex:0, busy:false, driveError:'', message:'', serial:0,
        init() {
            const result = new URLSearchParams(location.search).get('drive');
            if (result) {
                this.message = result === 'connected' ? t('Konto Google zostało połączone.') : result === 'denied' ? t('Połączenie konta Google zostało anulowane.') : '';
                const url = new URL(location.href); url.searchParams.delete('drive'); history.replaceState(null, '', url.pathname + url.search + url.hash);
            }
            this.$watch('token', () => { this.serial++; this.driveStatus=null; this.files=[]; this.driveError=''; this.message=''; });
            this.refresh();
        },
        destroy() { this.serial++; this.files=[]; this.driveStatus=null; },
        async refresh(reset = true) {
            const token=this.token, view=this.currentView, serial=++this.serial;
            const alive=()=>token===this.token && view===this.currentView && serial===this.serial && this.active();
            this.busy=true; this.driveError=''; this.files=[];
            if (reset) { this.pages=['']; this.pageIndex=0; }
            try {
                const status=await this.api('/plugins/google-drive/status');
                if (!alive()) return; this.driveStatus=status;
                if (status.connected) {
                    const result=await this.api('/plugins/google-drive/files?'+new URLSearchParams({search:this.search,page:this.pages[this.pageIndex]}));
                    if (!alive()) return; this.files=result.files; this.nextPage=result.next_page;
                } else this.nextPage='';
            } catch(error) { if (alive()) this.driveError=error.message; }
            finally { if (alive()) this.busy=false; }
        },
        async connect() {
            if (this.busy) return;
            const token=this.token, view=this.currentView; this.busy=true; this.driveError='';
            try {
                const result=await this.api('/plugins/google-drive/connect',{method:'POST',body:'{}'});
                if (token!==this.token || view!==this.currentView || !this.active()) return;
                const url=new URL(result.authorization_url);
                if (url.origin!=='https://accounts.google.com' || url.pathname!=='/o/oauth2/v2/auth' || url.username || url.password) throw Error(t('Błąd API'));
                location.assign(url.href);
            } catch(error) { if (token===this.token && view===this.currentView) this.driveError=error.message; }
            finally { if (token===this.token && view===this.currentView) this.busy=false; }
        },
        async disconnect() {
            if (this.busy) return;
            const token=this.token,view=this.currentView; this.busy=true; this.driveError='';
            try {
                const result=await this.api('/plugins/google-drive/connection',{method:'DELETE'});
                if (token!==this.token || view!==this.currentView || !this.active()) return;
                this.files=[]; this.driveStatus={...this.driveStatus,connected:false};
                this.message=t(result.revoked_at_google ? 'Konto Google zostało odłączone. Pliki pozostają na Twoim dysku.' : 'Połączenie w CRM usunięto. Cofnij też dostęp w ustawieniach konta Google.');
            } catch(error) { if (token===this.token && view===this.currentView) this.driveError=error.message; }
            finally { if (token===this.token && view===this.currentView) this.busy=false; }
        },
        async uploadSelected(event) {
            const file=event.target.files?.[0]; event.target.value='';
            if (!file || this.busy) return;
            if (file.size>this.driveStatus.upload_limit || !file.size) { this.driveError=t('Wybierz niepusty plik do 10 MB.'); return; }
            const token=this.token,view=this.currentView; this.busy=true; this.driveError='';
            try {
                await upload(this,file,file.name);
                if(token===this.token && view===this.currentView && this.active()) { this.message=t('Plik zapisano w folderze ZenCRM na Dysku Google.'); await this.refresh(); }
            } catch(error) { if(token===this.token && view===this.currentView) this.driveError=error.message; }
            finally { if(token===this.token && view===this.currentView) this.busy=false; }
        },
        next() { if(this.nextPage && !this.busy) { this.pages=this.pages.slice(0,this.pageIndex+1); this.pages.push(this.nextPage); this.pageIndex++; this.refresh(false); } },
        previous() { if(this.pageIndex && !this.busy) { this.pageIndex--; this.refresh(false); } },
        fileURL(file) { return safeURL(file.url); },
        fileSize(file) { const bytes=Number(file.size); return Number.isFinite(bytes) && bytes>0 ? (bytes/1024).toFixed(1)+' KB' : '—'; }
    });
})();
