const test = require('node:test');
const assert = require('node:assert/strict');
const {createComponent} = require('./helpers/frontend_contract.cjs');

test('ticket links and email previews use the CRM address and configured helpdesk path', () => {
    const app = createComponent();
    app.settingsForm.crm_base_url = 'https://crm.example.com:8443';
    app.ticketConfig = {helpdesk_path:'/support'};
    assert.equal(app.getTicketTrackingUrl('a/b?c'), 'https://crm.example.com:8443/support?ticket=a%2Fb%3Fc');
    app.helpdeskForm.helpdesk_path = '/support';
    app.selectedEmailTemplate = 'client_ticket_created';
    app.emailTemplateForm.subject = '{{ticket_number}}';
    app.emailTemplateForm.body_html = '<p><a href="{{ticket_url}}">Ticket</a><a href="{{login_url}}">CRM</a></p>';
    const preview = app.getRenderedEmailPreview();
    assert.ok(preview.html.includes('https://crm.example.com:8443/support?ticket=demo'));
    assert.ok(preview.html.includes('href="https://crm.example.com:8443"'));
    assert.ok(preview.html.includes('https://crm.example.com:8443/logo.png'));
});
