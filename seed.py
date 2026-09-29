"""Initialize database tables. Administrator is created via the web setup form on first launch."""
from app import create_app
from app.extensions import db
from app.models.user import User


def seed_admin():
    db.create_all()
    if User.query.first() is not None:
        print('[ZenCRM] Baza danych gotowa. Istniejący użytkownicy znalezieni.')
        return False
    print('[ZenCRM] Nowa instalacja. Otwórz CRM w przeglądarce, aby utworzyć konto administratora.')
    return True


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        seed_admin()
