const test=require('node:test'), assert=require('node:assert/strict'), vm=require('node:vm'), fs=require('node:fs');
function component() {
    const sandbox={window:{ZenI18n:{t:key=>key}}};
    vm.runInNewContext(fs.readFileSync('frontend/js/plugins/options.js','utf8'),sandbox);
    const value=sandbox.window.pluginOptions();
    Object.assign(value,{token:'session',user:{role:'admin'},currentView:'settings',settingsTab:'plugins',$dispatch(){}});
    return value;
}
test('options load and save use their own endpoint and boolean state',async()=>{
    const c=component(),calls=[];
    c.api=async(path,opts)=>{calls.push([path,opts]);return {configured_enabled:opts?JSON.parse(opts.body).enabled:false,server_locked:false};};
    await c.loadOptions();assert.equal(c.optionReady,true);assert.equal(c.optionEnabled,false);
    c.optionEnabled=true;await c.saveOptions();assert.equal(c.optionSaved,'Ustawienia zapisane');
    assert.equal(calls[1][0],'/plugins/settings');assert.deepEqual(JSON.parse(calls[1][1].body),{enabled:true});
});
test('server veto prevents enabling through the options component',async()=>{
    const c=component();c.optionReady=true;c.optionLocked=true;c.api=()=>assert.fail('Must not save a locked platform');
    await c.saveOptions();assert.equal(c.optionBusy,false);
});
test('late options response after logout cannot repopulate the component',async()=>{
    const c=component();let resolve;c.api=()=>new Promise(r=>resolve=r);
    const waiting=c.loadOptions();c.token='';resolve({configured_enabled:true,server_locked:false});await waiting;
    assert.equal(c.optionReady,false);assert.equal(c.optionEnabled,false);
});
