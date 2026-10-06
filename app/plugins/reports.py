"""Field-allowlisted, bounded aggregates with explicit integration record visibility."""
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from flask import abort
from sqlalchemy import case, cast, Date, DateTime, String, func
from .policy import visible_report_records

SOURCES = {
    'clients': {'status': 'status', 'groups': {'status': 'status', 'country': 'country'}, 'dates': {'created_at': 'created_at'}},
    'tasks': {'status': 'status', 'groups': {'status': 'status', 'priority': 'priority'}, 'dates': {'created_at': 'created_at', 'due_date': 'due_date'}, 'done': ['done'], 'due': 'due_date'},
    'leads': {'status': 'stage', 'groups': {'status': 'stage', 'source': 'source'}, 'dates': {'created_at': 'created_at', 'expected_close_date': 'expected_close_date'}, 'amount': 'value'},
    'projects': {'status': 'status', 'groups': {'status': 'status'}, 'dates': {'created_at': 'created_at', 'start_date': 'start_date', 'end_date': 'end_date'}, 'amount': 'budget', 'done': ['completed', 'done', 'cancelled'], 'due': 'end_date'},
    'tickets': {'status': 'status', 'groups': {'status': 'status', 'priority': 'priority', 'category': 'category', 'source': 'source'}, 'dates': {'created_at': 'created_at', 'resolved_at': 'resolved_at', 'closed_at': 'closed_at'}, 'done': ['resolved', 'closed']},
    'documents': {'status': 'status', 'groups': {'status': 'status', 'type': 'type'}, 'dates': {'created_at': 'created_at', 'updated_at': 'updated_at'}},
    'offers': {'status': 'status', 'groups': {'status': 'status'}, 'dates': {'created_at': 'created_at', 'valid_until': 'valid_until'}, 'amount': 'total_amount', 'done': ['accepted', 'rejected', 'expired'], 'due': 'valid_until'},
    'services': {'status': 'status', 'groups': {'status': 'status', 'billing_type': 'billing_type', 'billing_cycle': 'billing_cycle'}, 'dates': {'created_at': 'created_at', 'start_date': 'start_date', 'end_date': 'end_date'}, 'amount': 'price'},
    'meetings': {'status': 'status', 'groups': {'status': 'status'}, 'dates': {'created_at': 'created_at', 'start_time': 'start_time', 'end_time': 'end_time'}},
}


def report_capabilities():
    return {name: {'groups': list(item['groups']) + ['month'], 'dates': list(item['dates']),
                   'amount': 'amount' in item, 'overdue': 'due' in item} for name, item in SOURCES.items()}


def report_date(value):
    if value is None or value == '':
        return None
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        abort(400)
    try:
        parsed = datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        abort(400)
    if not 1900 <= parsed.year <= 9998:
        abort(400)
    return parsed


def amount_filter(value):
    if value is None or value == '':
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        abort(400)
    try:
        result = Decimal(str(value))
        if not result.is_finite() or abs(result) > Decimal('1000000000000'):
            abort(400)
        return result
    except InvalidOperation:
        abort(400)


