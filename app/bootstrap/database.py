"""Existing startup schema compatibility logic, preserved without migration changes.

Replace this only after testing upgrades from supported installation schemas.
"""
from ..extensions import db
from ..models import document_type, email_template


def initialize_database(app):
    with app.app_context():
        db.create_all()
        # create_all does not add columns to installations created before these features.
        with db.engine.begin() as conn:
            inspector = db.inspect(conn)
            if 'translation_languages' in inspector.get_table_names() and 'base_locale' not in {c['name'] for c in inspector.get_columns('translation_languages')}:
                conn.execute(db.text("ALTER TABLE translation_languages ADD COLUMN base_locale VARCHAR(16) NOT NULL DEFAULT 'pl'"))
            if 'created_by_id' not in {c['name'] for c in inspector.get_columns('attachments')}:
                conn.execute(db.text('ALTER TABLE attachments ADD COLUMN created_by_id INTEGER'))
            if 'document_type_key' not in {c['name'] for c in inspector.get_columns('templates')}:
                conn.execute(db.text('ALTER TABLE templates ADD COLUMN document_type_key VARCHAR(50)'))
        document_type.DocumentType.seed_defaults()
        try:
            with db.engine.connect() as conn:
                # tasks migrations
                res_t = conn.execute(db.text("PRAGMA table_info(tasks)")).fetchall()
                cols_t = [r[1] for r in res_t] if res_t else []
                if cols_t and 'project_id' not in cols_t:
                    conn.execute(db.text("ALTER TABLE tasks ADD COLUMN project_id INTEGER"))
                    conn.commit()

                res_meetings = conn.execute(db.text("PRAGMA table_info(meetings)")).fetchall()
                cols_meetings = [r[1] for r in res_meetings] if res_meetings else []
                if cols_meetings and 'lead_id' not in cols_meetings:
                    conn.execute(db.text("ALTER TABLE meetings ADD COLUMN lead_id INTEGER"))
                    conn.commit()

                # custom_fields migrations
                res_cf = conn.execute(db.text("PRAGMA table_info(custom_fields)")).fetchall()
                cols_cf = [r[1] for r in res_cf] if res_cf else []
                if cols_cf and 'required' not in cols_cf:
                    conn.execute(db.text("ALTER TABLE custom_fields ADD COLUMN required BOOLEAN DEFAULT 0"))
                    conn.commit()

                # sms_devices migrations
                res = conn.execute(db.text("PRAGMA table_info(sms_devices)")).fetchall()
                cols = [r[1] for r in res] if res else []
                if cols and 'user_id' not in cols:
                    conn.execute(db.text("ALTER TABLE sms_devices ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                    conn.commit()
                if cols and 'last_sync_at' not in cols:
                    conn.execute(db.text("ALTER TABLE sms_devices ADD COLUMN last_sync_at DATETIME"))
                    conn.commit()
                if cols and 'sync_from' not in cols:
                    conn.execute(db.text("ALTER TABLE sms_devices ADD COLUMN sync_from DATETIME"))
                    conn.commit()

                # sms_queue migrations
                res_q = conn.execute(db.text("PRAGMA table_info(sms_queue)")).fetchall()
                cols_q = [r[1] for r in res_q] if res_q else []
                if cols_q and 'action' not in cols_q:
                    conn.execute(db.text("ALTER TABLE sms_queue ADD COLUMN action VARCHAR(50) DEFAULT 'send_sms'"))
                    conn.commit()
                if cols_q and 'payload' not in cols_q:
                    conn.execute(db.text("ALTER TABLE sms_queue ADD COLUMN payload TEXT"))
                    conn.commit()
                if cols_q and 'client_id' not in cols_q:
                    conn.execute(db.text("ALTER TABLE sms_queue ADD COLUMN client_id INTEGER"))
                    conn.commit()
                if cols_q and 'user_id' not in cols_q:
                    conn.execute(db.text("ALTER TABLE sms_queue ADD COLUMN user_id INTEGER"))
                    conn.commit()
                if cols_q and 'error_message' not in cols_q:
                    conn.execute(db.text("ALTER TABLE sms_queue ADD COLUMN error_message TEXT"))
                    conn.commit()
                if cols_q and 'sent_at' not in cols_q:
                    conn.execute(db.text("ALTER TABLE sms_queue ADD COLUMN sent_at DATETIME"))
                    conn.commit()

                # phone_calls migrations
                res_c = conn.execute(db.text("PRAGMA table_info(phone_calls)")).fetchall()
                cols_c = [r[1] for r in res_c] if res_c else []
                if cols_c and 'call_time' not in cols_c:
                    conn.execute(db.text("ALTER TABLE phone_calls ADD COLUMN call_time DATETIME"))
                    conn.commit()
                if cols_c and 'client_id' not in cols_c:
                    conn.execute(db.text("ALTER TABLE phone_calls ADD COLUMN client_id INTEGER"))
                    conn.commit()
                if cols_c and 'note' not in cols_c:
                    conn.execute(db.text("ALTER TABLE phone_calls ADD COLUMN note TEXT"))
                    conn.commit()

                # sms_messages migrations
                res_m = conn.execute(db.text("PRAGMA table_info(sms_messages)")).fetchall()
                cols_m = [r[1] for r in res_m] if res_m else []
                if cols_m and 'message_time' not in cols_m:
                    conn.execute(db.text("ALTER TABLE sms_messages ADD COLUMN message_time DATETIME"))
                    conn.commit()
                if cols_m and 'client_id' not in cols_m:
                    conn.execute(db.text("ALTER TABLE sms_messages ADD COLUMN client_id INTEGER"))
                    conn.commit()

                # users migrations
                res_u = conn.execute(db.text("PRAGMA table_info(users)")).fetchall()
                cols_u = [r[1] for r in res_u] if res_u else []
                if cols_u and 'default_call_method' not in cols_u:
                    conn.execute(db.text("ALTER TABLE users ADD COLUMN default_call_method VARCHAR(20) DEFAULT 'link'"))
                    conn.commit()
                if cols_u and 'email_notifications' not in cols_u:
                    conn.execute(db.text("ALTER TABLE users ADD COLUMN email_notifications TEXT DEFAULT '{}'"))
                    conn.commit()

                # contacts migrations
                res_cnt = conn.execute(db.text("PRAGMA table_info(contacts)")).fetchall()
                cols_cnt = [r[1] for r in res_cnt] if res_cnt else []
                if cols_cnt and 'is_primary' not in cols_cnt:
                    conn.execute(db.text("ALTER TABLE contacts ADD COLUMN is_primary BOOLEAN DEFAULT 0"))
                    conn.commit()
        except Exception:
            pass

        try:
            email_template.EmailTemplate.seed_defaults()
        except Exception:
            pass
