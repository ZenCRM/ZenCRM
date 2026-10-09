const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');

const html = fs.readFileSync('frontend/views/record-form.html', 'utf8');

test('generic record-form controls carry the field label as their accessible name', () => {
    const generic = [
        /<textarea x-model="modal\.form\[field\.key\]"[^>]*>/,
        /<template x-if="field\.type === 'select' &&[^"]*">\s*<select x-model="modal\.form\[field\.key\]"[^>]*>/,
        /<template x-if="field\.type === 'project-select'">\s*<select[^>]*>/,
        /<template x-if="field\.type === 'client-select'">\s*<select[^>]*>/,
        /<input :type="field\.type" x-model="modal\.form\[field\.key\]"[\s\S]*?>/,
    ];
    for (const pattern of generic) {
        const tag = html.match(pattern);
        assert.ok(tag, `control not found: ${pattern}`);
        assert.match(tag[0], /:aria-label="field\.label"/, `missing :aria-label in ${tag[0].slice(0, 80)}`);
    }
});
