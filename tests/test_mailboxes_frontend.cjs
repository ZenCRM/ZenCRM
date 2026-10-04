const test = require('node:test');
const assert = require('node:assert/strict');
const {createComponent} = require('./helpers/frontend_contract.cjs');

test('successful sending navigates to the sent page', async () => {
    const app = createComponent(); app.token = 'session'; app.mail.boxId = 1;
    app.mail.composing = true; app.mail.compose = {to:'client@test.com',cc:'',bcc:'',subject:'Offer',body:'Hello',include_signature:false};
    app.api = async () => ({refused:[]}); app.notify = () => {};
    let view; app.selectView = async id => {view = id;};
    await app.sendMail();
    assert.equal(view,'mailSent');
    assert.equal(app.mail.composing,false);
});

test('periodic inbox refresh preserves opened mail and HTML is enabled by default', async () => {
    const app = createComponent(); app.token = 'session'; app.mail.boxId = 1;
    assert.equal(app.mail.htmlView,true);
    const selected = {id:11,body_html:'<table style="background:#14213d"></table>'};
    app.mail.selected = selected;
    app.api = async path => path === '/mailboxes/unread' ? {total:2} : {items:[{id:12}],total:1,pages:1,unread:2};
    await app.loadMailMessages(true);
    assert.equal(app.mail.selected,selected);
    assert.equal(app.mail.items[0].id,12);
    assert.ok(app.mailHTMLDocument(selected.body_html).includes('background:#14213d'));
});

test('unread badge ignores responses from a previous session and older request', async () => {
    const app = createComponent(); app.token = 'first'; let first;
    app.api = () => new Promise(resolve => { first = resolve; });
    const pending = app.loadUnreadMailCount();
    app.token = 'second'; app.api = async () => ({total:3});
    await app.loadUnreadMailCount(); first({total:99}); await pending;
    assert.equal(app.unreadMailCount,3);
    app.token = ''; await app.loadUnreadMailCount();
    assert.equal(app.unreadMailCount,0);
});

test('CRM email preference opens composer with recipient and preserves chosen mailbox', async () => {
    const app = createComponent(); app.user = {default_email_method:'crm'};
    app.mail.boxes = [{id:2,email:'office@test.com'}]; app.mail.boxId = 2;
    app.selectView = async id => { app.currentView = id; };
    await app.writeEmail('Client@Test.com');
    assert.equal(app.currentView,'mailboxes');
    assert.equal(app.mail.composing,true);
    assert.equal(app.mail.compose.to,'client@test.com');
    assert.equal(app.mail.boxId,2);
});

test('CRM preference without mailbox opens connection and remembers recipient', async () => {
    const app = createComponent(); app.user = {default_email_method:'crm'};
    app.selectView = async () => {};
    await app.writeEmail('client@test.com');
    assert.equal(app.mail.connecting,true);
    assert.equal(app.mail.pendingRecipient,'client@test.com');
    assert.equal(app.mail.composing,false);
});

test('client email history ignores responses from a previous client', async () => {
    const app = createComponent(); let resolveFirst;
    app.api = () => new Promise(resolve => { resolveFirst = resolve; });
    const first = app.loadClientMail(1);
    app.api = async () => ({items:[{id:22}],total:1,pages:1,emails:['second@test.com']});
    await app.loadClientMail(2);
    resolveFirst({items:[{id:11}],total:1,pages:1,emails:['first@test.com']});
    await first;
    assert.equal(app.clientMail.items[0].id,22);
    assert.equal(app.clientMail.clientId,2);
});

test('opening mail from client history initializes CRM links before fetching detail', async () => {
    const app = createComponent(); app.mail.boxId = 1;
    let resolve;
    app.api = () => new Promise(done => { resolve = done; });
    const pending = app.selectMailMessage({id:9,folder:'sent',is_read:true});
    assert.equal(app.mail.selected.links.clients.length,0);
    resolve({id:9,folder:'sent',is_read:true,links:{clients:[],contacts:[]}});
    await pending;
});

test('recipient chips accept pasted lists and display names, remove duplicates and keep invalid input', () => {
    const app = createComponent(); app.composeMail();
    assert.equal(app.addMailRecipients('cc','Anna <Anna@test.com>; other@test.com\nANNA@test.com'),true);
    assert.equal(app.mail.compose.cc,'anna@test.com, other@test.com');
    assert.equal(app.addMailRecipients('bcc','invalid; hidden@test.com'),false);
    assert.equal(app.mail.compose.bcc,'hidden@test.com');
    assert.equal(app.mail.recipientInputs.bcc,'invalid');
    assert.match(app.mail.recipientErrors.bcc,/invalid/);
    app.removeMailRecipient('cc','anna@test.com');
    assert.equal(app.mail.compose.cc,'other@test.com');
});

