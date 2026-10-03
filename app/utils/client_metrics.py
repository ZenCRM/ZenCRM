import re


def validate_metrics(metrics, statuses):
    if not isinstance(metrics, list) or len(metrics) > 6:
        raise ValueError('Wybierz maksymalnie 6 metryk.')
    allowed = {'all', 'assigned', 'unassigned'} | {'status:' + s['id'] for s in statuses}
    clean = []
    for metric in metrics:
        if not isinstance(metric, dict) or metric.get('id') not in allowed:
            raise ValueError('Wybierz poprawną metrykę klientów.')
        color = metric.get('color')
        if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise ValueError('Wybierz poprawny kolor metryki.')
        clean.append({'id': metric['id'], 'color': color})
    if len({m['id'] for m in clean}) != len(clean):
        raise ValueError('Metryki nie mogą się powtarzać.')
    return clean
