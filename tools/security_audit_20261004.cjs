// Offline regression check: a session change must suppress the old download.
// The DOM, network and Blob URLs are mocks: no files are actually downloaded.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
let resolveResponse;
let clicks = 0;
const sandbox = {
    AbortController,
    window: {ZenI18n: {locale: 'pl', t: value => value}},
    fetch: () => new Promise(resolve => { resolveResponse = resolve; }),
    URL: {createObjectURL: () => 'blob:audit-mock', revokeObjectURL: () => {}},
    document: {createElement: () => ({click() { clicks++; }})},
    setTimeout: () => {},
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('frontend/js/modules/mailboxes.js', 'utf8'), sandbox);
(async () => {
    const app = sandbox.window.ZenModules.mailboxes();
    app.token = 'session-A'; app.mail.boxId = 1; app.mail.selected = {id: 1};
    const pending = app.downloadMailAttachment({part: '2', filename: 'private-audit-dummy.pdf'});
    app.token = 'session-B'; app.mail = sandbox.window.ZenModules.mailboxes().mail;
    resolveResponse({ok: true, blob: async () => ({})});
    await pending;
    assert.equal(clicks, 0);
    console.log(JSON.stringify({download_after_session_change: false, simulated_download_clicks: clicks}));
})().catch(error => { console.error(error); process.exitCode = 1; });
