/* No cached CRM pages or credentials; this worker only handles Web Push. */
const window = self;
importScripts('/locales/pl.js', '/locales/en.js');
const bindingDb = () => new Promise((resolve, reject) => {
    const req = indexedDB.open('zencrm-push', 1);
    req.onupgradeneeded = () => req.result.createObjectStore('binding');
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
});
async function binding(value) {
    const db = await bindingDb();
    return new Promise((resolve, reject) => {
        const tx = db.transaction('binding', value === undefined ? 'readonly' : 'readwrite');
        const store = tx.objectStore('binding');
        const req = value === undefined ? store.get('user') : store.put(value, 'user');
        tx.oncomplete = () => { db.close(); resolve(req.result); };
        tx.onerror = () => { db.close(); reject(tx.error); };
    });
}
self.addEventListener('install', event => event.waitUntil(self.skipWaiting()));
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('message', event => {
    if (event.data?.type === 'PUSH_BIND') event.waitUntil(binding({userId: event.data.userId, locale: event.data.locale === 'en' ? 'en' : 'pl'}).then(() => event.ports[0]?.postMessage({ok:true})));
});
self.addEventListener('push', event => {
    event.waitUntil((async () => {
        if (!event.data) return;
        const data = event.data.json();
        const user = await binding();
        if (Number(user?.userId ?? user) !== Number(data.user_id)) return;
        const key = data.title || 'Przypomnienie ZenCRM';
        const title = self.ZenLocales[user?.locale || 'pl']?.[key] || key;
        await self.registration.showNotification(title, {
            body: data.body, icon:'/icon.png', badge:'/icon.png', tag:data.tag,
            requireInteraction:true, data:{url:'/?reminder='+encodeURIComponent(data.reminder_id)},
        });
    })());
});
self.addEventListener('notificationclick', event => {
    event.notification.close();
    event.waitUntil((async () => {
        const clients = await self.clients.matchAll({type:'window', includeUncontrolled:true});
        for (const client of clients) {
            if (new URL(client.url).origin === self.location.origin && !/\/(portal|helpdesk|workspace)/.test(new URL(client.url).pathname)) {
                client.postMessage({type:'REMINDER_PUSH_OPEN'});
                await client.focus(); return;
            }
        }
        await self.clients.openWindow(event.notification.data?.url || '/');
    })());
});
