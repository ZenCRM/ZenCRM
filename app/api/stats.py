from datetime import datetime, timedelta
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from ..extensions import db
from ..models.client import Client
from ..models.lead import Lead
from ..models.task import Task
from ..models.offer import Offer
from ..models.meeting import Meeting
from ..models.service import Service
from ..models.project import Project
from ..models.ticket import Ticket
from ..models.activity import Activity
from ..models.user import User

stats_bp = Blueprint('stats', __name__)


@stats_bp.route('', methods=['GET'])
@jwt_required()
def get_stats():
    now = datetime.utcnow()
    month_ago = now - timedelta(days=30)

    # ── Karty KPI ──
    cards = {
        'clients':  Client.query.filter(Client.deleted_at.is_(None)).count(),
        'leads':    Lead.query.filter(Lead.deleted_at.is_(None)).count(),
        'projects': Project.query.filter(Project.deleted_at.is_(None)).count(),
        'tasks':    Task.query.filter(Task.status != 'done', Task.deleted_at.is_(None)).count(),
        'tickets':  Ticket.query.count(),
        'tickets_open': Ticket.query.filter(Ticket.status.notin_(['resolved', 'closed'])).count(),
        'services': Service.query.filter(Service.deleted_at.is_(None)).count(),
        'offers':   Offer.query.count(),
        'meetings': Meeting.query.count(),
        'revenue':  float(db.session.query(
            func.coalesce(func.sum(Offer.total_amount), 0)
        ).filter(Offer.status == 'accepted').scalar() or 0),
        'won_value': float(db.session.query(
            func.coalesce(func.sum(Lead.value), 0)
        ).filter(Lead.stage == 'won', Lead.deleted_at.is_(None)).scalar() or 0),
        'pipeline': float(db.session.query(
            func.coalesce(func.sum(Lead.value), 0)
        ).filter(Lead.stage.notin_(['won', 'lost']), Lead.deleted_at.is_(None)).scalar() or 0),
    }

    # ── Lejek sprzedaży ──
    from ..utils.lead_stages import get_stages
    stages = [s['id'] for s in get_stages()]
    funnel = {s: Lead.query.filter_by(stage=s).filter(Lead.deleted_at.is_(None)).count() for s in stages}
    lead_values = dict(db.session.query(Lead.stage, func.coalesce(func.sum(Lead.value), 0))
                       .filter(Lead.deleted_at.is_(None)).group_by(Lead.stage).all())
    task_status = dict(db.session.query(Task.status, func.count(Task.id))
                       .filter(Task.deleted_at.is_(None)).group_by(Task.status).all())

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # ── Zadania dla dashboardu (zaległe, dzisiaj, najbliższe) ──
    overdue_tasks = Task.query.filter(
        Task.status != 'done',
        Task.deleted_at.is_(None),
        Task.due_date.isnot(None),
        Task.due_date < now,
    ).order_by(Task.due_date.asc()).limit(20).all()

    today_tasks = Task.query.filter(
        Task.status != 'done',
        Task.deleted_at.is_(None),
        Task.due_date.isnot(None),
        Task.due_date >= today_start,
        Task.due_date <= today_end,
    ).order_by(Task.due_date.asc()).limit(20).all()

    upcoming_tasks = Task.query.filter(
        Task.status != 'done',
        Task.deleted_at.is_(None),
        (Task.due_date > today_end) | (Task.due_date.is_(None)),
    ).order_by(Task.due_date.asc().nullslast()).limit(20).all()

    # ── Nadchodzące spotkania ──
    upcoming_meetings = Meeting.query.filter(Meeting.start_time >= now) \
        .order_by(Meeting.start_time.asc()).limit(3).all()

    # ── Ostatnia aktywność ──
    recent = Activity.query.order_by(Activity.created_at.desc()).limit(8).all()

    # ── Top klienci (wg wygranych leadów) ──
    top_clients_rows = db.session.query(
        Client.id, Client.name,
        func.coalesce(func.sum(Lead.value), 0).label('total'),
    ).join(Lead, Lead.client_id == Client.id) \
     .filter(Lead.stage == 'won') \
     .group_by(Client.id, Client.name) \
     .order_by(func.sum(Lead.value).desc()) \
     .limit(5).all()
    top_clients = [
        {'id': r[0], 'name': r[1], 'value': float(r[2] or 0)}
        for r in top_clients_rows
    ]

    # ── Aktywni użytkownicy (liczba aktywności w ostatnich 30 dniach) ──
    top_users_rows = db.session.query(
        User.id, User.first_name, User.last_name, User.avatar_url,
        func.count(Activity.id).label('cnt'),
    ).join(Activity, Activity.user_id == User.id) \
     .filter(Activity.created_at >= month_ago) \
     .group_by(User.id, User.first_name, User.last_name, User.avatar_url) \
     .order_by(func.count(Activity.id).desc()) \
     .limit(5).all()
    top_users = [
        {'id': r[0], 'first_name': r[1], 'last_name': r[2],
         'avatar_url': r[3], 'count': r[4]}
        for r in top_users_rows
    ]

    # ── Zadania do zrobienia dziś (licznik) ──
    tasks_today = Task.query.filter(
        Task.status != 'done',
        Task.deleted_at.is_(None),
        Task.due_date.isnot(None),
        Task.due_date <= today_end,
    ).count()

    return jsonify({
        'cards': cards,
        'funnel': funnel,
        'lead_values': {stage: float(lead_values.get(stage, 0)) for stage in stages},
        'task_status': task_status,
        'overdue_tasks': [t.to_dict() for t in overdue_tasks],
        'today_tasks': [t.to_dict() for t in today_tasks],
        'upcoming_tasks': [t.to_dict() for t in upcoming_tasks],
        'upcoming_meetings': [m.to_dict() for m in upcoming_meetings],
        'recent_activities': [a.to_dict() for a in recent],
        'top_clients': top_clients,
        'top_users': top_users,
        'tasks_today': tasks_today,
    }), 200
