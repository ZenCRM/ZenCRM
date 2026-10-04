const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function component() {
    const calls = {clicked: 0, created: 0, revoked: 0};
    const sandbox = {
        window: {ZenI18n: {locale: 'pl', t: value => value}}, AbortController,
        URL: {createObjectURL() { calls.created++; return 'blob:dummy'; }, revokeObjectURL() { calls.revoked++; }},
        document: {createElement: () => ({click() { calls.clicked++; }})},
        setTimeout: callback => callback(),
    };
    vm.createContext(sandbox);
    vm.runInContext(fs.readFileSync('frontend/js/modules/mailboxes.js', 'utf8'), sandbox);
    const app = sandbox.window.ZenModules.mailboxes();
    app.token = 'A'; app.mail.boxId = 1; app.mail.selected = {id: 1};
    return {app, sandbox, calls};
}

test('attachment response from an old session cannot trigger a download', async () => {
    const {app, sandbox, calls} = component(); let resolve;
    sandbox.fetch = () => new Promise(done => { resolve = done; });
    const pending = app.downloadMailAttachment({part: '2', filename: 'private.pdf'});
    app.token = 'B'; app.mail = sandbox.window.ZenModules.mailboxes().mail;
    resolve({ok: true, blob: async () => ({})}); await pending;
    assert.equal(calls.clicked, 0); assert.equal(calls.created, 0);
});

test('session changes during blob transfer also suppress download', async () => {
    const {app, sandbox, calls} = component(); let resolveBlob;
    sandbox.fetch = async () => ({ok: true, blob: () => new Promise(done => { resolveBlob = done; })});
    const pending = app.downloadMailAttachment({part: '2', filename: 'private.pdf'});
    await new Promise(done => setImmediate(done));
    app.token = ''; resolveBlob({}); await pending;
    assert.equal(calls.clicked, 0); assert.equal(calls.created, 0);
});

test('cancelled download does not update the next session or show an error', async () => {
    const {app, sandbox, calls} = component(); let resolve;
    sandbox.fetch = (path, options) => {
        assert.ok(options.signal);
        return new Promise(done => { resolve = done; });
    };
    const state = app.mail;
    const pending = app.downloadMailAttachment({part: '2', filename: 'private.pdf'});
    state.downloadController.abort(); resolve({ok: true, blob: async () => ({})}); await pending;
    assert.equal(calls.clicked, 0); assert.equal(state.error, '');
    assert.equal(state.downloadController, null);
});

test('authorized download still works and revokes its blob URL', async () => {
    const {app, sandbox, calls} = component();
    sandbox.fetch = async () => ({ok: true, blob: async () => ({})});
    await app.downloadMailAttachment({part: '2', filename: 'safe.pdf'});
    assert.deepEqual(calls, {clicked: 1, created: 1, revoked: 1});
});
