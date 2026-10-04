const test = require('node:test');
const assert = require('node:assert/strict');
const {createComponent} = require('./helpers/frontend_contract.cjs');

function setup(type) {
    const app = createComponent();
    app.detailView = {open: true, type, id: 42, data: {client_id: 7}, tab: 'meetings'};
    app.canRecordAction = () => true;
    app.ensureLookups = () => {};
    app.loadCustomFields = () => {};
    app.loadEntityTelephony = undefined;
    app.notify = () => {};
    return app;
}

for (const type of ['client', 'lead']) {
    test(`${type}: adding meeting preserves relation, tab and refreshes list after save`, async () => {
        const app = setup(type);
        let posted;
        const calls = [];
        app.api = async (url, options) => {
            calls.push(url);
            if (options?.method === 'POST') {
                posted = JSON.parse(options.body);
                return {id: 9, ...posted};
            }
            if (url === `/meetings?${type}_id=42`) return posted ? [{id: 9, ...posted}] : [];
            if (url === `/${type === 'client' ? 'clients' : 'leads'}/42`) return {id: 42, client_id: 7};
            return [];
        };
        app.quickAdd('meeting');
        assert.equal(app.modal.view, 'meetings');
        assert.equal(app.modal.keepDetail, true);
        assert.equal(app.modal.form[type + '_id'], 42);
        if (type === 'lead') assert.equal(app.modal.form.client_id, 7);
        assert.ok(app.modal.lockedRelations.includes(type + '_id'));
        Object.assign(app.modal.form, {title: 'Demo', start_time: '2026-10-05T10:00', end_time: '2026-10-05T11:00'});
        await app.save();
        assert.equal(posted[type + '_id'], 42);
        assert.equal(app.detailView.tab, 'meetings');
        assert.equal(app.detailView.meetings[0].title, 'Demo');
        assert.ok(calls.includes(`/meetings?${type}_id=42`));
        assert.equal(app.modal.open, false);
    });
}

test('meetings load chronologically and stale responses cannot replace a new detail', async () => {
    const app = setup('lead');
    app.api = async url => url.startsWith('/meetings?') ? [
        {id: 2, start_time: '2026-10-06T12:00'}, {id: 1, start_time: '2026-10-05T12:00'}
    ] : [];
    await app.loadDetail();
    assert.deepEqual(Array.from(app.detailView.meetings, m => m.id), [1, 2]);
    let release;
    const old = app.detailView;
    app.api = url => url.startsWith('/meetings?') ? new Promise(resolve => {release = resolve;}) : Promise.resolve([]);
    const loading = app.loadDetail();
    app.detailView = {open: true, type: 'client', id: 99, meetings: []};
    release([{id: 3}]);
    await loading;
    assert.equal(app.detailView.id, 99);
    assert.equal(app.detailView.meetings.length, 0);
    assert.deepEqual(Array.from(old.meetings, m => m.id), [1, 2]);
});
