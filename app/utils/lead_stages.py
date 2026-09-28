import json
import re
from ..models.setting import Setting
from ..models.lead import Lead

DEFAULT_STAGES = [
    {'id': key, 'label': label, 'accent': color}
    for key, label, color in [
        ('new', 'Nowy', '#0057b8'), ('contacted', 'Kontakt', '#007fce'),
        ('qualified', 'Kwalifikowany', '#009fb9'), ('proposal', 'Oferta', '#27b8ce'),
        ('negotiation', 'Negocjacje', '#008e98'), ('won', 'Wygrany', '#27ad8a'),
        ('lost', 'Przegrany', '#20364b')]
]

def get_stages():
    try:
        return json.loads(Setting.get_value('lead_stages', 'null')) or DEFAULT_STAGES
    except (ValueError, TypeError):
        return DEFAULT_STAGES

def validate_stages(stages):
    if not isinstance(stages, list) or not 3 <= len(stages) <= 20:
        raise ValueError('Ustaw od 3 do 20 statusów.')
    clean = []
    for stage in stages:
        if not isinstance(stage, dict):
            raise ValueError('Nieprawidłowy status.')
        key, label, color = stage.get('id'), stage.get('label'), stage.get('accent')
        if not isinstance(key, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,29}', key):
            raise ValueError('Nieprawidłowy identyfikator statusu.')
        if not isinstance(label, str) or not 1 <= len(label.strip()) <= 60:
            raise ValueError('Nazwa statusu musi mieć od 1 do 60 znaków.')
        if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise ValueError('Wybierz poprawny kolor statusu.')
        clean.append({'id': key, 'label': label.strip(), 'accent': color})
    ids = {s['id'] for s in clean}
    if len(ids) != len(clean):
        raise ValueError('Statusy muszą mieć unikalne identyfikatory.')
    if not {'new', 'won', 'lost'} <= ids:
        raise ValueError('Pozostaw status początkowy, wygrany i przegrany; możesz zmienić ich nazwy i kolory.')
    used = {stage for (stage,) in Lead.query.with_entities(Lead.stage).distinct().all()}
    if used - ids:
        raise ValueError('Przenieś leady z usuwanego statusu do innego etapu (także w archiwum).')
    return clean
