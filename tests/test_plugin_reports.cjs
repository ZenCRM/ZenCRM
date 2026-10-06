const test = require('node:test'), assert = require('node:assert/strict'), vm = require('node:vm'), fs = require('node:fs');
function setup() {
    const sandbox = {window:{ZenI18n:{t:key=>key}},Date,Blob,URL,setTimeout};
    vm.runInNewContext(fs.readFileSync('frontend/js/plugins/reports.js','utf8'), sandbox);
    const entry = {app:{id:'zencrm-report-studio'}};
    const component = sandbox.window.pluginReport(entry);
    Object.assign(component,{token:'session',currentView:'plugin/zencrm-report-studio/main',active:()=>true});
    return {component,csv:sandbox.window.ZenReportCSV.encode,sandbox};
}
test('report CSV neutralizes formula injection and escapes delimiters, quotes and newlines',()=>{
    const {csv}=setup(); const value=csv([['=HYPERLINK("https://evil")',' \t+cmd','-1','@SUM(1)', '\tcommand','Safe;"quoted"\ntext',42]]);
    assert.ok(value.startsWith('\uFEFF'));
    assert.ok(value.includes('"\'=HYPERLINK(""https://evil"")"'));
    assert.ok(value.includes('"\' \t+cmd"'));
    assert.ok(value.includes('"\'-1"'));assert.ok(value.includes('"\'@SUM(1)"'));assert.ok(value.includes('"\'\tcommand"'));
    assert.ok(value.includes('"Safe;""quoted""\ntext"'));assert.ok(value.endsWith('"42"\r\n'));
});
test('report generation uses the plugin invocation contract and clears stale output',async()=>{
    const {component:c}=setup(); const calls=[];c.report={total:99};c.entity='clients';c.dateFrom='2020-01-01';c.dateTo='2020-01-31';c.overdueOnly=true;
    c.api=async(path,options)=>{calls.push([path,JSON.parse(options.body)]);return {total:2,rows:[]};};await c.generate();
    assert.equal(c.report.total,2);assert.equal(c.busy,false);
    assert.equal(calls[0][0],'/plugins/apps/zencrm-report-studio/invoke');assert.equal(calls[0][1].operation,'reports.aggregate');
    assert.deepEqual(calls[0][1].params,{entity:'clients',group_by:'status',date_from:'2020-01-01',date_to:'2020-01-31',status:'',overdue_only:false});
});
test('late report replies cannot overwrite newer filters or survive destruction',async()=>{
    const {component:c}=setup();const resolvers=[];c.api=()=>new Promise(resolve=>resolvers.push(resolve));
    const first=c.generate();c.entity='clients';const second=c.generate();resolvers[1]({total:2});await second;resolvers[0]({total:99});await first;
    assert.equal(c.report.total,2);const last=c.generate();c.destroy();resolvers[2]({total:99});await last;assert.equal(c.report,null);
});
test('logout and navigation changes discard private in-flight reports',async()=>{
    for(const change of [c=>c.token='',c=>c.currentView='dashboard']) {
        const {component:c}=setup();let resolve;c.api=()=>new Promise(r=>resolve=r);const request=c.generate();change(c);resolve({total:99});await request;
        assert.equal(c.report,null);
    }
});
test('failed report requests remove the previous report and expose the error',async()=>{
    const {component:c}=setup();c.report={total:1};c.api=async()=>{throw Error('Denied');};await c.generate();
    assert.equal(c.report,null);assert.equal(c.reportError,'Denied');assert.equal(c.busy,false);
});
test('export records the generated filters instead of unsaved form changes',async()=>{
    const {component:c,sandbox}=setup();let download,blob,clicked=false;
    sandbox.URL={createObjectURL:value=>{blob=value;return 'blob:local';},revokeObjectURL:()=>{}};sandbox.setTimeout=fn=>fn();
    sandbox.document={createElement:()=>download={click:()=>clicked=true}};
    c.report={entity:'tasks',group_by:'status',date_from:'2020-01-01',date_to:'2020-01-31',status:'=unsafe',overdue_only:false,
        generated_at:'2020-02-01T12:00:00Z',total:1,rows:[{label:'=unsafe',count:1,percent:100}]};
    c.entity='clients';c.dateFrom='2026-01-01';c.exportCSV();const contents=await blob.text();
    assert.equal(clicked,true);assert.equal(download.download,'zencrm-report-tasks-2020-02-01.csv');
    assert.ok(contents.includes('2020-01-01'));assert.ok(!contents.includes('2026-01-01'));assert.ok(contents.includes("'=unsafe"));
    c.token='';clicked=false;c.exportCSV();assert.equal(clicked,false);
});
