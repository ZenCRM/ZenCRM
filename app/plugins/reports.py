"""Bounded aggregate reports over the integration's existing record visibility policy."""
import re
from datetime import datetime, timedelta
from flask import abort
from sqlalchemy import case, func
from ..models.client import Client
from ..models.task import Task
from .policy import visible_clients, visible_tasks


def report_date(value):
    if value is None or value == '':
        return None
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        abort(400)
    try:
        parsed = datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        abort(400)
    # Leave room for the inclusive end-date conversion to the next midnight.
    if parsed.year < 1900 or parsed.year > 9998:
        abort(400)
    return parsed


def aggregate_report(user, params):
    if set(params) - {'entity', 'group_by', 'date_from', 'date_to', 'status', 'overdue_only'}:
        abort(400)
    entity, group = params.get('entity', 'tasks'), params.get('group_by', 'status')
    if entity not in ('clients', 'tasks') or group not in ('status', 'priority') or (entity == 'clients' and group != 'status'):
        abort(400)
    start, end = report_date(params.get('date_from')), report_date(params.get('date_to'))
    if start and end and start > end:
        abort(400)
    status, overdue_only = params.get('status', ''), params.get('overdue_only', False)
    if not isinstance(status, str) or len(status) > 20 or any(ord(c) < 32 for c in status):
        abort(400)
    if type(overdue_only) is not bool or (overdue_only and entity != 'tasks'):
        abort(400)
    model = Task if entity == 'tasks' else Client
    query = visible_tasks(user) if entity == 'tasks' else visible_clients(user)
    if start:
        query = query.filter(model.created_at >= start)
    if end:
        query = query.filter(model.created_at < end + timedelta(days=1))
    if status:
        query = query.filter(model.status == status)
    now = datetime.utcnow()
    unfinished = (Task.status.is_(None) | (Task.status != 'done'))
    overdue = unfinished & Task.due_date.is_not(None) & (Task.due_date < now)
    if overdue_only:
        query = query.filter(overdue)
    label = func.coalesce(getattr(model, group), '')
    count = func.count(model.id)
    # Windows run before LIMIT. One statement keeps totals, metrics and groups consistent
    # even when another request changes records while the report is being generated.
    columns = [label, count, func.sum(count).over()]
    if entity == 'tasks':
        columns.extend(func.sum(func.sum(case((condition, 1), else_=0))).over()
                       for condition in (unfinished, Task.status == 'done', overdue))
    grouped = query.with_entities(*columns).group_by(label).order_by(count.desc(), label).limit(100).all()
    total = int(grouped[0][2]) if grouped else 0
    metrics = ({key: int(grouped[0][index]) if grouped else 0
                for index, key in enumerate(('open', 'done', 'overdue'), start=3)} if entity == 'tasks' else {})
    rows = [{'label': row[0], 'count': row[1], 'percent': round(row[1] * 100 / total, 2) if total else 0}
            for row in grouped]
    # Legacy/custom statuses can be arbitrarily numerous; preserve the total without an unbounded response.
    remainder = total - sum(row['count'] for row in rows)
    if remainder:
        rows.append({'label': '', 'other': True, 'count': remainder, 'percent': round(remainder * 100 / total, 2)})
    return {'entity': entity, 'group_by': group, 'date_from': start.date().isoformat() if start else None,
            'date_to': end.date().isoformat() if end else None, 'status': status, 'overdue_only': overdue_only,
            'generated_at': now.isoformat(timespec='seconds') + 'Z', 'total': total, 'metrics': metrics, 'rows': rows}
