const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {createComponent} = require('./helpers/frontend_contract.cjs');

test('restored session sets administrator controls before initialization awaits network', async () => {
    for (const [role, initial, expected] of [['admin', false, true], ['employee', true, false]]) {
        const sandbox = {window:{}, sessionStorage:{getItem:()=>null,setItem:()=>{}}, location:{reload:()=>{}}};
        vm.createContext(sandbox);
        vm.runInContext(fs.readFileSync('frontend/js/core/lifecycle.js', 'utf8'), sandbox);
        let finish;
        const app = {...sandbox.window.ZenCore.lifecycle(), user:{role}, isAdmin:initial, token:'restored', api:()=>new Promise(resolve=>{finish=resolve;})};
        const pending = app.init();
        assert.equal(app.isAdmin, expected);
        finish({languages:{}});
        await pending;
    }
});

test('task status editor supports edits, insertion, reordering, deletion and persistence', async () => {
    const app = createComponent();
    app.editTaskStages();
    app.taskStageDraft[1].label = 'Weryfikacja';
    app.taskStageDraft[1].accent = '#123456';
    app.addTaskStage();
    const added = app.taskStageDraft[2].id;
    app.moveTaskStage(2,-1);
    assert.equal(app.taskStageDraft[1].id,added);
    app.moveTaskStage(1,1);
    assert.equal(app.taskStageDraft[1].label,'Weryfikacja');
    app.removeTaskStage(added);
    app.removeTaskStage('todo'); app.removeTaskStage('done');
    assert.equal(app.taskStageDraft.length,3);
    app.api = async (url, options) => {
        assert.equal(url,'/tasks/board-settings');
        return JSON.parse(options.body);
    };
    app.notify = () => {};
    await app.saveTaskStages();
    assert.equal(app.taskStageEditorOpen,false);
    assert.equal(app.taskStatusStages[1].label,'Weryfikacja');
    assert.equal(app.taskStatusStages[1].accent,'#123456');
});
