const test = require('node:test');
const assert = require('node:assert/strict');
const {createComponent} = require('./helpers/frontend_contract.cjs');

test('classic sidebar color is independent of page dark mode and modern retains dark sidebar', () => {
    const app = createComponent(); app.darkMode = true;
    app.settingsForm = {ui_template:'classic',ui_classic_sidebar:'light'};
    assert.equal(app.darkSidebar,false);
    app.darkMode = false; app.settingsForm.ui_classic_sidebar = 'dark';
    assert.equal(app.darkSidebar,true);
    app.settingsForm = {ui_template:'modern',ui_classic_sidebar:'light'};
    assert.equal(app.darkSidebar,true);
});

test('saving appearance sends its own settings without invalid defaults from other sections', async () => {
    const app = createComponent(); app.settingsTab = 'appearance';
    app.settingsForm = {ui_template:'classic',ui_classic_sidebar:'dark',client_statuses:'null',smtp_password:''};
    app.applyTheme = () => {};
    let payload; app.api = async (_path,options) => {payload=JSON.parse(options.body);return payload;};
    await app.saveSettings();
    assert.deepEqual(payload,{ui_template:'classic',ui_classic_sidebar:'dark'});
    assert.equal(app.settingsError,'');
});