def aggregate_report(user, params):
    if set(params) - {'entity', 'group_by', 'date_from', 'date_to', 'status', 'overdue_only', 'date_field', 'compare_previous', 'amount_min', 'amount_max'}:
        abort(400)
    entity, group = params.get('entity', 'tasks'), params.get('group_by', 'status')
    if not isinstance(entity, str) or entity not in SOURCES or not isinstance(group, str):
        abort(400)
    source = SOURCES[entity]
    date_field = params.get('date_field', 'created_at')
    if group not in [*source['groups'], 'month'] or not isinstance(date_field, str) or date_field not in source['dates']:
        abort(400)
    start, end = report_date(params.get('date_from')), report_date(params.get('date_to'))
    if start and end and start > end:
        abort(400)
    status, overdue_only, compare = params.get('status', ''), params.get('overdue_only', False), params.get('compare_previous', False)
    if not isinstance(status, str) or len(status) > (30 if entity in ('leads', 'projects', 'tickets') else 20) or any(ord(c) < 32 for c in status):
        abort(400)
    if type(overdue_only) is not bool or (overdue_only and 'due' not in source) or type(compare) is not bool:
        abort(400)
    if compare and (not start or not end or (end - start).days > 3660):
        abort(400)
    minimum, maximum = amount_filter(params.get('amount_min')), amount_filter(params.get('amount_max'))
    if (minimum is not None or maximum is not None) and 'amount' not in source:
        abort(400)
    if minimum is not None and maximum is not None and minimum > maximum:
        abort(400)
    query = visible_report_records(user, entity)
    model = query.column_descriptions[0]['entity']
    status_column = getattr(model, source['status'])
    date_column = getattr(model, source['dates'][date_field])
    date_only = isinstance(date_column.type, Date) and not isinstance(date_column.type, DateTime)
    now = datetime.utcnow()
    if status:
        query = query.filter(status_column == status)
    amount = func.coalesce(getattr(model, source['amount']), 0) if 'amount' in source else None
    if minimum is not None:
        query = query.filter(amount >= minimum)
    if maximum is not None:
        query = query.filter(amount <= maximum)
    unfinished = (status_column.is_(None) | status_column.notin_(source.get('done', []))) if 'done' in source else None
    overdue = None
    if 'due' in source:
        due_column = getattr(model, source['due'])
        cutoff = now.date() if isinstance(due_column.type, Date) and not isinstance(due_column.type, DateTime) else now
        overdue = unfinished & due_column.is_not(None) & (due_column < cutoff)
    if overdue_only:
        query = query.filter(overdue)

    def period_query(first, last):
        result = query
        if first:
            result = result.filter(date_column >= (first.date() if date_only else first))
        if last:
            following = last + timedelta(days=1)
            result = result.filter(date_column < (following.date() if date_only else following))
        return result

    label = func.coalesce(func.substr(cast(date_column, String), 1, 7), '') if group == 'month' else func.coalesce(getattr(model, source['groups'][group]), '')
    count = func.count(model.id)
    columns = [label, count, func.sum(count).over()]
    metric_names = []
    for key, condition in [('open', unfinished), ('done', None if unfinished is None else ~unfinished), ('overdue', overdue)]:
        if condition is not None:
            columns.append(func.sum(func.sum(case((condition, 1), else_=0))).over()); metric_names.append(key)
    if amount is not None:
        columns.extend([func.sum(amount), func.sum(func.sum(amount)).over()])
    grouped = period_query(start, end).with_entities(*columns).group_by(label).order_by(*( [label] if group == 'month' else [count.desc(), label])).limit(100).all()
    total = int(grouped[0][2]) if grouped else 0
    metrics = {key: int(grouped[0][index]) if grouped else 0 for index, key in enumerate(metric_names, start=3)}
    rows = [{'label': row[0], 'count': row[1], 'percent': round(row[1] * 100 / total, 2) if total else 0,
             **({'amount': format(Decimal(str(row[3 + len(metric_names)])), '.2f')} if amount is not None else {})} for row in grouped]
    total_amount = Decimal(str(grouped[0][-1])) if amount is not None and grouped else Decimal(0)
    if amount is not None:
        metrics['amount'] = format(total_amount, '.2f')
    remainder = total - sum(row['count'] for row in rows)
    if remainder:
        other = {'label': '', 'other': True, 'count': remainder, 'percent': round(remainder * 100 / total, 2)}
        if amount is not None:
            other['amount'] = format(total_amount - sum(Decimal(row['amount']) for row in rows), '.2f')
        rows.append(other)
    comparison = None
    if compare:
        days = (end - start).days + 1
        previous_end, previous_start = start - timedelta(days=1), start - timedelta(days=days)
        if previous_start.year < 1900:
            abort(400)
        previous = period_query(previous_start, previous_end)
        previous_total = previous.count()
        comparison = {'date_from': previous_start.date().isoformat(), 'date_to': previous_end.date().isoformat(),
                      'total': previous_total, 'change': total - previous_total,
                      'change_percent': round((total - previous_total) * 100 / previous_total, 2) if previous_total else None}
        if amount is not None:
            comparison['amount'] = format(Decimal(str(previous.with_entities(func.coalesce(func.sum(amount), 0)).scalar())), '.2f')
    return {'entity': entity, 'group_by': group, 'date_field': date_field, 'date_from': start.date().isoformat() if start else None,
            'date_to': end.date().isoformat() if end else None, 'status': status, 'overdue_only': overdue_only,
            'amount_min': str(minimum) if minimum is not None else None, 'amount_max': str(maximum) if maximum is not None else None,
            'generated_at': now.isoformat(timespec='seconds') + 'Z', 'total': total, 'metrics': metrics, 'rows': rows, 'comparison': comparison}
