const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function localeComponent(confirm = () => true) {
    const stored = {}, state = {reloads:0};
    const sandbox = {window:{ZenCustomI18n:{languages:{en:{name:'English'},pl:{name:'Polski'}}},ZenLocales:{pl:{},en:{}}},
        localStorage:{getItem:()=> 'pl',setItem:(key,value)=>{stored[key]=value;}},location:{reload:()=>state.reloads++},confirm};
    vm.runInNewContext(fs.readFileSync('frontend/js/i18n.js','utf8'),sandbox);
    return {app:sandbox.window.ZenModules.locale(),state,stored};
}

test('language switch persists after the select model already changes its value', () => {
    const {app,state,stored} = localeComponent();
    assert.equal(app.locale,'pl');
    app.locale = 'en';
    app.setLocale('en');
    assert.equal(stored['zen-locale'],'en');
    assert.equal(state.reloads,1);
});

test('canceling a language change restores the selected current language', () => {
    const {app,state,stored} = localeComponent(()=>false);
    app.modal={open:true};app.locale='en';app.setLocale('en');
    assert.equal(app.locale,'pl');assert.equal(state.reloads,0);assert.deepEqual(stored,{});
});
