# ZenCRM

[Polski](#polski) · [English](#english)

## Polski

### O aplikacji

ZenCRM to aplikacja do zarządzania sprzedażą i obsługą klientów. Backend działa we Flasku, a interfejs Alpine.js jest serwowany przez tę samą aplikację. Frontend nie wymaga osobnego procesu budowania.

Główne możliwości:

- klienci, kontakty i leady z tablicą Kanban oraz konfigurowalnymi etapami;
- zadania, projekty, spotkania i kalendarz;
- usługi, katalog usług, oferty, dokumenty i szablony;
- tickety, portal klienta oraz rejestr działań i połączeń;
- dashboard z metrykami i wykresami;
- role, zespoły, uprawnienia, pola własne i archiwum;
- interfejs po polsku i angielsku, jasny i ciemny motyw.

### Instalacja lokalna

Wymagany jest **Python 3.11 lub nowszy**. Domyślna baza to SQLite. Node.js jest potrzebny wyłącznie do testów frontendu. Na Linuxie generowanie PDF przez WeasyPrint może wymagać bibliotek systemowych, takich jak Pango i HarfBuzz; ich lista znajduje się w `Dockerfile`.

W katalogu projektu wykonaj:

**Windows PowerShell**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

**Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

W `.env` zastąp przykładowe wartości `SECRET_KEY` i `JWT_SECRET_KEY` dwoma różnymi, długimi losowymi sekretami. Następnie utwórz pierwsze konto administratora i uruchom aplikację:

**Windows PowerShell**

```powershell
python seed.py
$env:PORT = "5000"
python run.py
```

**Linux / macOS**

```bash
python seed.py
PORT=5000 python run.py
```

Otwórz **http://localhost:5000/**. Skrypt `seed.py` tworzy konto `admin@zencrm.pl` z hasłem `admin123`, jeśli jeszcze nie istnieje. **Zmień hasło po pierwszym logowaniu.** `run.py` uruchamia serwer deweloperski Flask z włączonym debugowaniem. Jeśli nie ustawisz `PORT`, użyje portu 80.

### Instalacja przez Docker Compose

Plik `docker-compose.yml` uruchamia opublikowany obraz `kosiorekmateusz/zencrm:latest`. Przed startem wpisz w nim własne wartości `SECRET_KEY` i `JWT_SECRET_KEY`. Domyślnie aplikacja będzie dostępna na porcie 80:

```bash
docker compose up -d
docker compose exec zencrm python seed.py
```

Otwórz **http://localhost/**, zaloguj się kontem administratora podanym wyżej i od razu zmień hasło. Wolumen `zencrm_data` przechowuje bazę w `/app/instance`, a `zencrm_uploads` przesłane pliki w `/app/uploads`. Compose pobiera gotowy obraz; aby uruchomić własny kod po zmianach w repozytorium, zbuduj obraz lokalnie i wskaż go w konfiguracji Compose.

### Konfiguracja i dane

| Zmienna | Opis | Przykład |
| --- | --- | --- |
| `SECRET_KEY` | Sekret aplikacji Flask | losowy ciąg |
| `JWT_SECRET_KEY` | Sekret tokenów logowania | inny losowy ciąg |
| `DATABASE_URL` | Adres bazy SQLAlchemy | `sqlite:///zencrm.db` |
| `PORT` | Port serwera | `5000` lokalnie |

Przy uruchomieniu aplikacja tworzy brakujące tabele. Przed aktualizacją instalacji z danymi wykonaj kopię bazy i katalogu `uploads/` oraz sprawdź migracje w `migrations/`. Instalację dostępną z Internetu uruchamiaj za HTTPS i chroń sekrety z `.env`.

## English

### About the application

ZenCRM is an application for sales and customer service management. Its backend uses Flask, while the Alpine.js interface is served by the same application. The frontend has no separate build step.

Main features:

- clients, contacts, and leads with a Kanban board and configurable stages;
- tasks, projects, meetings, and a calendar;
- services, a service catalog, offers, documents, and templates;
- tickets, a customer portal, and an activity and call log;
- a dashboard with metrics and charts;
- roles, teams, permissions, custom fields, and an archive;
- Polish and English interfaces with light and dark themes.

### Local installation

You need **Python 3.11 or newer**. SQLite is the default database. Node.js is only needed for the frontend tests. On Linux, PDF generation with WeasyPrint may require system libraries such as Pango and HarfBuzz; see `Dockerfile` for the package list.

Run these commands from the project directory:

**Windows PowerShell**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

**Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

In `.env`, replace the sample `SECRET_KEY` and `JWT_SECRET_KEY` with two different, long random secrets. Then create the initial administrator account and start the application:

**Windows PowerShell**

```powershell
python seed.py
$env:PORT = "5000"
python run.py
```

**Linux / macOS**

```bash
python seed.py
PORT=5000 python run.py
```

Open **http://localhost:5000/**. If it does not exist yet, `seed.py` creates the account `admin@zencrm.pl` with password `admin123`. **Change this password after your first login.** `run.py` starts Flask's development server with debugging enabled. Without `PORT`, it listens on port 80.

### Docker Compose installation

The included `docker-compose.yml` uses the published `kosiorekmateusz/zencrm:latest` image. Set your own `SECRET_KEY` and `JWT_SECRET_KEY` values in that file before starting. The default host port is 80:

```bash
docker compose up -d
docker compose exec zencrm python seed.py
```

Open **http://localhost/**, sign in with the administrator account above, and change its password immediately. The `zencrm_data` volume stores the database in `/app/instance`; `zencrm_uploads` stores uploaded files in `/app/uploads`. Compose pulls a published image. To run changes from this repository, build a local image and reference it in your Compose configuration.

### Configuration and data

| Variable | Purpose | Example |
| --- | --- | --- |
| `SECRET_KEY` | Flask application secret | random string |
| `JWT_SECRET_KEY` | Login token secret | a different random string |
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///zencrm.db` |
| `PORT` | Server port | `5000` locally |

The application creates missing tables on startup. Before updating an installation with existing data, back up the database and `uploads/` directory and review the migrations in `migrations/`. Use HTTPS for an Internet-facing installation and protect the secrets in `.env`.