test('recipient keyboard supports Enter and Backspace without submitting the form', () => {
    const app = createComponent(); app.composeMail();
    app.mail.recipientInputs.to = 'client@test.com';
    let prevented = false;
    app.mailRecipientKey({key:'Enter',preventDefault(){prevented=true;}},'to');
    assert.equal(prevented,true); assert.equal(app.mail.compose.to,'client@test.com');
    app.mailRecipientKey({key:'Backspace'},'to');
    assert.equal(app.mail.compose.to,'');
});

test('recipient suggestions filter CRM contacts and omit already added recipients', () => {
    const app = createComponent(); app.composeMail();
    app.contacts = [{first_name:'Anna',last_name:'Nowak',email:'anna@test.com'}, {name:'Other',email:'other@test.com'}];
    app.clients = [{name:'Anna',email:'anna@test.com'}];
    app.mail.recipientInputs.to = 'anna';
    assert.equal(app.mailRecipientSuggestions('to').length,1);
    app.addMailRecipients('to','anna@test.com'); app.mail.recipientInputs.cc = 'anna';
    assert.equal(app.mailRecipientSuggestions('cc').length,0);
});

test('send commits unfinished recipient input and blocks invalid addresses', async () => {
    const app = createComponent(); app.composeMail();
    app.mail.boxId = 1; app.mail.compose.subject = 'Offer'; app.mail.compose.body = 'Hello';
    app.mail.recipientInputs.to = 'client@test.com'; app.mail.recipientInputs.bcc = 'invalid';
    let sent;
    app.api = async (url, options) => { sent = JSON.parse(options.body); return {refused:[]}; };
    app.notify = () => {}; app.loadMailMessages = async () => {};
    await app.sendMail(); assert.equal(sent,undefined);
    app.mail.recipientInputs.bcc = 'hidden@test.com';
    await app.sendMail(); assert.equal(sent.to,'client@test.com'); assert.equal(sent.bcc,'hidden@test.com');
});

test('mail search ignores stale responses after changing mailbox', async () => {
    const app = createComponent();
    app.mail.boxId = 1;
    let first;
    app.api = () => new Promise(resolve => { first = resolve; });
    const pending = app.loadMailMessages();
    app.mail.boxId = 2;
    app.api = async () => ({items:[{id:22}],total:1,pages:1});
    await app.loadMailMessages();
    first({items:[{id:11}],total:1,pages:1});
    await pending;
    assert.equal(app.mail.items[0].id,22);
});

test('reply uses the sender and adds a single Re prefix', () => {
    const app = createComponent();
    app.mail.selected = {sender:'client@test.com',subject:'Re: Offer'};
    app.composeMail(true);
    assert.equal(app.mail.compose.to,'client@test.com');
    assert.equal(app.mail.compose.subject,'Re: Offer');
    assert.equal(app.mail.compose.include_signature,true);
});

test('template copy does not mutate original custom fields', async () => {
    const app = createComponent();
    app.$nextTick = () => {};
    app.api = async () => [];
    const original = {id:5,name:'Original',type:'document',content:'{% if client %}{{ client.name }}{% endif %}',variables:[{name:'term',label:'Term'}]};
    await app.duplicateTemplate(original);
    assert.equal(app.templateModal.editingId,null);
    assert.equal(app.templateStudio.mode,'source');
    app.templateModal.form.variables[0].label = 'Changed';
    assert.equal(original.variables[0].label,'Term');
});

test('blank template never submits a save request', async () => {
    const app = createComponent();
    app.templateModal.form.name = '  ';
    let requests = 0;
    app.api = async () => { requests++; };
    await app.saveTemplate();
    assert.equal(requests,0);
    assert.ok(app.templateModal.error);
});

test('forward keeps original message id but starts with empty recipient fields', () => {
    const app = createComponent();
    app.mail.selected = {id:12,sender:'sender@test.com',subject:'Offer'};
    app.composeMail('forward');
    assert.equal(app.mail.compose.forward_message_id,12);
    assert.equal(app.mail.compose.reply_to_id,null);
    assert.equal(app.mail.compose.to,'');
    assert.equal(app.mail.compose.cc,'');
    assert.equal(app.mail.compose.bcc,'');
    assert.equal(app.mail.compose.subject,'Fwd: Offer');
});

