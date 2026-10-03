"""Migrate the database (create_app runs prepare_database) and report whether setup is needed.

The administrator is created via the web setup form on first launch.
"""
from app import create_app
from app.models.user import User


def seed_admin():
    if User.query.first() is not None:
        print('[ZenCRM] Baza danych gotowa. Istniejący użytkownicy znalezieni.')
        return False
    print('[ZenCRM] Nowa instalacja. Otwórz CRM w przeglądarce, aby utworzyć konto administratora.')
    return True


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        seed_admin()
