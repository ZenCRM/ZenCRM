"""Run separately: python -m app.plugins.worker [--once]. No background Flask threads."""
import argparse
import json
import time
import uuid
from datetime import datetime, timedelta
from flask import current_app
from werkzeug.exceptions import HTTPException
from sqlalchemy import or_
from ..extensions import db
from ..utils.secret_storage import unseal
from .models import PluginDelivery, PluginEvent, PluginToken, PluginCode
from .policy import principal, require_scope, visible_clients, platform_enabled
from .transport import send_event


def run_once():
    if not platform_enabled():
        return 0
    now = datetime.utcnow()
    due = PluginDelivery.query.filter(
        PluginDelivery.status.in_(['pending', 'sending']), PluginDelivery.next_attempt_at <= now,
        or_(PluginDelivery.lease_until.is_(None), PluginDelivery.lease_until <= now)
    ).order_by(PluginDelivery.next_attempt_at).limit(20).all()
    processed = 0
    for delivery in due:
        lease = str(uuid.uuid4())
        changed = PluginDelivery.query.filter_by(id=delivery.id).filter(
            PluginDelivery.status.in_(['pending', 'sending']),
            or_(PluginDelivery.lease_until.is_(None), PluginDelivery.lease_until <= now)
        ).update({'status': 'sending', 'lease_token': lease, 'lease_until': now + timedelta(seconds=60),
                  'attempts': PluginDelivery.attempts + 1}, synchronize_session=False)
        db.session.commit()
        if not changed:
            continue
        db.session.refresh(delivery)
        event = db.session.get(PluginEvent, delivery.event_id)
        status_code = None
        outcome = 'pending'
        try:
            app, grant, user = principal(delivery.grant_id, app_revision=delivery.app_revision,
                                         grant_revision=delivery.grant_revision)
            require_scope(app, grant, 'clients.read')
            require_scope(app, grant, 'events.clients')
            from .models import PluginSubscription
            if not event or not PluginSubscription.query.filter_by(grant_id=grant.id, kind=event.kind).first():
                raise LookupError
            from ..models.client import Client
            client = db.session.get(Client, event.entity_id)
            # Recheck access before dispatch, including archival notifications.
            if not client or (user.role != 'admin' and client.assignee_id != user.id):
                raise LookupError
            if event.kind != 'client.archived.v1' and not visible_clients(user).filter_by(id=event.entity_id).first():
                raise LookupError
            body = json.dumps({'event_id': event.id, 'delivery_id': delivery.id, 'event': event.kind,
                'app_id': app.id, 'user_id': user.id, 'entity_id': event.entity_id,
                'occurred_at': event.created_at.isoformat() + 'Z'}, separators=(',', ':')).encode()
            url, signing = app.manifest.get('event_url'), app.signing_secret_encrypted
            if not url or not signing:
                raise LookupError
            # Release the read transaction before external IO, preserving the lease.
            secret = unseal(signing)
            db.session.rollback()
            status_code = send_event(url, body, delivery.id, secret)
            if 200 <= status_code < 300:
                outcome = 'delivered'
            elif status_code in (408, 429) or status_code >= 500:
                outcome = 'pending'
            else:
                outcome = 'failed'
        except (HTTPException, LookupError):
            db.session.rollback()
            outcome = 'cancelled'
        except Exception:
            db.session.rollback()
            current_app.logger.warning('Plugin delivery failed; no callback data logged')
        if delivery.attempts >= 6 or (event and now - event.created_at >= timedelta(days=1)):
            outcome = 'failed' if outcome == 'pending' else outcome
        PluginDelivery.query.filter_by(id=delivery.id, lease_token=lease, status='sending').update({
            'status': outcome, 'last_status': status_code, 'lease_token': None, 'lease_until': None,
            'next_attempt_at': datetime.utcnow() + timedelta(seconds=min(3600, 30 * 2 ** min(delivery.attempts, 7)))
        }, synchronize_session=False)
        db.session.commit()
        processed += 1
    # Bounded retention. Keep spent refresh tokens through the family lifetime to detect reuse.
    PluginToken.query.filter(PluginToken.expires_at < now,
        or_(PluginToken.refresh_expires_at.is_(None), PluginToken.refresh_expires_at < now)).delete(synchronize_session=False)
    PluginCode.query.filter(PluginCode.expires_at < now).delete(synchronize_session=False)
    old = db.select(PluginEvent.id).where(PluginEvent.created_at < now - timedelta(days=14))
    PluginDelivery.query.filter(PluginDelivery.event_id.in_(old)).delete(synchronize_session=False)
    PluginEvent.query.filter(PluginEvent.created_at < now - timedelta(days=14)).delete(synchronize_session=False)
    from .models import PluginAudit
    PluginAudit.query.filter(PluginAudit.created_at < now - timedelta(days=90)).delete(synchronize_session=False)
    db.session.commit()
    return processed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    from .. import create_app
    from ..config import Config
    class WorkerConfig(Config):
        PREPARE_DATABASE = False
        PUSH_ENABLED = False
        MAIL_POLLING_ENABLED = False
    app = create_app(WorkerConfig)
    while True:
        with app.app_context():
            try:
                run_once()
            except Exception:
                db.session.rollback()
                app.logger.error('Plugin worker cycle failed; check database and migration status')
                if args.once:
                    raise
            finally:
                db.session.remove()
        if args.once:
            break
        time.sleep(5)


if __name__ == '__main__':
    main()
