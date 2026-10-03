const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function component() {
    const context = {window:{},document:{activeElement:{focus(){}}},Date, setInterval,clearInterval};
    vm.createContext(context);
    vm.runInContext(fs.readFileSync('frontend/js/modules/reminders.js','utf8'),context);
    const app=context.window.ZenModules.reminders();
    Object.assign(app,{token:'one',$refs:{},$nextTick:fn=>fn(),api:async()=>[]});
    return app;
}
test('overdue reminders queue, snooze and dismiss without losing the next alert',async()=>{
    const app=component(); let sounds=0;
    app.playReminderSound=()=>sounds++;
    app.reminders=[{id:1,title:'One',remind_at:'2000-01-01T00:00:00Z'},{id:2,title:'Two',remind_at:'2000-01-01T00:00:00Z'}];
    app.checkReminders(); app.checkReminders();
    assert.equal(app.reminderActive.id,1);assert.equal(sounds,1);
    app.api=async()=>({id:1,remind_at:'2099-01-01T00:00:00Z',dismissed:false});
    await app.resolveReminder(app.reminderActive,'snooze');
    assert.equal(app.reminderActive.id,2);assert.equal(sounds,2);
    app.api=async()=>({id:2,dismissed:true});
    await app.resolveReminder(app.reminderActive,'dismiss');
    assert.equal(app.reminderActive,null);assert.equal(app.reminders.length,1);
});
test('failed action keeps alert available for retry',async()=>{
    const app=component();app.reminders=[{id:1,remind_at:'2000-01-01T00:00:00Z'}];app.checkReminders();
    app.api=async()=>{throw new Error('offline')};
    await app.resolveReminder(app.reminderActive,'dismiss');
    assert.equal(app.reminderActive.id,1);assert.equal(app.reminderError,'offline');assert.equal(app.reminderBusy,false);
});
test('logout ignores in-flight responses',async()=>{
    const app=component();let finish;
    app.api=()=>new Promise(resolve=>finish=resolve);
    const pending=app.loadReminders();app.stopReminders();app.token='';
    finish([{id:1,remind_at:'2000-01-01T00:00:00Z'}]);await pending;
    assert.equal(app.reminders.length,0);assert.equal(app.reminderActive,null);
});
