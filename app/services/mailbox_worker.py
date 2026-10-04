"""Periodic server-side mail retrieval, with a database lease across workers."""
import threading
from datetime import datetime, timedelta
from sqlalchemy import or_
from flask import current_app
from ..extensions import db
from ..models.mailbox import Mailbox
from .mailbox_service import sync_inbox
from .mailbox_lock import claim_mailbox, release_mailbox


def sync_due(now=None):
    now = now or datetime.utcnow()
    due = or_(Mailbox.next_sync_at.is_(None), Mailbox.next_sync_at <= now)
    free = or_(Mailbox.sync_claim_until.is_(None), Mailbox.sync_claim_until <= now)
    ids = [row.id for row in Mailbox.query.filter(due, free).order_by(Mailbox.next_sync_at, Mailbox.id).limit(20)]
    for box_id in ids:
        token = claim_mailbox(box_id, now, due_only=True)
        if not token:
            continue
        box = db.session.get(Mailbox, box_id)
        if box is None:
            continue
        interval = box.sync_interval_minutes
        try:
            sync_inbox(box, claim_token=token)
        except Exception:
            db.session.rollback()
            # Do not log credentials, message data or provider exception text.
            current_app.logger.warning('Mailbox %s periodic sync failed; retry scheduled', box_id)
        finally:
            interval = Mailbox.query.with_entities(Mailbox.sync_interval_minutes).filter_by(id=box_id, sync_claim_token=token).scalar() or interval
            release_mailbox(box_id, token, datetime.utcnow() + timedelta(minutes=interval))
            db.session.remove()


def start_mail_worker(app):
    if app.testing or not app.config.get('MAIL_POLLING_ENABLED', True) or app.extensions.get('mail_worker'):
        return
    def run():
        while True:
            with app.app_context():
                try:
                    sync_due()
                except Exception:
                    db.session.rollback()
                    app.logger.warning('Mailbox polling cycle failed; will retry')
                finally:
                    db.session.remove()
            threading.Event().wait(30)
    worker = threading.Thread(target=run, name='zencrm-mail-polling', daemon=True)
    app.extensions['mail_worker'] = worker
    worker.start()
