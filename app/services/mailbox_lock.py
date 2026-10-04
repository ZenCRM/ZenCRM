"""Atomic mailbox lease shared by manual and scheduled synchronization."""
import uuid
from datetime import datetime, timedelta
from sqlalchemy import or_
from ..extensions import db
from ..models.mailbox import Mailbox


class MailboxBusy(Exception):
    pass


def claim_mailbox(box_id, now=None, due_only=False):
    now = now or datetime.utcnow()
    token = str(uuid.uuid4())
    query = Mailbox.query.filter(Mailbox.id == box_id, or_(
        Mailbox.sync_claim_until.is_(None), Mailbox.sync_claim_until <= now))
    if due_only:
        query = query.filter(or_(Mailbox.next_sync_at.is_(None), Mailbox.next_sync_at <= now))
    changed = query.update({Mailbox.sync_claim_token: token,
        Mailbox.sync_claim_until: now + timedelta(minutes=5)}, synchronize_session=False)
    db.session.commit()
    return token if changed else None


def release_mailbox(box_id, token, next_sync_at=None):
    values = {Mailbox.sync_claim_token: None, Mailbox.sync_claim_until: None}
    if next_sync_at is not None:
        values[Mailbox.next_sync_at] = next_sync_at
    Mailbox.query.filter_by(id=box_id, sync_claim_token=token).update(values, synchronize_session=False)
    db.session.commit()
