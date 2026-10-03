"""Domyslne wartosci ustawien CRM."""

DEFAULTS = {
    'client_company_provider': '',
    'client_statuses': 'null',
    'client_metrics': 'null',
    'gus_enabled': 'false',
    'gus_api_key': '',
    # ── BRANDING ──
    'brand_name':            'ZenCRM',
    'brand_color_primary':   '#7e3af2',
    'brand_color_secondary': '#6366f1',
    'brand_logo_light':      '/logo.png',
    'brand_logo_dark':       '/logo.png',
    'brand_logo_size':       '56',
    'brand_favicon':         '/icon.png',

    # ── LOGIN ──
    'login_bg_type':         'gradient',
    'login_bg_color':        '#7e3af2',
    'login_bg_color2':       '#6366f1',
    'login_bg_image':        '',
    'login_welcome_text':    'Zaloguj sie do systemu',
    'login_footer':          '',
    'login_show_logo':       'true',

    # ── DANE FIRMY ──
    'company_name':          'ZenCRM Sp. z o.o.',
    'company_address':       'ul. Przykladowa 1, 00-001 Warszawa',
    'company_nip':           '0000000000',
    'company_email':         'kontakt@zencrm.pl',
    'company_phone':         '+48 22 000 00 00',
    'company_www':           'zencrm.pl',

    'ui_detail_client': 'compact',
    'ui_detail_lead': 'compact',
    'ui_detail_task': 'compact',
    'ui_detail_service': 'compact',

    # ── UI ──
    'ui_template':           'classic',
    'ui_hero_background':    'random',
    'ui_show_footer':        'false',
    'ui_footer_text':        '© 2026 ZenCRM',
    'ui_dark_default':       'false',

    # ── MENU ──
    'menu_permissions':      '{}',

    # ── LEADS ──
    'lead_sources':          '["Formularz WWW", "Polecenie", "Kampania reklamowa", "Social Media", "Telefon / Zimny kontakt", "Targi / Konferencja", "Partner", "Inne"]',
    'lead_webhook_enabled':  'true',
    'lead_webhook_token':    '',
}


def seed_defaults():
    """Wstawia brakujace ustawienia do bazy (nie nadpisuje istniejacych)."""
    import secrets
    from ..extensions import db
    from ..models.setting import Setting
    added = 0
    for key, value in DEFAULTS.items():
        if not Setting.query.filter_by(key=key).first():
            cat = _category(key)
            val = str(value)
            if key == 'lead_webhook_token' and not val:
                val = f'zen_lead_{secrets.token_hex(16)}'
            Setting.set_value(key, val, cat)
            added += 1
    # Check if lead_webhook_token exists but is empty
    token_rec = Setting.query.filter_by(key='lead_webhook_token').first()
    if token_rec and not token_rec.value:
        token_rec.value = f'zen_lead_{secrets.token_hex(16)}'
    db.session.commit()
    return added


def _category(key):
    if key.startswith('client_'):
        return 'clients'
    if key.startswith('gus_'):
        return 'gus'
    if key.startswith('brand_'):
        return 'branding'
    if key.startswith('login_'):
        return 'login'
    if key.startswith('company_'):
        return 'company'
    if key.startswith('ui_'):
        return 'ui'
    if key.startswith('lead_'):
        return 'leads'
    if key.startswith('menu_'):
        return 'menu'
    return 'general'
