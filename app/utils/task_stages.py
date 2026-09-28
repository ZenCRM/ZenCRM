"""Konfiguracja globalnych etapów zadań (poza etapami projektów)."""
import json
import re

from ..models.setting import Setting
from ..models.task import Task

DEFAULT_TASK_STAGES = [
    {'id': 'todo', 'label': 'Do zrobienia', 'accent': '#865528'},
    {'id': 'in_progress', 'label': 'W toku', 'accent': '#008c9f'},
    {'id': 'done', 'label': 'Zrobione', 'accent': '#16886e'},
]


def get_task_stages():
    try:
        stages = json.loads(Setting.get_value('task_stages', 'null'))
        return stages if isinstance(stages, list) and stages else DEFAULT_TASK_STAGES
    except (ValueError, TypeError):
        return DEFAULT_TASK_STAGES


def validate_task_stages(stages):
    if not isinstance(stages, list) or not 2 <= len(stages) <= 20:
        raise ValueError('Ustaw od 2 do 20 statusów zadań.')
    if any(not isinstance(stage, dict) for stage in stages):
        raise ValueError('Nieprawidłowy status zadania.')
    ids = [stage.get('id') for stage in stages]
    if any(not isinstance(key, str) for key in ids):
        raise ValueError('Nieprawidłowy identyfikator statusu.')
    if ids[0] != 'todo' or ids[-1] != 'done':
        raise ValueError('Pozostaw status początkowy jako pierwszy i zakończony jako ostatni.')
    if len(set(ids)) != len(ids):
        raise ValueError('Statusy muszą mieć unikalne identyfikatory.')
    clean = []
    for stage in stages:
        key, label, accent = stage.get('id'), stage.get('label'), stage.get('accent')
        if not isinstance(key, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,19}', key):
            raise ValueError('Nieprawidłowy identyfikator statusu.')
        if not isinstance(label, str) or not 1 <= len(label.strip()) <= 60:
            raise ValueError('Nazwa statusu musi mieć od 1 do 60 znaków.')
        if not isinstance(accent, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', accent):
            raise ValueError('Wybierz poprawny kolor statusu.')
        clean.append({'id': key, 'label': label.strip(), 'accent': accent})
    used = {status for (status,) in Task.query.with_entities(Task.status).filter(Task.project_id.is_(None)).distinct().all()}
    if used - set(ids):
        raise ValueError('Przenieś zadania z usuwanego statusu do innego etapu (także w archiwum).')
    return clean
