window.ZenModules = window.ZenModules || {};
window.ZenModules.notifications = () => ({
    notifications: [], notificationRead: [], notificationsOpen: false,
    notificationsLoading: false, notificationsError: '', notificationTimer: null,
    get unreadNotifications() { return this.notifications.filter(n => !this.notificationRead.includes(n.id)).length; },
    startNotifications() {
        this.stopNotifications();
        if (!this.token || !this.user) return;
        try { this.notificationRead = JSON.parse(localStorage.getItem('zen-notifications:'+this.user.id) || '[]'); if (!Array.isArray(this.notificationRead)) this.notificationRead=[]; } catch { this.notificationRead=[]; }
        this.loadNotifications();
        this.notificationTimer = setInterval(() => { if (!document.hidden) this.loadNotifications(); }, 60000);
    },
    stopNotifications() { clearInterval(this.notificationTimer); this.notificationTimer=null; this.notifications=[]; this.notificationRead=[]; this.notificationsOpen=false; },
    async loadNotifications() {
        if (!this.token || this.notificationsLoading) return;
        const token=this.token; this.notificationsLoading=true; this.notificationsError='';
        try { const rows=await this.api('/notifications'); if(this.token===token) this.notifications=rows; }
        catch(e) { if(this.token===token) this.notificationsError=e.message; }
        finally { this.notificationsLoading=false; }
    },
    toggleNotifications() { this.notificationsOpen=!this.notificationsOpen; if(this.notificationsOpen) this.loadNotifications(); },
    markNotificationsRead(ids=this.notifications.map(n=>n.id)) {
        this.notificationRead=[...new Set([...this.notificationRead,...ids])].slice(-5000);
        localStorage.setItem('zen-notifications:'+this.user.id,JSON.stringify(this.notificationRead));
    },
    async openNotification(item) {
        this.markNotificationsRead([item.id]); this.notificationsOpen=false;
        if(item.entity_type==='meeting') {
            try { const meeting=await this.api('/meetings/'+item.entity_id); this.openModal(meeting,null,false,'meetings'); } catch(e) { this.notify(e.message); }
        } else await this.openDetail(item.entity_type,item.entity_id);
    },
    notificationAction(action) {
        const labels={assigned:'Przypisano do Ciebie',created:'Utworzono',updated:'Zaktualizowano',comment:'Nowy komentarz',commented:'Nowy komentarz',status:'Zmieniono status',status_changed:'Zmieniono status',team:'Zmieniono zespół',call:'Zapisano rozmowę',email:'Zapisano e-mail',converted:'Przekonwertowano na klienta'};
        return this.t(labels[action] || 'Nowa aktywność');
    },
});
