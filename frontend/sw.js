/* No cached CRM pages or credentials; this worker only handles Web Push. */
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
    if (event.data?.type === 'PUSH_BIND') event.waitUntil(binding(event.data.userId).then(() => event.ports[0]?.postMessage({ok:true})));
});
self.addEventListener('push', event => {
    event.waitUntil((async () => {
        if (!event.data) return;
        const data = event.data.json();
        if (Number(await binding()) !== Number(data.user_id)) return;
        await self.registration.showNotification(data.title || 'Przypomnienie ZenCRM', {
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
