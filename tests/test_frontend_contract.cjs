const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {capture, createComponent} = require('./frontend_contract.cjs');

test('production script order preserves the released component state, methods and getters', () => {
    const expected = JSON.parse(fs.readFileSync('tests/fixtures/frontend_contract.json', 'utf8'));
    assert.deepEqual(JSON.parse(JSON.stringify(capture())), expected);
});

test('component factories do not share mutable state', () => {
    const first = createComponent(), second = createComponent();
    first.loginForm.email = 'private@example.com';
    first.clients.push({id: 1});
    assert.equal(second.loginForm.email, '');
    assert.equal(second.clients.length, 0);
});
