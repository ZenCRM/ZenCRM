"""Tworzy domyślnego admina: admin@zencrm.pl / admin123"""
from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app()
with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='admin@zencrm.pl').first():
        u = User(email='admin@zencrm.pl', first_name='Admin',
                 last_name='Zen', role='admin')
        u.set_password('admin123')
        db.session.add(u)
        db.session.commit()
        print('✅ Admin utworzony: admin@zencrm.pl / admin123')
    else:
        print('ℹ️  Admin już istnieje')
