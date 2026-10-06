const test=require('node:test'), assert=require('node:assert/strict'), vm=require('node:vm'), fs=require('node:fs');
function component() {
    const sandbox={window:{ZenI18n:{t:key=>key}}};
    vm.runInNewContext(fs.readFileSync('frontend/js/plugins/drive.js','utf8'),sandbox);
    const c=sandbox.window.pluginDriveSettings();
    Object.assign(c,{token:'session',user:{role:'admin'},currentView:'plugins',hubTab:'manage',selected:{id:'zencrm-google-drive'}});
    return c;
}
test('saved secrets are never loaded and an empty replacement keeps the server secret',async()=>{
    const c=component(); let sent;
    c.api=async(path,opts)=>{assert.equal(path,'/plugins/google-drive/settings');if(opts) sent=JSON.parse(opts.body);return {client_id:'panel.apps.googleusercontent.com',secret_set:true,revision:'revision',encryption_ready:true};};
    await c.loadDriveSettings();assert.equal(c.driveClientSecret,'');
    await c.saveDriveSettings();assert.equal(sent.client_secret,'');assert.equal(sent.revision,'revision');
});
test('secret input is cleared before request settles, including errors',async()=>{
    const c=component(); c.driveConfig={revision:'revision'};c.driveClientSecret='sensitive'; let reject, sent;
    c.api=(path,opts)=>{sent=JSON.parse(opts.body);return new Promise((resolve,r)=>reject=r);};
    const request=c.saveDriveSettings();assert.equal(c.driveClientSecret,'');assert.equal(sent.client_secret,'sensitive');
    reject(Error('failure'));await request;assert.equal(c.driveClientSecret,'');assert.equal(c.settingsError,'failure');
});
test('late settings response after logout cannot restore admin configuration',async()=>{
    const c=component();let resolve;c.api=()=>new Promise(r=>resolve=r);
    const request=c.loadDriveSettings();c.token='';c.clearSettings();resolve({client_id:'private',revision:'revision'});
    await request;assert.equal(c.driveConfig,null);assert.equal(c.driveClientId,'');
});
test('moving to a different plugin blocks settings saves',async()=>{
    const c=component();c.driveConfig={revision:'revision'};c.selected={id:'another-plugin'};
    c.api=()=>assert.fail('Wrong plugin must not save Drive credentials');await c.saveDriveSettings();
});
