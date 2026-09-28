<div align="center">

<img src="https://zencrm.pl/logow.png" alt="ZenCRM" width="240">

# ZenCRM

### Mniej chaosu. Więcej relacji. Wszystko w jednym CRM.

Sprzedaż, projekty i obsługa klienta — od pierwszego kontaktu po realizację usługi.

**Na Twoim serwerze. W Twoim języku. W rytmie Twojego zespołu.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1%2B-111827?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Alpine.js](https://img.shields.io/badge/Alpine.js-Frontend-8BC0D0?style=for-the-badge&logo=alpinedotjs&logoColor=black)](https://alpinejs.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](docker-compose.yml)

[Strona projektu](https://zencrm.pl) · [Instalacja](#instalacja-przez-docker-compose) · [Dokumentacja](#dokumentacja) · [Zgłoś błąd](https://github.com/ZenCRM/ZenCRM/issues)

[Polski](#polski) · [English](#english)

</div>

---

<a href="https://zencrm.pl/screens/1a.png">
  <img src="https://zencrm.pl/screens/1a.png" alt="ZenCRM — zrzut ekranu aplikacji do zarządzania sprzedażą i obsługą klientów" width="100%">
</a>

<p align="center"><sub>ZenCRM w akcji · Kliknij zrzut ekranu, aby zobaczyć go w pełnym rozmiarze.</sub></p>

## Polski

### Twoje centrum pracy z klientem

ZenCRM łączy informacje o klientach, proces sprzedaży i codzienną pracę zespołu. Prowadź leady na tablicy Kanban, przygotowuj oferty, planuj realizację i obsługuj zgłoszenia w jednej aplikacji.

- **Od leada do klienta** — konwersja szansy sprzedaży przenosi powiązane kontakty, zadania i dokumenty.
- **Wspólna praca, jasne przypisania** — projekty, zespoły i zadania ze statusem każdego wykonawcy.
- **Kontakt także po sprzedaży** — portal klienta, helpdesk i historia aktywności przy rekordach.
- **Własna instalacja** — Docker Compose lub Python, domyślnie z bazą SQLite.
- **Wygodny interfejs** — język polski i angielski oraz jasny i ciemny motyw.

### Możliwości

| Obszar | Co możesz zrobić |
| --- | --- |
| 🤝 **Klienci i kontakty** | Gromadź dane firm i osób, przypisuj opiekunów i przeglądaj historię współpracy. |
| 🎯 **Leady i Kanban** | Zarządzaj etapami sprzedaży, wartością szans i prawdopodobieństwem zamknięcia. |
| ✅ **Projekty i zadania** | Organizuj etapy pracy, członków projektu i zadania wielu wykonawców. |
| 📅 **Spotkania i kalendarz** | Planuj spotkania i przeglądaj terminy w kalendarzu. |
| 🛠️ **Usługi i katalog** | Utrzymuj katalog usług i prowadź konkretne realizacje z przypisanymi osobami. |
| 📄 **Oferty i dokumenty** | Pracuj na szablonach, generuj PDF i udostępniaj materiały przez linki z tokenem. |
| 🎫 **Helpdesk** | Obsługuj tickety, konfiguruj kategorie oraz reguły automatycznego przydziału. |
| 🌐 **Portal klienta** | Zarządzaj członkami portalu, udostępnianymi modułami i wyglądem przestrzeni. |
| 📱 **Telefonia i SMS** | Po podłączeniu urządzenia synchronizuj historię połączeń i wiadomości. |
| 📊 **Dashboard** | Sprawdzaj metryki i wykresy na pulpicie aplikacji. |
| ⚙️ **Administracja** | Zarządzaj rolami, zespołami, uprawnieniami, polami własnymi i archiwum. |

### Jak to się łączy?

```mermaid
flowchart LR
    A[Kontakt i lead] --> B[Proces sprzedaży]
    B --> C[Oferta]
    C --> D[Klient]
    D --> E[Projekt i usługi]
    E --> F[Obsługa i helpdesk]
```

Przykładowy przebieg pracy: od pozyskania kontaktu po obsługę po sprzedaży. Poszczególne moduły możesz wykorzystywać zgodnie z procesem swojego zespołu.

### Technologia

| Warstwa | Rozwiązanie |
| --- | --- |
| Backend | Python, Flask, SQLAlchemy, Flask-Migrate |
| Interfejs | Alpine.js, widoki Jinja, JavaScript i CSS |
| Baza danych | Domyślnie SQLite; połączenie konfigurowane przez `DATABASE_URL` |
| Logowanie do CRM | Tokeny JWT przez Flask-JWT-Extended |
| Dokumenty | Jinja2, WeasyPrint i xhtml2pdf |
| Uruchomienie w kontenerze | Docker Compose i Gunicorn |

Frontend jest serwowany przez Flask i **nie wymaga osobnego procesu budowania**. Node.js jest potrzebny wyłącznie do testów frontendu.

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

### Dokumentacja

| Materiał | Zawartość |
| --- | --- |
| [Przewodnik użytkownika](docs/uzytkownik.md) | Praca z modułami, portal klienta, role i powiadomienia. |
| [Dokumentacja API](docs/api.md) | Uwierzytelnianie, mapa endpointów i przykłady żądań. |
| [Frontend](frontend/README.md) | Struktura widoków, moduły JavaScript, tłumaczenia i testy. |
| [Dockerfile](Dockerfile) | Budowanie obrazu i zależności systemowe. |

### Praca nad projektem

Pobierz kod i przejdź do katalogu projektu, a następnie wykonaj kroki instalacji lokalnej:

```bash
git clone https://github.com/ZenCRM/ZenCRM.git
cd ZenCRM
```

Najważniejsze katalogi:

```text
ZenCRM/
├── app/               # Backend: API, modele, schematy i usługi
├── frontend/          # Widoki, moduły JavaScript, style i tłumaczenia
├── docs/              # Przewodnik użytkownika i dokumentacja API
├── migrations/        # Migracje bazy danych
├── tests/             # Testy backendu i frontendu
├── run.py             # Uruchomienie aplikacji
└── seed.py            # Utworzenie pierwszego administratora
```

Po instalacji zależności, w aktywnym środowisku Python, uruchom testy z katalogu głównego repozytorium:

```bash
python -m unittest discover -s tests
node tests/test_frontend.cjs
```

### Pomysły i współpraca

Masz pomysł na usprawnienie albo znalazłeś błąd? [Otwórz zgłoszenie](https://github.com/ZenCRM/ZenCRM/issues). Opisz oczekiwane zachowanie, kroki odtworzenia i środowisko uruchomienia; przy problemach z interfejsem dołącz zrzut ekranu bez danych klientów.

Zmiany w kodzie możesz zaproponować przez pull request. Dołącz opis rozwiązania i wyniki odpowiednich testów. Przy zmianach interfejsu pamiętaj o obu językach oraz jasnym i ciemnym motywie.

---

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


### Documentation & development

- [User guide (Polish)](docs/uzytkownik.md)
- [API reference (Polish)](docs/api.md)
- [Frontend guide (Polish)](frontend/README.md)

After installing dependencies, run `python -m unittest discover -s tests` and `node tests/test_frontend.cjs` from the repository root. Contributions and [issue reports](https://github.com/ZenCRM/ZenCRM/issues) are welcome.

---

<div align="center">

**ZenCRM · Zadbaj o relacje. Uporządkuj pracę.**

[Strona projektu](https://zencrm.pl) · [Zgłoszenia i pomysły](https://github.com/ZenCRM/ZenCRM/issues) · [Powrót na górę](#zencrm)

Jeśli ZenCRM przydaje się w Twojej pracy, zostaw ⭐ na GitHubie.

</div>