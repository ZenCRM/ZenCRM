"""Web Push sender. Database leases make multiple WSGI workers safe."""
import base64
import json
import threading
import uuid
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy.exc import IntegrityError
from flask import current_app
from ..extensions import db
from ..models.push import PushIdentity, PushSubscription, PushDelivery
from ..models.reminder import Reminder
from ..models.task import Task
from ..models.user import User


def identity():
    row = db.session.get(PushIdentity, 1)
    if row is None:
        key = ec.generate_private_key(ec.SECP256R1())
        pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption()).decode()
        row = PushIdentity(id=1, private_key=pem)
        db.session.add(row)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            row = db.session.get(PushIdentity, 1)
    return serialization.load_pem_private_key(row.private_key.encode(), password=None)


def public_key():
    raw = identity().public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode()


def is_due(reminder, now):
    if not reminder or reminder.dismissed or reminder.remind_at > now:
        return False
    if reminder.task_id:
        task = db.session.get(Task, reminder.task_id)
        if not task or task.deleted_at or task.status == 'done':
            return False
    return True


def send_due():
    from pywebpush import webpush, WebPushException
    from py_vapid import Vapid02
    now = datetime.utcnow()
    subscriptions = PushSubscription.query.join(User, User.id == PushSubscription.user_id).filter(
        PushSubscription.enabled.is_(True), User.is_active.is_(True)).all()
    for sub in subscriptions:
        due = Reminder.query.filter(Reminder.user_id == sub.user_id, Reminder.dismissed.is_(False),
                                    Reminder.remind_at <= now).all()
        for reminder in due:
            if not is_due(reminder, now):
                continue
            match = dict(subscription_id=sub.id, reminder_id=reminder.id, scheduled_at=reminder.remind_at)
            if not PushDelivery.query.filter_by(**match).first():
                db.session.add(PushDelivery(**match))
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
    pending = PushDelivery.query.filter(PushDelivery.sent.is_(False), PushDelivery.next_attempt <= now).order_by(PushDelivery.id).limit(100).all()
    for delivery in pending:
        did = delivery.id
        lease = uuid.uuid4().hex
        claimed = PushDelivery.query.filter(PushDelivery.id == did, PushDelivery.sent.is_(False),
                                            PushDelivery.next_attempt <= now).update({
            'next_attempt': now + timedelta(seconds=90), 'lease': lease,
            'attempts': PushDelivery.attempts + 1}, synchronize_session=False)
        db.session.commit()
        if not claimed:
            continue
        delivery = db.session.get(PushDelivery, did)
        sub = db.session.get(PushSubscription, delivery.subscription_id)
        reminder = db.session.get(Reminder, delivery.reminder_id)
        user = db.session.get(User, sub.user_id) if sub else None
        if not sub or not sub.enabled or not user or not user.is_active or not is_due(reminder, now) or reminder.user_id != sub.user_id or reminder.remind_at != delivery.scheduled_at:
            delivery.sent = True
            db.session.commit()
            continue
        try:
            webpush(subscription_info=sub.subscription,
                    data=json.dumps({'title': 'Przypomnienie ZenCRM', 'body': reminder.title,
                                     'reminder_id': reminder.id, 'user_id': reminder.user_id,
                                     'tag': f'reminder-{reminder.id}', 'url': '/?reminder=' + str(reminder.id)}),
                    vapid_private_key=Vapid02(private_key=identity()),
                    vapid_claims={'sub': current_app.config['VAPID_SUBJECT']}, ttl=3600,
                    timeout=15, headers={'Urgency': 'high'})
            delivery.sent = True
        except WebPushException as error:
            code = error.response.status_code if error.response is not None else None
            if code in (404, 410):
                sub.enabled = False
                delivery.sent = True
            else:
                delivery.next_attempt = datetime.utcnow() + timedelta(seconds=min(3600, 30 * 2 ** min(delivery.attempts, 7)))
                current_app.logger.warning('Push delivery %s failed (HTTP %s); retry scheduled', did, code)
        except Exception:
            delivery.next_attempt = datetime.utcnow() + timedelta(minutes=1)
            current_app.logger.warning('Push delivery %s failed; retry scheduled', did)
        db.session.commit()
    # Remove only obsolete delivery receipts, keeping current schedules deduplicated.
    old_ids = [row.id for row in PushDelivery.query.filter(PushDelivery.scheduled_at < now-timedelta(days=30)).all()
               if not (r := db.session.get(Reminder, row.reminder_id)) or r.dismissed or r.remind_at != row.scheduled_at]
    if old_ids:
        PushDelivery.query.filter(PushDelivery.id.in_(old_ids)).delete(synchronize_session=False)
        db.session.commit()


def start_push_worker(app):
    if app.testing or not app.config['PUSH_ENABLED'] or app.extensions.get('push_worker'):
        return
    def run():
        while True:
            with app.app_context():
                try:
                    send_due()
                except Exception:
                    db.session.rollback()
                    app.logger.warning('Push worker cycle failed; will retry')
                finally:
                    db.session.remove()
            threading.Event().wait(10)
    worker = threading.Thread(target=run, name='zencrm-web-push', daemon=True)
    app.extensions['push_worker'] = worker
    worker.start()
