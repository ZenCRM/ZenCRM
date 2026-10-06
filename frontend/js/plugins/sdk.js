/* Vendor SDK: explicitly configure the expected CRM origin. No CRM token crosses the bridge. */
(function (root) {
    'use strict';
    root.ZenPlugin = function ({hostOrigin}) {
        const origin = new URL(hostOrigin).origin;
        if (new URL(hostOrigin).protocol !== 'https:' && !['localhost', '127.0.0.1'].includes(new URL(hostOrigin).hostname)) throw new Error('CRM origin must use HTTPS');
        let channel = null, context = null, sequence = 0, closed = false;
        const pending = new Map();
        let resolveReady;
        const ready = new Promise(resolve => { resolveReady = resolve; });
        const listener = event => {
            if (closed || event.source !== root.parent || event.origin !== origin) return;
            const message = event.data;
            if (!message || typeof message.channel !== 'string') return;
            if (message.type === 'zen:init' && !channel) {
                channel = message.channel; context = message.context; resolveReady(context); return;
            }
            if (message.type !== 'zen:response' || message.channel !== channel) return;
            const request = pending.get(message.id);
            if (!request) return;
            pending.delete(message.id); clearTimeout(request.timeout);
            message.error ? request.reject(new Error(message.error)) : request.resolve(message.result);
        };
        root.addEventListener('message', listener);
        function send(method, operation, params) {
            if (closed || !channel) return Promise.reject(new Error('Wait for ready() before calling the host'));
            if (pending.size >= 8) return Promise.reject(new Error('Too many pending requests'));
            const id = String(++sequence);
            return new Promise((resolve, reject) => {
                const timeout = setTimeout(() => { pending.delete(id); reject(new Error('Host request timed out')); }, 15000);
                pending.set(id, {resolve, reject, timeout});
                root.parent.postMessage({type:'zen:request', channel, id, method, operation, params}, origin);
            });
        }
        return {
            ready: () => ready,
            call: (operation, params = {}) => send('call', operation, params),
            context: () => send('context'),
            resize: height => send('resize', null, {height}),
            close() {
                closed = true; root.removeEventListener('message', listener);
                for (const request of pending.values()) { clearTimeout(request.timeout); request.reject(new Error('SDK closed')); }
                pending.clear();
            }
        };
    };
})(window);
