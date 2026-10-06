const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const crypto=require('node:crypto');

test('iframe reload rotates channel and discards the previous document response', async()=>{
    let listener, onLoad, resolve;
    const sent=[];
    const window={ZenI18n:{t:key=>key},addEventListener:(type,fn)=>listener=fn,removeEventListener(){}};
    vm.runInNewContext(fs.readFileSync('frontend/js/plugins/host.js','utf8'),{window,crypto});
    const frame={contentWindow:{postMessage:message=>sent.push(message)},style:{},addEventListener:(type,fn)=>onLoad=fn,removeEventListener(){},remove(){}};
    const port=window.ZenPluginBridge.create(frame,'https://app.example.com',{},()=>new Promise(r=>resolve=r),()=>true);
    onLoad();const first=sent[0].channel;
    const pending=listener({source:frame.contentWindow,origin:'https://app.example.com',data:{type:'zen:request',channel:first,id:'1',method:'call',operation:'clients.list'}});
    onLoad();assert.notEqual(first,sent[1].channel);
    resolve({private:'old document'});await pending;
    assert.equal(sent.length,2);
    await listener({source:frame.contentWindow,origin:'https://app.example.com',data:{type:'zen:request',channel:first,id:'2',method:'context'}});
    assert.equal(sent.length,2);port.close();
});
