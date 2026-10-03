const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');

function createComponent() {
    class FixedDate extends Date {
        constructor(...args) { super(...(args.length ? args : ['2026-10-03T12:00:00Z'])); }
        static now() { return Date.parse('2026-10-03T12:00:00Z'); }
    }
    const sandbox = {window: {}, localStorage: {getItem: () => null}, location: {hash: ''},
        Date: FixedDate, console, setTimeout, clearTimeout};
    vm.createContext(sandbox);
    const head = fs.readFileSync('frontend/views/head.html', 'utf8');
    const featureScripts = [...head.matchAll(/src="(\/js\/(?:modules|core|settings)\/[^?\"]+)(?:\?[^\"]*)?"/g)]
        .map(match => match[1]);
    const files = ['/locales/pl.js', '/locales/en.js', '/js/i18n.js', '/js/config.js', '/js/ux.js',
        ...featureScripts, '/js/app.js'];
    for (const file of files) vm.runInContext(fs.readFileSync('frontend' + file, 'utf8'), sandbox);
    return sandbox.crmApp();
}

function capture() {
    const hash = fn => crypto.createHash('sha256').update(fn.toString().replace(/\s+/g, ' ')).digest('hex');
    return Object.fromEntries(Object.entries(Object.getOwnPropertyDescriptors(createComponent()))
        .sort(([a], [b]) => a.localeCompare(b, 'en'))
        .map(([key, descriptor]) => [key, {
            enumerable: descriptor.enumerable, configurable: descriptor.configurable,
            writable: descriptor.writable,
            get: descriptor.get && hash(descriptor.get),
            set: descriptor.set && hash(descriptor.set),
            value: typeof descriptor.value === 'function' ? {function: hash(descriptor.value)}
                : JSON.parse(JSON.stringify(descriptor.value === undefined ? null : descriptor.value)),
        }]));
}
module.exports = {capture, createComponent};
