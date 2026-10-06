const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const entry={id:'plugin/reports/summary',app_id:'reports',view_id:'summary',placement_id:'main',label:'My report',app_name:'Reports',category:'Raporty',bundled:false};
function setup(){
 const stores={};let init;
 const sandbox={window:{Alpine:{store:(key,value)=>value?(stores[key]=value):stores[key]},ZenI18n:{t:k=>k}},document:{addEventListener:(kind,fn)=>init=fn}};
 vm.runInNewContext(fs.readFileSync('frontend/js/plugins/navigation.js','utf8'),sandbox);init();
 vm.runInNewContext(fs.readFileSync('frontend/js/core/navigation.js','utf8'),sandbox);
 return {nav:sandbox.window.ZenPluginNavigation,state:stores.pluginNavigation,root:sandbox.window.ZenCore.navigation(),sandbox};
}
test('authorized application routes remain separate from core routes and respect menu permissions',async()=>{
 const {nav,state,root}=setup();const ctx={token:'token',api:async p=>p==='/plugins/status'?{enabled:true}:[entry]};
 await nav.load(ctx);Object.assign(root,{menu:[{id:'plugins'}],user:{role:'employee'},settingsForm:{},currentView:entry.id});
 assert.equal(root.isKnownView(entry.id),true);assert.equal(root.isKnownView('plugin/reports/missing'),false);assert.equal(root.canAccessView(entry.id),true);
 root.settingsForm.menu_permissions={plugins:{enabled:false}};assert.equal(root.canAccessView(entry.id),false);
 root.api=()=>assert.fail('Plugin routes must not be forwarded to a core CRUD endpoint');await root.reload();
 nav.clear();assert.equal(state.entries.length,0);assert.equal(root.isKnownView(entry.id),false);
});
test('late response after logout cannot register application views',async()=>{
 const {nav,state}=setup();let resolve;const ctx={token:'token',api:()=>new Promise(r=>resolve=r)};
 const waiting=nav.load(ctx);ctx.token='';nav.clear();resolve({enabled:false});await waiting;
 assert.equal(state.entries.length,0);assert.equal(state.session,'');assert.equal(state.ready,false);
});
test('disabled platform and an unsafe provider route remove menu items',async()=>{
 const {nav,state}=setup();let enabled=true;const ctx={token:'token',api:async p=>p==='/plugins/status'?{enabled}:[entry,{...entry,id:'javascript:alert(1)'},{...entry,id:'plugin/reports/../settings'}]};
 await nav.load(ctx);assert.equal(state.entries.length,1);enabled=false;await nav.load(ctx,true);assert.equal(state.entries.length,0);
});
test('shared bootstrap/menu loading waits on the same request and revalidates on refresh',async()=>{
 const {nav,state}=setup();let resolve,calls=0;const status=new Promise(r=>resolve=r);const ctx={token:'token',api:async p=>{calls++;return p==='/plugins/status'?status:[entry];}};
 const one=nav.load(ctx),two=nav.load(ctx);resolve({enabled:true});await Promise.all([one,two]);assert.equal(calls,2);assert.equal(state.entries.length,1);
 const version=state.version;await nav.load(ctx);assert.equal(calls,2);await nav.load(ctx,true);assert.equal(calls,4);assert.equal(state.version,version,'Unchanged menu must not remount application iframes');
});
test('a named view mounts only its referenced page placement',async()=>{
 const {sandbox,nav}=setup();const ctx={token:'token',api:async p=>p==='/plugins/status'?{enabled:true}:[entry]};await nav.load(ctx);
 vm.runInNewContext(fs.readFileSync('frontend/js/plugins/host.js','utf8'),sandbox);const c=sandbox.window.pluginSlot('menu.view');
 Object.assign(c,{token:'token',currentView:entry.id,detailView:{open:false},canAccessView:()=>true,$nextTick:async()=>{}});
 const app={id:'reports',consented_scopes:['reports.read'],manifest:{type:'declarative',placements:[{id:'main',slot:'app.page',operation:'reports.summary'},{id:'other',slot:'app.page',operation:'tasks.list'}]}};
 const calls=[];c.api=async(path,options)=>{calls.push([path,options]);return path==='/plugins/status'?{enabled:true}:path==='/plugins/apps'?[app]:{clients:1};};
 await c.loadSlots();assert.equal(c.entries.length,1);assert.equal(c.entries[0].placement.id,'main');assert.equal(JSON.parse(calls[2][1].body).operation,'reports.summary');
 nav.clear();assert.equal(c.active(),false);
});
test('native modal waits for its content, closes without retaining secrets, and uses host-owned icons',async()=>{
 const {sandbox}=setup();vm.runInNewContext(fs.readFileSync('frontend/js/plugins/host.js','utf8'),sandbox);
 const c=sandbox.window.pluginHub();let shown=0,closed=0;Object.assign(c,{token:'token',currentView:'plugins',$nextTick:async()=>{},$refs:{pluginDetails:{open:false,showModal(){shown++;},close(){closed++;}}}});
 await c.showDetails({id:'app'});assert.equal(shown,1);c.oneTimeSecret='secret';c.closeDetails();assert.equal(c.storeDetail,null);assert.equal(c.oneTimeSecret,'');assert.equal(closed,1);
 assert.equal(sandbox.window.ZenPluginVisual.icon('<img src=x onerror=alert(1)>').includes('<img'),false);
});
