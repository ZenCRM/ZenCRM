<div align="center">

<img src="frontend/logo.png" alt="ZenCRM" width="240">

# ZenCRM

**Mniej chaosu. Więcej relacji. Wszystko w jednym CRM.**  
**Less chaos. Stronger relationships. Everything in one CRM.**

Samodzielnie hostowany CRM do sprzedaży, projektów, dokumentów i obsługi klienta.  
A self-hosted CRM for sales, projects, documents, and customer support.

[![Demo](https://img.shields.io/badge/LIVE_DEMO-TRY_ZENCRM-16a34a?style=for-the-badge)](https://zencrmdemo.tw5.org/)
[![Docker](https://img.shields.io/badge/DOCKER-HUB-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://hub.docker.com/r/kosiorekmateusz/zencrm)
[![Release](https://img.shields.io/github/v/release/ZenCRM/ZenCRM?style=for-the-badge)](https://github.com/ZenCRM/ZenCRM/releases/latest)

[Polski](#polski) · [English](#english) · [Galeria / Gallery](#galeria--gallery) · [Zgłoś błąd / Report an issue](https://github.com/ZenCRM/ZenCRM/issues)

</div>

---

## Galeria / Gallery

Zrzuty pochodzą z katalogu <code>screens/</code>. Kliknij obraz, aby otworzyć go w pełnym rozmiarze.  
Screenshots are stored in <code>screens/</code>. Click an image to open it at full size.

| Classic — pulpit / dashboard | Modern — pulpit / dashboard |
| :---: | :---: |
| [![Pulpit ZenCRM w szablonie Classic / Classic dashboard](screens/normaltheme-dashboard.png)](screens/normaltheme-dashboard.png) | [![Pulpit ZenCRM w szablonie Modern / Modern dashboard](screens/modern-dashboard.png)](screens/modern-dashboard.png) |
| **Classic — karta klienta / client record** | **Modern — karta klienta / client record** |
| [![Karta klienta w szablonie Classic / Classic client record](screens/normaltheme-client.png)](screens/normaltheme-client.png) | [![Karta klienta w szablonie Modern / Modern client record](screens/modern-client.png)](screens/modern-client.png) |

**Zadania w Kanban / Tasks in Kanban**

[![Tablica Kanban zadań ZenCRM / ZenCRM task Kanban board](screens/normaltheme-canban.png)](screens/normaltheme-canban.png)

---

## Polski

### Jeden system od pierwszego kontaktu do obsługi po sprzedaży

ZenCRM łączy dane klientów, leady, zadania, projekty, komunikację i helpdesk. Przykładowy przebieg pracy to **lead → oferta → klient → projekt lub usługa → obsługa zgłoszeń**. Każdy moduł może też działać samodzielnie, zgodnie z procesem zespołu.

| 📱 **TWOJE POŁĄCZENIA I SMS-Y PROSTO W CRM** |
| :--- |
| Koniec z ręcznym przepisywaniem historii kontaktów. Połącz swój telefon Android z ZenCRM, a zsynchronizowane połączenia i SMS-y z klientem pojawią się w jego karcie. Możesz też zlecić połączenie lub wysłać wiadomość bezpośrednio z CRM. **Nie potrzebujesz Twilio ani zewnętrznej bramki SMS** — wiadomości obsługuje Twój telefon z kompatybilną aplikacją mobilną. |

### Dwa szablony interfejsu

| Szablon | Wygląd i zastosowanie |
| --- | --- |
| **Classic — domyślny** | Jasny, uporządkowany układ z tradycyjną nawigacją i kartami rekordów. |
| **Modern** | Ciemny sidebar z delikatnym gradientem, szerszy obszar treści, odświeżone listy i Kanban oraz stonowane zdjęcia gór, lasów lub wybrzeża w nagłówkach rekordów. Tło można wybrać albo losować z kilku wariantów. |

Szablon wybierzesz w **Ustawienia → Szablony wyglądu**. Oba współpracują z trybem jasnym i ciemnym. Zrzuty obu wersji znajdziesz w [galerii](#galeria--gallery).

### Co potrafi ZenCRM?

| Obszar | Funkcje |
| --- | --- |
| **Pulpit** | Liczniki klientów, leadów, projektów, zadań i usług, wykresy lejka oraz skróty do codziennych działań. |
| **Klienci i kontakty** | Dane firm i osób, opiekunowie, powiązane kontakty, pliki, notatki i historia aktywności w jednej karcie. |
| **Leady** | Etapy sprzedaży, wartość i prawdopodobieństwo, widok tabeli i Kanban, konwersja leada na klienta oraz źródła i webhook leadów. |
| **Projekty** | Statusy, etapy, członkowie, powiązania z klientami, zadania i pliki projektu. |
| **Zadania** | Lista i Kanban, priorytety, terminy, postęp oraz przypisanie wielu wykonawców. |
| **Kalendarz i spotkania** | Widok miesiąca i plan dnia, spotkania oraz terminy powiązane z pracą zespołu. |
| **Usługi** | Katalog usług i obsługa konkretnych realizacji przypisanych do klientów i pracowników. |
| **Oferty i dokumenty** | Szablony, podgląd, generowanie PDF, typy dokumentów z własnymi polami i publiczne linki oparte na tokenie. |
| **Telefonia i SMS** | Telefony przypisane do użytkowników, synchronizacja połączeń i wiadomości, wątki SMS, statystyki oraz zlecanie akcji na telefonie. |
| **E-mail** | Konfiguracja SMTP i szablony wiadomości używanych przez CRM. |
| **Tickety i helpdesk** | Zgłoszenia, kategorie, reguły przydziału, publiczna strona pomocy oraz komunikacja w ramach ticketu. |
| **Portal klienta** | Oddzielne logowanie, członkowie portalu, udostępniane moduły i wygląd przestrzeni klienta. |
| **Powiadomienia** | Aktywność przy rekordach, przypomnienia oraz opcjonalne powiadomienia push w przeglądarce. |
| **Administracja** | Role, zespoły, uprawnienia, pola własne, wymagane pola, konfiguracja menu, branding, archiwum i przywracanie rekordów. |
| **Języki** | Polski i angielski w zestawie; administrator może utworzyć nowy język i edytować tłumaczenia. |
| **Aktualizacje** | Porównanie zainstalowanej wersji z najnowszym stabilnym wydaniem GitHub i dostęp do opisów wydań. |

### Generowanie ofert i dokumentów

| 📄 **SZABLON → PODGLĄD → PDF → LINK DO UDOSTĘPNIENIA** |
| :--- |
| Przygotuj ofertę lub dokument na własnym szablonie, uzupełnij dane z CRM i wygeneruj PDF bez przepisywania informacji. Gotowy materiał można pobrać albo udostępnić przez link z indywidualnym tokenem. |

1. Przygotuj szablon w edytorze i sprawdź jego podgląd. Dokumenty mogą korzystać z konfigurowalnych typów i dodatkowych pól.
2. Utwórz ofertę lub dokument i powiąż go z właściwym klientem, a w razie potrzeby także z leadem lub usługą.
3. Wygeneruj podgląd i plik PDF. Gotowy materiał możesz pobrać albo udostępnić przez indywidualny link z tokenem.

Szablony i dane biznesowe pozostają w Twojej instalacji. Generowanie PDF wykorzystuje Jinja2 oraz biblioteki PDF zainstalowane po stronie serwera.

### Telefonia i SMS w praktyce

W **Telefonia & SMS** dodajesz urządzenie i łączysz je z aplikacją Android współpracującą z bramką CRM (SMS Manager / GoFlow) za pomocą indywidualnego tokenu. Aplikacja działa w tle telefonu i synchronizuje historię połączeń oraz wiadomości. ZenCRM wiąże ją z klientami, leadami i kontaktami po numerze telefonu. Z ich kart możesz przejrzeć wcześniejszy kontakt oraz zlecić wykonanie połączenia lub wysłanie SMS-a przez podłączony telefon. Dostęp do urządzeń i wysyłania jest powiązany z zalogowanym użytkownikiem.

### Aktualizacje i tłumaczenia

| 🔄 **AUTOMATYCZNE SPRAWDZANIE NOWYCH WYDAŃ** |
| :--- |
| Po wejściu w **Ustawienia → Aktualizacja** ZenCRM pobiera listę wydań GitHub i porównuje najnowszą stabilną wersję z wersją instalacji. Widzisz opis zmian i odnośnik do wydania. Wdrożenie nowej wersji wykonuje administrator. |

Zakładka **Ustawienia → Aktualizacja** automatycznie pobiera informacje o wydaniach z [GitHub Releases](https://github.com/ZenCRM/ZenCRM/releases) po jej otwarciu. Pokazuje wersję instalacji, najnowsze stabilne wydanie i opis zmian. **Instalacja aktualizacji nie odbywa się samoczynnie**: administrator wdraża wybrane wydanie zgodnie ze sposobem instalacji, po wykonaniu kopii danych.

W **Ustawienia → Tłumaczenia** można poprawiać polskie i angielskie teksty oraz utworzyć język na podstawie polskiego lub angielskiego. Własne wpisy są przechowywane w bazie i mają pierwszeństwo przed tekstami dostarczonymi z aplikacją. Brakujące frazy korzystają z języka bazowego, więc nowe teksty dodane wraz z wydaniem pojawiają się bez ręcznego kopiowania całego katalogu.

### Szybki start: Docker Compose

Wymagane są Docker i Docker Compose. Plik [docker-compose.yml](docker-compose.yml) używa obrazu [kosiorekmateusz/zencrm](https://hub.docker.com/r/kosiorekmateusz/zencrm). Przed uruchomieniem ustaw własne, różne wartości <code>SECRET_KEY</code> i <code>JWT_SECRET_KEY</code>.

~~~bash
docker compose pull zencrm
docker compose up -d --no-build zencrm
~~~

Otwórz **http://localhost/**. Przy pierwszym uruchomieniu w przeglądarce pojawi się formularz utworzenia administratora. Skrypt startowy przygotowuje bazę automatycznie; nie tworzy konta z domyślnym hasłem. Wolumen <code>zencrm_data</code> przechowuje bazę, a <code>zencrm_uploads</code> przesłane pliki.

Aby wdrożyć nowszy obraz po wykonaniu kopii danych:

~~~bash
docker compose pull zencrm
docker compose up -d --no-build zencrm
~~~

Wolumeny pozostają zachowane. Do przewidywalnych wdrożeń możesz zamiast <code>latest</code> wskazać konkretny tag obrazu, na przykład <code>0.9.0.2</code>.

### Uruchomienie lokalne

Wymagany jest **Python 3.11 lub nowszy**. Frontend jest serwowany przez Flask i nie wymaga osobnego procesu budowania. Linux może wymagać bibliotek systemowych do PDF, wymienionych w [Dockerfile](Dockerfile).

**Windows PowerShell**

~~~powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
$env:PORT = "5000"
python run.py
~~~

**Linux / macOS**

~~~bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
PORT=5000 python run.py
~~~

W pliku <code>.env</code> zastąp przykładowe sekrety własnymi. Otwórz **http://localhost:5000/** i utwórz administratora w formularzu pierwszego uruchomienia. <code>run.py</code> służy do pracy lokalnej i włącza tryb debugowania Flask; wdrożenie kontenerowe używa Gunicorn.

### Konfiguracja, dane i bezpieczeństwo

| Zmienna | Znaczenie |
| --- | --- |
| <code>SECRET_KEY</code> | Sekret aplikacji Flask. |
| <code>JWT_SECRET_KEY</code> | Oddzielny sekret tokenów logowania. |
| <code>DATABASE_URL</code> | Adres bazy SQLAlchemy; domyślnie SQLite. |
| <code>PORT</code> | Port serwera; lokalnie w przykładach 5000, w Compose 80. |
| <code>ZENCRM_VERSION</code> | Opcjonalny identyfikator wersji; obraz Docker ustawia go podczas budowania. |

Przed wdrożeniem nowej wersji wykonaj kopię bazy i katalogu przesłanych plików. Aplikacja tworzy brakujące tabele i uzupełnia część starszych schematów przy starcie. Instalację dostępną przez Internet uruchamiaj przez HTTPS i chroń sekrety.

### Dokumentacja i współpraca

| Materiał | Zawartość |
| --- | --- |
| [Przewodnik użytkownika](docs/uzytkownik.md) | Praca z klientami, leadami, projektami, portalem i powiadomieniami. |
| [Dokumentacja API](docs/api.md) | Logowanie, endpointy i przykładowe żądania. |
| [Opis frontendu](frontend/README.md) | Widoki, moduły JavaScript i katalogi językowe. |
| [Najnowsze wydanie](https://github.com/ZenCRM/ZenCRM/releases/latest) | Opis zmian i dostępne tagi. |

Błędy i pomysły zgłaszaj przez [GitHub Issues](https://github.com/ZenCRM/ZenCRM/issues). Zmiany można proponować przez pull request.

---

## English

### One system from first contact to after-sales support

ZenCRM brings customer records, leads, tasks, projects, communication, and support together. A typical workflow is **lead → offer → client → project or service → support**, while each module can also be used on its own.

| 📱 **YOUR CALLS AND TEXTS, RIGHT IN THE CRM** |
| :--- |
| Stop copying contact history by hand. Connect your Android phone to ZenCRM and synchronized calls and texts with a client appear on their record. You can also request a call or send a message from the CRM. **No Twilio or external SMS gateway is needed** — your phone handles messaging through a compatible mobile app. |

### Two interface templates

| Template | Appearance |
| --- | --- |
| **Classic — default** | A light, structured layout with familiar navigation and record cards. |
| **Modern** | A dark sidebar with a subtle gradient, a wider content area, refined lists and Kanban, and muted mountain, forest, or coast photos behind record headers. Choose a photo or rotate among several backgrounds. |

Select a template under **Settings → Appearance templates**. Both work with light and dark mode. See the [gallery](#galeria--gallery) for screenshots of each template.

### What can ZenCRM do?

| Area | Features |
| --- | --- |
| **Dashboard** | Counts for clients, leads, projects, tasks, and services, pipeline charts, and shortcuts to frequent actions. |
| **Clients and contacts** | Company and person details, account owners, linked contacts, files, notes, and activity history in one record. |
| **Leads** | Sales stages, value and probability, table and Kanban views, lead conversion, lead sources, and a lead webhook. |
| **Projects** | Statuses, stages, members, client links, tasks, and project files. |
| **Tasks** | List and Kanban, priorities, due dates, progress, and multiple assignees. |
| **Calendar and meetings** | Month view and daily agenda for meetings and team deadlines. |
| **Services** | A service catalog and individual client deliveries assigned to team members. |
| **Offers and documents** | Templates, preview, PDF generation, document types with custom fields, and token-based public links. |
| **Telephony and SMS** | User-owned phones, synchronized calls and messages, SMS threads, statistics, and actions queued to a phone. |
| **Email** | SMTP configuration and email templates used by the CRM. |
| **Tickets and helpdesk** | Requests, categories, assignment rules, a public help page, and conversations within tickets. |
| **Customer portal** | Separate login, portal members, shared modules, and workspace appearance. |
| **Notifications** | Record activity, reminders, and optional browser push notifications. |
| **Administration** | Roles, teams, permissions, custom and required fields, menu configuration, branding, archive, and restore. |
| **Languages** | Polish and English included; administrators can create languages and edit translations. |
| **Updates** | Compare the installed version with the latest stable GitHub release and read release notes. |

### Generate offers and documents

| 📄 **TEMPLATE → PREVIEW → PDF → SHAREABLE LINK** |
| :--- |
| Prepare an offer or document from your template, fill it with CRM data, and generate a PDF without copying information by hand. Download the result or share it using a link with an individual token. |

1. Create a template in the editor and review its preview. Documents can use configurable types and extra fields.
2. Create an offer or document and link it to a client, and where relevant to a lead or service.
3. Generate a preview and PDF. Download the result or share it using an individual token-based link.

Templates and business data stay in your installation. PDF generation uses Jinja2 and server-side PDF libraries.

### Telephony and SMS in practice

In **Telephony & SMS**, add a device and pair a compatible Android app (SMS Manager / GoFlow) with the CRM gateway using an individual token. The app runs in the background on your phone and synchronizes call and message history. ZenCRM links it to clients, leads, and contacts by phone number. From their records, you can review earlier conversations and request a call or send a text through the connected phone. Device access and sending permissions are tied to the signed-in user.

### Updates and translations

| 🔄 **AUTOMATIC RELEASE CHECKS** |
| :--- |
| Opening **Settings → Updates** fetches GitHub releases and compares the latest stable version with the installed version. The screen shows release notes and a link to the release. An administrator deploys the new version. |

Opening **Settings → Updates** automatically fetches releases from [GitHub Releases](https://github.com/ZenCRM/ZenCRM/releases). It shows the installed version, the latest stable release, and its notes. **The application does not install updates unattended**: an administrator deploys the chosen release using the installation method after backing up data.

Under **Settings → Translations**, you can edit Polish and English text or create a language based on either one. Custom entries are stored in the database and take precedence over bundled translations. Missing phrases fall back to the base language, so new text from later releases appears without copying the entire catalog by hand.

### Quick start: Docker Compose

Docker and Docker Compose are required. [docker-compose.yml](docker-compose.yml) uses the published [kosiorekmateusz/zencrm](https://hub.docker.com/r/kosiorekmateusz/zencrm) image. Before starting, set your own, distinct <code>SECRET_KEY</code> and <code>JWT_SECRET_KEY</code> values.

~~~bash
docker compose pull zencrm
docker compose up -d --no-build zencrm
~~~

Open **http://localhost/**. On the first launch, the browser displays a form to create the administrator. The entrypoint prepares the database automatically; it does not create an account with a default password. The <code>zencrm_data</code> volume stores the database and <code>zencrm_uploads</code> stores uploaded files.

To deploy a newer image after backing up your data:

~~~bash
docker compose pull zencrm
docker compose up -d --no-build zencrm
~~~

The volumes are retained. For predictable deployments, you can replace <code>latest</code> with a specific image tag such as <code>0.9.0.2</code>.

### Run locally

You need **Python 3.11 or newer**. Flask serves the frontend without a separate build step. On Linux, PDF generation may require the system libraries listed in the [Dockerfile](Dockerfile).

**Windows PowerShell**

~~~powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
$env:PORT = "5000"
python run.py
~~~

**Linux / macOS**

~~~bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
PORT=5000 python run.py
~~~

Replace the sample secrets in <code>.env</code> with your own. Open **http://localhost:5000/** and create the administrator through the first-run form. <code>run.py</code> is intended for local work and enables Flask debug mode; the container deployment uses Gunicorn.

### Configuration, data, and security

| Variable | Purpose |
| --- | --- |
| <code>SECRET_KEY</code> | Flask application secret. |
| <code>JWT_SECRET_KEY</code> | Separate secret for login tokens. |
| <code>DATABASE_URL</code> | SQLAlchemy database URL; SQLite by default. |
| <code>PORT</code> | Server port; 5000 in the local examples and 80 in Compose. |
| <code>ZENCRM_VERSION</code> | Optional version identifier; the Docker image sets it at build time. |

Back up the database and uploaded files before deploying a new release. The application creates missing tables and updates some older schemas at startup. Use HTTPS for an Internet-facing installation and protect your secrets.

### Documentation and contributions

| Resource | Contents |
| --- | --- |
| [User guide (Polish)](docs/uzytkownik.md) | Clients, leads, projects, the portal, and notifications. |
| [API reference (Polish)](docs/api.md) | Login, endpoints, and example requests. |
| [Frontend notes (Polish)](frontend/README.md) | Views, JavaScript modules, and language catalogs. |
| [Latest release](https://github.com/ZenCRM/ZenCRM/releases/latest) | Release notes and available tags. |

Report bugs and ideas through [GitHub Issues](https://github.com/ZenCRM/ZenCRM/issues). Code changes can be proposed in a pull request.
