const test=require('node:test'), assert=require('node:assert/strict'), vm=require('node:vm'), fs=require('node:fs');
function component() {
    const sandbox={window:{ZenI18n:{t:key=>key}},URLSearchParams,location:{search:''}};
    vm.runInNewContext(fs.readFileSync('frontend/js/plugins/host.js','utf8'),sandbox);
    const c=sandbox.window.pluginHub();
    Object.assign(c,{token:'session',user:{id:1,role:'employee'},currentView:'plugins',$dispatch(){}});
    return c;
}
const app=(id,consent=[])=>({id,bundled:true,manifest:{name:'App '+id,description:'Local tool',scopes:['reports.read']},approved_scopes:['reports.read'],consented_scopes:consent,category:'Raporty',available:true});
test('store search/category and My apps distinguish availability from consent',()=>{
    const c=component(); c.storeApps=[app('one'),{...app('two'),category:'Sales'}]; c.hubApps=[app('one'),app('two',['reports.read'])];
    assert.equal(c.ownedApps().length,1); c.storeQuery=' ONE '; assert.equal(c.filteredStore().length,1);
    c.storeCategory='Sales'; assert.equal(c.filteredStore().length,0); c.storeQuery=''; assert.equal(c.filteredStore().length,1);
    c.openApp(c.hubApps[1]); assert.equal(c.hubTab,'mine'); assert.equal(c.workspaceApp,'two');
});
test('out-of-order hub response cannot replace the latest store state',async()=>{
    const c=component(); const status=[]; c.api=path=>path==='/plugins/status'?new Promise(r=>status.push(r)):Promise.resolve([app('fresh')]);
    const first=c.loadHub(),second=c.loadHub(); status[1]({enabled:true}); await second;
    status[0]({enabled:false}); await first; assert.equal(c.enabled,true); assert.equal(c.storeApps[0].id,'fresh');
});
test('logout while catalog loads prevents data and secret repopulation',async()=>{
    const c=component(); let resolve;const catalog=new Promise(r=>resolve=r);c.api=path=>path==='/plugins/status'?Promise.resolve({enabled:true}):catalog;
    const pending=c.loadHub(); await new Promise(r=>setImmediate(r));c.token='';resolve([]);await pending;
    assert.equal(c.storeApps.length,0); assert.equal(c.hubApps.length,0);
    c.token='session'; c.api=()=>new Promise(r=>resolve=r); const secret=c.showSecret(app('one')); c.token=''; resolve({access_token:'secret'}); await secret; assert.equal(c.oneTimeSecret,'');
});
test('administrator all-users audience is sent explicitly only when selected',async()=>{
    const c=component();c.user.role='admin'; c.selected={...app('one'),revision:1};c.selectedScopes=['reports.read'];c.selectedUsers=[1];c.allUsers=true;c.configurationText='{}';let payload;
    c.loadHub=async()=>{};c.api=async(path,options)=>{payload=JSON.parse(options.body);return {...c.selected,all_users:true,allowed_users:['all-active-users']};};
    await c.installApp();assert.deepEqual(payload.allowed_users,[]);assert.equal(payload.all_users,true);assert.equal(c.selectedUsers.length,0);
});
test('declarative application page loads only the selected consented application',async()=>{
    const sandbox={window:{ZenI18n:{t:key=>key}}};vm.runInNewContext(fs.readFileSync('frontend/js/plugins/host.js','utf8'),sandbox);
    const c=sandbox.window.pluginSlot('app.page');const apps=['one','two'].map(id=>({...app(id,['reports.read']),manifest:{type:'declarative',placements:[{id:'main',slot:'app.page',operation:'reports.summary'}]}}));
    Object.assign(c,{token:'session',currentView:'plugins',hubTab:'mine',workspaceApp:'two',detailView:{open:false},$nextTick:async()=>{}});
    const calls=[];c.api=async path=>{calls.push(path);return path==='/plugins/status'?{enabled:true}:path==='/plugins/apps'?apps:{clients:1};};
    await c.loadSlots(); assert.equal(c.entries.length,1);assert.equal(c.entries[0].app.id,'two'); assert.equal(calls.includes('/plugins/apps/one/invoke'),false);
    c.hubTab='store'; assert.equal(c.active(),false);
});
