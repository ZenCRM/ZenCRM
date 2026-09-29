window.ZenModules = window.ZenModules || {};
window.ZenModules.notifications = () => ({
    notifications: [], notificationRead: [], notificationsOpen: false,
    notificationsLoading: false, notificationsError: '', notificationTimer: null,
    notificationFilter: 'all', notificationSearch: '',
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
    markNotificationUnread(id) {
        this.notificationRead = this.notificationRead.filter(item => item !== id);
        localStorage.setItem('zen-notifications:'+this.user.id, JSON.stringify(this.notificationRead));
    },
    toggleNotificationRead(item) {
        if (this.notificationRead.includes(item.id)) {
            this.markNotificationUnread(item.id);
        } else {
            this.markNotificationsRead([item.id]);
        }
    },
    async openNotification(item) {
        this.markNotificationsRead([item.id]); this.notificationsOpen=false;
        if(item.entity_type==='meeting') {
            try { const meeting=await this.api('/meetings/'+item.entity_id); this.openModal(meeting,null,false,'meetings'); } catch(e) { this.notify(e.message); }
        } else await this.openDetail(item.entity_type,item.entity_id);
    },
    notificationAction(action) {
        const labels={assigned:window.ZenI18n.t('Przypisano do Ciebie'),created:window.ZenI18n.t('Utworzono'),updated:window.ZenI18n.t('Zaktualizowano'),comment:window.ZenI18n.t('Nowy komentarz'),commented:window.ZenI18n.t('Nowy komentarz'),status:window.ZenI18n.t('Zmieniono status'),status_changed:window.ZenI18n.t('Zmieniono status'),team:window.ZenI18n.t('Zmieniono zespół'),call:window.ZenI18n.t('Zapisano rozmowę'),email:window.ZenI18n.t('Zapisano e-mail'),converted:window.ZenI18n.t('Przekonwertowano na klienta')};
        return this.t(labels[action] || window.ZenI18n.t('Nowa aktywność'));
    },
    entityLabel(entityType) {
        const labels = {
            client: window.ZenI18n.t('Klient'),
            lead: window.ZenI18n.t('Lead'),
            task: window.ZenI18n.t('Zadanie'),
            service: window.ZenI18n.t('Usługa'),
            meeting: window.ZenI18n.t('Spotkanie'),
            project: window.ZenI18n.t('Projekt'),
            reminder: window.ZenI18n.t('Przypomnienie')
        };
        return this.t(labels[entityType] || entityType || window.ZenI18n.t('Element'));
    },
});
