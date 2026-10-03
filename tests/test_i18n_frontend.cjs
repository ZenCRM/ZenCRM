const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function context() {
    const sandbox = {window:{ZenCustomI18n:{languages:{pl:{name:'Polski',base:'pl'},en:{name:'English',base:'en'}},overrides:{}}}, localStorage:{getItem:()=> 'en'}, document:{documentElement:{}}, console};
    vm.createContext(sandbox);
    for (const file of ['locales/pl.js','locales/en.js','js/i18n.js','js/api.js']) {
        vm.runInContext(fs.readFileSync('frontend/'+file,'utf8'),sandbox);
    }
    return sandbox;
}

test('English messages preserve parameter content and unknown names', () => {
    const {window} = context(), t = window.ZenI18n.t.bind(window.ZenI18n);
    assert.equal(t('Brak powiadomień'), 'No notifications');
    assert.equal(t('constructor'), 'constructor');
    assert.equal(t('Utworzono klienta: {name}', {name:'Łódź {phone}', phone:'123'}), 'Client created: Łódź {phone}');
    assert.equal(t('Własna nazwa klienta'), 'Własna nazwa klienta');
});

test('default stage labels translate without changing custom names or edit values', () => {
    const {window} = context();
    const raw = {id:'todo',label:'Do zrobienia'};
    assert.equal(window.ZenI18n.taskStage(raw).label,'To do');
    assert.equal(raw.label,'Do zrobienia');
    assert.equal(window.ZenI18n.taskStage({id:'todo',label:'Moja kolejka'}).label,'Moja kolejka');
    assert.equal(window.ZenI18n.taskStage({id:'custom',label:'Do zrobienia'}).label,'Do zrobienia');
});

test('API requests, login and password reset send the selected language', async () => {
    const sandbox = context(), calls=[];
    sandbox.fetch = async (url, options) => {calls.push(options); return {status:200,ok:true,headers:{get:()=> 'application/json'},json:async()=>({})};};
    await sandbox.window.ZenApi.request('/clients');
    await sandbox.window.ZenApi.login('test@example.com','test');
    await sandbox.window.ZenApi.forgotPassword('test@example.com');
    assert.equal(calls.length,3);
    for (const call of calls) assert.equal(call.headers['Accept-Language'],'en');
});

test('push uses the bound user language and keeps reminder content untouched', async () => {
    const handlers={}, notifications=[];
    const sandbox={self:{addEventListener:(event,handler)=>{handlers[event]=handler;},
        registration:{showNotification:async(title,options)=>notifications.push({title,options})}},
        URL, encodeURIComponent};
    vm.createContext(sandbox);
    sandbox.importScripts=(...files)=>files.forEach(file=>vm.runInContext(fs.readFileSync('frontend'+file,'utf8'),sandbox));
    vm.runInContext(fs.readFileSync('frontend/sw.js','utf8'),sandbox);
    vm.runInContext("binding = async () => ({userId:7,locale:'en'})",sandbox);
    let pending;
    handlers.push({data:{json:()=>({user_id:7,reminder_id:3,title:'Przypomnienie ZenCRM',body:'Zadzwoń do Łodzi'})},waitUntil:promise=>{pending=promise;}});
    await pending;
    assert.equal(notifications[0].title,'ZenCRM reminder');
    assert.equal(notifications[0].options.body,'Zadzwoń do Łodzi');
    handlers.push({data:{json:()=>({user_id:8,reminder_id:4,body:'Private'})},waitUntil:promise=>{pending=promise;}});
    await pending;
    assert.equal(notifications.length,1);
});

test('standalone portal renderer translates only explicitly marked system copy', () => {
    const sandbox=context();
    const system={dataset:{i18n:'Brak powiadomień'},textContent:'Brak powiadomień'};
    const custom={textContent:'Brak powiadomień'};
    const placeholder={getAttribute:()=> 'Nazwa klienta',setAttribute:(name,value)=>{placeholder[name]=value;}};
    sandbox.document.querySelectorAll=selector=>selector==='[data-i18n]'?[system]:selector==='[data-i18n-placeholder]'?[placeholder]:[];
    sandbox.document.querySelector=()=>null;
    sandbox.location={search:'?embed=1'};
    sandbox.URLSearchParams=URLSearchParams;
    vm.runInContext(fs.readFileSync('frontend/js/i18n-dom.js','utf8'),sandbox);
    assert.equal(system.textContent,'No notifications');
    assert.equal(custom.textContent,'Brak powiadomień');
    assert.equal(placeholder.placeholder,'Client name');
});
