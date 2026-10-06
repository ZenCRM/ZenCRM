const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');

function harness(file) {
    const listeners = new Set(), messages = [];
    const window = {ZenI18n:{t:key=>key}, addEventListener:(type,fn)=>listeners.add(fn),removeEventListener:(type,fn)=>listeners.delete(fn),
        parent:{postMessage:(value,origin)=>messages.push({value,origin})}};
    const context={window, URL, URLSearchParams, console, crypto, setTimeout,clearTimeout, location:{origin:'https://crm.example.com'}};
    vm.runInNewContext(fs.readFileSync(file,'utf8'),context);
    return {window,listeners,messages,async emit(event) { for (const fn of [...listeners]) await fn(event); }};
}

test('bridge validates source, exact origin, channel and session; never sends credentials',async () => {
    const h=harness('frontend/js/plugins/host.js'); let active=true, calls=0, onLoad;
    const sent=[], frame={contentWindow:{postMessage:(data,origin)=>sent.push({data,origin})},style:{},
        addEventListener:(type,fn)=>onLoad=fn, removeEventListener(){},remove(){this.removed=true;}};
    const bridge=h.window.ZenPluginBridge.create(frame,'https://apps.example.com',{app_id:'test',entity_id:1},async()=>{calls++;return {id:1};},()=>active);
    onLoad(); const channel=sent[0].data.channel;
    const data={type:'zen:request',channel,id:'1',method:'call',operation:'clients.get',params:{id:1}};
    await h.emit({source:{},origin:'https://apps.example.com',data});
    await h.emit({source:frame.contentWindow,origin:'https://evil.example.com',data});
    await h.emit({source:frame.contentWindow,origin:'https://apps.example.com',data:{...data,channel:'wrong'}});
    assert.equal(calls,0);
    await h.emit({source:frame.contentWindow,origin:'https://apps.example.com',data});
    assert.equal(calls,1);assert.equal(sent[1].origin,'https://apps.example.com');
    assert.equal(JSON.stringify(sent).includes('token'),false);
    await h.emit({source:frame.contentWindow,origin:'https://apps.example.com',data}); assert.equal(calls,1);
    active=false;
    await h.emit({source:frame.contentWindow,origin:'https://apps.example.com',data:{...data,id:'2'}});assert.equal(calls,1);
    bridge.close(); assert.equal(h.listeners.size,0);assert.equal(frame.removed,true);
});

test('logout during an in-flight call prevents the response reaching the old app',async()=>{
    const h=harness('frontend/js/plugins/host.js'); let active=true, resolve, onLoad;
    const sent=[],frame={contentWindow:{postMessage:data=>sent.push(data)},style:{},addEventListener:(type,fn)=>onLoad=fn,removeEventListener(){},remove(){}};
    const port=h.window.ZenPluginBridge.create(frame,'https://apps.example.com',{},()=>new Promise(r=>resolve=r),()=>active);
    onLoad();const request=h.emit({source:frame.contentWindow,origin:'https://apps.example.com',data:{type:'zen:request',channel:sent[0].channel,id:'1',method:'call',operation:'clients.list'}});
    active=false;resolve({private:'result'});await request;assert.equal(sent.length,1);port.close();
});

test('resize is bounded and arbitrary host methods are rejected',async()=>{
    const h=harness('frontend/js/plugins/host.js');let onLoad;
    const sent=[],frame={contentWindow:{postMessage:data=>sent.push(data)},style:{},addEventListener:(type,fn)=>onLoad=fn,removeEventListener(){},remove(){}};
    const port=h.window.ZenPluginBridge.create(frame,'https://apps.example.com',{},()=>assert.fail(),()=>true);onLoad();
    const message={type:'zen:request',channel:sent[0].channel,id:'1',method:'resize',params:{height:10000}};
    await h.emit({source:frame.contentWindow,origin:'https://apps.example.com',data:message});assert.equal(frame.style.height,'800px');
    await h.emit({source:frame.contentWindow,origin:'https://apps.example.com',data:{...message,id:'2',method:'eval'}});assert.ok(sent.at(-1).error);port.close();
});

test('SDK only accepts the configured CRM parent, correlates replies and cancels requests',async()=>{
    const h=harness('frontend/js/plugins/sdk.js'),sdk=h.window.ZenPlugin({hostOrigin:'https://crm.example.com'});
    await assert.rejects(sdk.call('clients.list'));
    await h.emit({source:h.window.parent,origin:'https://evil.example.com',data:{type:'zen:init',channel:'bad'}});
    await assert.rejects(sdk.context());
    await h.emit({source:h.window.parent,origin:'https://crm.example.com',data:{type:'zen:init',channel:'valid',context:{entity_id:1}}});
    assert.equal((await sdk.ready()).entity_id,1);
    const response=sdk.call('clients.get',{id:1}),request=h.messages.at(-1);
    assert.equal(request.origin,'https://crm.example.com');
    await h.emit({source:h.window.parent,origin:'https://crm.example.com',data:{type:'zen:response',channel:'valid',id:request.value.id,result:{id:1}}});
    assert.equal((await response).id,1);
    const pending=sdk.context();sdk.close();await assert.rejects(pending,/SDK closed/);assert.equal(h.listeners.size,0);
});
