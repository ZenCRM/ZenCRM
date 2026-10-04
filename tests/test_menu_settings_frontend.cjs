const test = require('node:test');
const assert = require('node:assert/strict');
const {createComponent} = require('./helpers/frontend_contract.cjs');

test('menu settings include every sidebar group and child, including later additions', () => {
    const app = createComponent();
    const expected = app.menu.flatMap(item => [item.id,...(item.children || []).map(child => child.id)]);
    assert.deepEqual(Array.from(app.menuModulesList,item=>item.id),Array.from(expected));
    for (const id of ['mail_group','mailboxes','mailSent','mailAccounts','mailSettings','notifications','users','documentTypes','portal_group','portalUsers']) {
        assert.ok(app.menuModulesList.some(item=>item.id===id),id);
    }
    app.menu.push({id:'future_module',label:'Future module'});
    assert.ok(app.menuModulesList.some(item=>item.id==='future_module'));
});

test('disabling a group blocks its child views and preserves child configuration', () => {
    const app = createComponent(); app.user = {role:'employee'};
    app.setMenuModuleEnabled('mail_group',false);
    for (const id of ['mailboxes','mailSent','mailAccounts','mailSettings']) assert.equal(app.canAccessView(id),false);
    assert.ok(!app.visibleMenu.some(item=>item.id==='mail_group'));
    app.setMenuModuleEnabled('mailSent',false);
    app.setMenuModuleEnabled('mail_group',true);
    assert.equal(app.canAccessView('mailboxes'),true);
    assert.equal(app.canAccessView('mailSent'),false);
    assert.deepEqual(Array.from(app.visibleMenu.find(item=>item.id==='mail_group').children,item=>item.id),['mailboxes','mailAccounts','mailSettings']);
});

test('role restrictions on groups apply to child views and notifications can be disabled', () => {
    const app = createComponent(); app.user = {role:'employee'};
    app.setMenuModuleRole('mail_group','manager');
    assert.equal(app.canAccessView('mailboxes'),false);
    app.user = {role:'manager'};
    assert.equal(app.canAccessView('mailboxes'),true);
    app.setMenuModuleEnabled('notifications',false);
    assert.equal(app.canAccessView('notifications'),false);
    assert.ok(!app.visibleMenu.some(item=>item.id==='notifications'));
});

test('administrative pages keep role restrictions and settings cannot lock out the admin', () => {
    const app = createComponent(); app.user = {role:'employee'};
    app.settingsForm.menu_permissions = {users:{role:'all'},documentTypes:{role:'all'},portal_group:{role:'all'}};
    for (const id of ['users','documentTypes','portal_group','portalUsers','settings']) assert.equal(app.canAccessView(id),false);
    assert.equal(app.getMenuModuleConfig('users').role,'admin');
    app.user = {role:'admin'};
    app.setMenuModuleEnabled('settings',false);
    assert.equal(app.canAccessView('settings'),true);
    assert.equal(app.getMenuModuleConfig('settings').enabled,true);
    app.setMenuModuleEnabled('users',false);
    assert.equal(app.canAccessView('users'),false);
});

test('saving menu settings retains unknown entries and writes email and notification choices', async () => {
    const app = createComponent(); app.notify = () => {};
    app.menuPermissionsState = {legacy:{enabled:false,role:'manager'}};
    app.setMenuModuleEnabled('notifications',false);
    app.setMenuModuleRole('mailboxes','manager');
    let saved;
    app.api = async (path, options) => {assert.equal(path,'/settings');saved = JSON.parse(options.body);return {};};
    await app.saveMenuSettings();
    const config = JSON.parse(saved.menu_permissions);
    assert.deepEqual(config.legacy,{enabled:false,role:'manager'});
    assert.equal(config.notifications.enabled,false);
    assert.equal(config.mailboxes.role,'manager');
    assert.equal(app.savingMenuSettings,false);
});
