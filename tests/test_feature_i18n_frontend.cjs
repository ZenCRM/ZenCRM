const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function feature(locale) {
    const sandbox = {window:{ZenCustomI18n:{languages:{pl:{},en:{}}}},localStorage:{getItem:()=>locale},
        document:{documentElement:{},getElementById:()=>null},setTimeout,clearTimeout,console};
    vm.createContext(sandbox);
    for (const path of ['locales/pl.js','locales/en.js','js/i18n.js','js/modules/mailboxes.js',
        'js/modules/template-studio.js','js/modules/documents.js']) {
        vm.runInContext(fs.readFileSync('frontend/'+path,'utf8'),sandbox);
    }
    const app = {locale};
    for (const name of ['mailboxes','templateStudio','documents']) {
        Object.defineProperties(app,Object.getOwnPropertyDescriptors(sandbox.window.ZenModules[name]()));
    }
    return {app,window:sandbox.window};
}

test('English mailbox headings, composer modes and recipient validation use the selected language', () => {
    const {app} = feature('en');
    app.currentView='mailboxes'; assert.equal(app.mailPageTitle,'Inbox');
    app.currentView='mailSettings'; assert.equal(app.mailPageTitle,'Email settings');
    app.composeMail('replyAll'); assert.equal(app.mailComposeTitle,'Reply all');
    app.addMailRecipients('cc','niepoprawny');
    assert.equal(app.mail.recipientErrors.cc,'Check the address: niepoprawny');
});

test('sync messages interpolate counts and keep user input intact in both languages', async () => {
    for (const locale of ['pl','en']) {
        const {app,window} = feature(locale);
        app.mail.boxId=1; app.mail.boxes=[{id:1}]; app.token='session';
        app.api=async()=>({mailbox:{id:1},processed:10,imported:3,total:10,next_before_uid:null});
        app.loadMailMessages=async()=>{};
        let message; app.notify=value=>{message=value;};
        await app.syncMailbox();
        assert.equal(message,locale==='en'?'Downloaded 3 new messages':'Pobrano 3 nowych wiadomości');
        assert.equal(window.ZenI18n.t('Usuń odbiorcę ')+ 'Łódź@test.com',
            (locale==='en'?'Remove recipient ':'Usuń odbiorcę ')+'Łódź@test.com');
    }
});

test('English starter layouts and inserted blocks preserve template placeholders and escape custom translations', () => {
    const {app,window} = feature('en');
    for (const kind of ['business','letter','agreement']) {
        const html=app.starterTemplate(kind);
        assert.ok(html.includes('Prepared for'));
        assert.ok(html.includes('{{ client.name }}'));
        assert.ok(html.includes('{{ company.name }}'));
        assert.doesNotMatch(html,/Przygotowano|Szanowni|Podpis|Warunki|Zakres/);
    }
    assert.ok(app.templateVariables().some(row=>row.label==='Client email'));
    app.templateStudio.mode='source'; let inserted;
    app.insertTemplateText=value=>{inserted=value;}; app.insertStudioBlock('table');
    assert.ok(inserted.includes('Description')); assert.ok(inserted.includes('Value'));
    window.ZenCustomI18n.overrides={en:{'Nowa sekcja':'<img src=x onerror=alert(1)>'}};
    app.insertStudioBlock('heading');
    assert.ok(inserted.includes('&lt;img')); assert.ok(!inserted.includes('<img'));
});

test('opening saved documents preserves author content and Polish starter defaults remain Polish', () => {
    for (const locale of ['pl','en']) {
        const {app} = feature(locale);
        app.templateModal={form:{},open:false}; app.documentTypes=[{key:'contract'}];
        app.$nextTick=()=>{}; app.mountVisualTemplate=()=>{};
        const content='<h1>Moja własna umowa</h1><p>{{ client.name }}</p>';
        app.openTemplateModal({id:7,name:'Moja umowa',type:'document',content});
        assert.equal(app.templateModal.form.content,content);
        assert.equal(app.templateModal.form.name,'Moja umowa');
        assert.ok(app.starterTemplate().includes(locale==='pl'?'Przygotowano dla':'Prepared for'));
    }
});