test('reply all removes own address and duplicates, preserves CC and never copies BCC', () => {
    const app = createComponent();
    app.mail.boxId = 1;
    app.mail.boxes = [{id:1,email:'office@test.com'}];
    app.mail.selected = {id:8,sender:'Client@Test.com',recipients:['office@test.com','partner@test.com','CLIENT@test.com'],cc:['Office@Test.com','partner@test.com','other@test.com','OTHER@test.com'],bcc:['hidden@test.com'],subject:'Offer'};
    app.composeMail('replyAll');
    assert.equal(app.mail.compose.to,'client@test.com, partner@test.com');
    assert.equal(app.mail.compose.cc,'other@test.com');
    assert.equal(app.mail.compose.bcc,'');
    assert.equal(app.mail.compose.reply_to_id,8);
    assert.equal(app.mailComposeTitle,'Odpowiedz wszystkim');
});

test('sent messages can be answered to the original recipients', () => {
    const app = createComponent();
    app.mail.boxId = 1;
    app.mail.boxes = [{id:1,email:'office@test.com'}];
    app.mail.selected = {id:9,folder:'sent',sender:'Office@Test.com',recipients:['client@test.com'],cc:['partner@test.com'],subject:'Re: Offer'};
    app.composeMail('reply');
    assert.equal(app.mail.compose.to,'client@test.com');
    app.composeMail('replyAll');
    assert.equal(app.mail.compose.to,'client@test.com');
    assert.equal(app.mail.compose.cc,'partner@test.com');
    assert.equal(app.mail.compose.subject,'Re: Offer');
});

test('mail menu separates inbox, sent, accounts and settings; account pages load no messages', async () => {
    const app = createComponent();
    const group = app.menu.find(item => item.id === 'mail_group');
    assert.deepEqual(Array.from(group.children, item => item.id),['mailboxes','mailSent','mailAccounts','mailSettings']);
    assert.deepEqual(Array.from(group.children, item => item.label),['Odebrane','Wysłane','Skrzynki','Ustawienia']);
    app.currentView = 'mailSettings';
    app.api = async path => path === '/teams' ? [] : [{id:1,signature:'Best regards',signature_format:'text'}];
    app.loadMailMessages = async () => assert.fail('Settings must not request inbox');
    await app.loadMailboxes();
    assert.equal(app.mail.signature,'Best regards');
    assert.equal(app.mail.boxId,1);
    app.mail.boxes.push({id:2,signature:'Other mailbox',signature_format:'html'});
    app.mail.boxId = 2;
    app.editMailboxSettings();
    assert.equal(app.mail.signature,'Other mailbox');
    assert.equal(app.mail.signatureFormat,'html');
    app.currentView = 'mailAccounts';
    await app.loadMailboxes();
    assert.equal(app.mail.items.length,0);
});

test('full synchronization follows every server cursor and keeps cumulative progress', async () => {
    const app = createComponent();
    app.mail.boxId = 1;
    app.token = 'test';
    app.mail.boxes = [{id:1}];
    const cursors = [];
    app.api = async (path, options) => {
        const data = JSON.parse(options.body);
        cursors.push(data.before_uid);
        return {mailbox:{id:1},processed:50,imported:10,total:150,next_before_uid:cursors.length === 1 ? 101 : cursors.length === 2 ? 51 : null};
    };
    app.loadMailMessages = async () => {};
    app.notify = () => {};
    await app.syncMailbox(true);
    assert.deepEqual(cursors,[null,101,51]);
    assert.equal(app.mail.syncProgress.processed,150);
    assert.equal(app.mail.syncProgress.imported,30);
    assert.equal(app.mail.busy,false);
});

test('canceling a full synchronization finishes current batch and does not request the next', async () => {
    const app = createComponent();
    app.mail.boxId = 1;
    let calls = 0;
    app.api = async () => { calls++; app.mail.cancelSync = true; return {mailbox:{id:1},processed:50,imported:5,total:100,next_before_uid:51}; };
    app.loadMailMessages = async () => {};
    app.notify = () => {};
    await app.syncMailbox(true);
    assert.equal(calls,1);
    assert.equal(app.mail.syncProgress.imported,5);
    assert.equal(app.mail.syncingAll,false);
});
