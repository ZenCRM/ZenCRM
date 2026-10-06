# Aplikacje i pluginy ZenCRM — API v1

Platforma umożliwia instalowanie aplikacji przez administratora, udostępnianie ich wskazanym użytkownikom i przyznawanie dostępu po osobistej zgodzie. Działa bez importowania kodu dostawcy do procesu CRM i bez przebudowy `crmApp`. Inspiracją są aplikacje lokalne Bitrix24: zakresy API, miejsca osadzenia, zgoda i zdarzenia. To własny kontrakt ZenCRM, bez zgodności protokołu z Bitrix24.

## Co jest zaimplementowane

- Aplikacje deklaratywne: manifest JSON i widżety z gotowych operacji CRM.
- Aplikacje zewnętrzne: interfejs na osobnej domenie HTTPS w ograniczonym iframe, własny backend dostawcy i opcjonalne odbieranie zdarzeń.
- Rejestracja, aktualizacja manifestu, zatwierdzanie zakresów i użytkowników, instalacja, włączenie, wyłączenie, odinstalowanie, osobista zgoda i jej cofnięcie.
- Tokeny osobiste na 1–30 dni (panel wydaje na 24 godziny), confidential authorization code + PKCE S256, rotacja refresh tokenów, wykrywanie ponownego użycia i unieważnianie całej rodziny.
- Wersjonowane, ograniczone operacje klientów, zadań, podsumowania i prywatnego storage; osobny endpoint tokenów aplikacji.
- Podpisane zdarzenia klientów, zapisane razem ze zmianą biznesową i wysyłane przez osobny worker. Dziennik administracyjny i stan dostarczeń.
- Panel **Aplikacje**: sklep z wyszukiwaniem i kategoriami, **Moje aplikacje** oraz osobna sekcja administracyjna. Widżety dashboardu i zakładka **Aplikacje** na karcie klienta. Etykiety PL/EN, układ mobilny i ciemny motyw.

## Preinstalowane aplikacje i sklep

Standardowy start bazy dodaje trzy aplikacje ZenCRM: **Podsumowanie pracy** (liczniki klientów i otwartych zadań, również na dashboardzie), **Katalog klientów** oraz **Lista zadań** (listy z wyszukiwaniem i paginacją). To lokalne deklaracje, bez pobierania paczek i uruchamiania kodu dostawcy. Wszystkie korzystają wyłącznie z zakresów odczytu.

Po włączeniu platformy aplikacje są preinstalowane i udostępnione aktywnym kontom, także utworzonym później. Samo preinstalowanie nie tworzy zgód ani tokenów. Użytkownik wybiera **Szczegóły**, sprawdza zakres i klika **Dodaj do moich aplikacji**; dopiero wtedy może otworzyć narzędzie. Administrator nadal może wyłączyć, odinstalować lub ograniczyć aplikację do konkretnych osób. Restart nie zmienia tych decyzji i nie przywraca odinstalowanych aplikacji.

`GET /api/plugins/store` wymaga aktywnego konta i włączonej platformy. Pokazuje oficjalne definicje lokalne (także niedostępne, bez możliwości aktywacji) oraz zewnętrzne aplikacje udostępnione danemu użytkownikowi. Nie ujawnia list użytkowników, konfiguracji ani zewnętrznych aplikacji spoza jego grupy dostępu. To katalog lokalny; nie ma zakupów, płatności ani pobierania z internetowego marketplace.

Definicje znajdują się w `app/plugins/bundled.py`. Identyfikatory `zencrm-work-summary`, `zencrm-client-directory`, `zencrm-task-list` są zarezerwowane. Manifesty są nieedytowalne w panelu, a status aplikacji ZenCRM wymaga dokładnej zgodności całej definicji; sama nazwa lub ID nie wystarcza. Wyłącznie dla takich definicji administrator może wybrać **Wszyscy aktywni użytkownicy, także nowe konta**. Instalacja API przyjmuje wtedy `all_users: true` i pustą `allowed_users`; baza przechowuje wewnętrzny znacznik `all-active-users`. Dla aplikacji zewnętrznych obowiązuje lista konkretnych osób.

Gmail, Google Drive, magazyn i pełny silnik raportów to kolejne aplikacje/moduły. Przykładowy raport to podsumowanie liczb, bez generatora PDF, harmonogramu i konstruktora raportów. Uwierzytelnianie 2FA należy rozbudować w rdzeniu logowania; plugin nie powinien przejmować uwierzytelniania CRM.

## Uruchomienie i wycofanie

1. Zrób i sprawdź backup bazy, katalogu `instance` z kluczami oraz uploadów. Najpierw wdrażaj na kopii testowej. Nie uruchamiaj nowego i starego obrazu jednocześnie na tej samej bazie podczas migracji.
2. Zbuduj obraz z tego PR. Migracja `20261006_plugins` dodaje dziewięć tabel i indeksy; nie zmienia tabel biznesowych. Standardowy `seed.py`/entrypoint wykonuje migracje pod istniejącą blokadą. Platforma jest początkowo wyłączona; administrator może ją włączyć w **Ustawienia → Aplikacje i pluginy**.
3. Ustaw rzeczywisty `PUBLIC_BASE_URL=https://crm.twoja-domena.pl`. Zachowaj stabilne `SECRET_KEY` i `JWT_SECRET_KEY` albo istniejący wspólny plik kluczy w `instance`. Ustaw zaufane proxy zgodnie z konfiguracją instalacji. CRM i aplikacje produkcyjne muszą działać przez HTTPS. `PLUGINS_ENABLED` określa tylko stan początkowy, dopóki administrator nie zapisze przełącznika w CRM. Zapis w bazie ma pierwszeństwo i działa bez restartu, także dla workera. `PLUGINS_LOCKED=true` jest osobną blokadą awaryjną serwera, której nie można obejść w panelu; w zwykłej instalacji pozostaje `false`.
4. Uruchom główny serwis z nowego obrazu: `docker compose up -d --build zencrm`. Dla zdarzeń uruchom dodatkowo `docker compose --profile plugins up -d --build plugin-worker`. Oba serwisy muszą używać tej samej wersji obrazu i tej samej bazy/kluczy. `depends_on` nie gwarantuje gotowości bazy; worker ponawia cykl po błędzie. Sprawdź logi pierwszego cyklu po migracji.
5. Administrator zaznacza **Włącz aplikacje i pluginy** w **Ustawienia → Aplikacje i pluginy** i zapisuje ustawienie. Następnie otwiera **Aplikacje**, wkleja manifest z `plugins/examples/reports/manifest.json`, rejestruje go, wybiera zakresy i użytkowników, zatwierdza instalację i włącza aplikację. Wskazany użytkownik akceptuje wymienione zakresy. Przykład działa bez serwera dostawcy i bez workera.
6. Dla aplikacji zewnętrznej zmień domeny w przykładowym manifeście. Wydaj sekrety przed przyznaniem zgód; zapisz je w backendzie aplikacji. Rotacja sekretów unieważnia dotychczasowe zgody/tokeny/subskrypcje. Udostępnij własną kopię `sdk.js`, ustaw `hostOrigin` i TLS. Backend dostawcy ma własną bazę oraz własne sekrety i limity zasobów; nie montuj mu `instance`, uploadów, Docker socket ani kluczy CRM.
7. Sprawdź scenariusze dwóch użytkowników, cofnięcie zgody, wyłączenie aplikacji, utratę przypisania klienta, opóźnienia odbiorcy i ponowienie zdarzeń. Dopiero potem udostępniaj kolejnym użytkownikom.

**Zatrzymanie:** globalny przełącznik w ustawieniach od razu blokuje nowe wywołania, zapis nowych zdarzeń i wysyłkę workera. Zachowuje zgody, tokeny, konfigurację i kolejkę, więc ponowne włączenie może wznowić dostęp i dostarczenia. Do trwałego cofnięcia uprawnień wyłącz konkretną aplikację w panelu (unieważnia tokeny/zgody i anuluje oczekujące zdarzenia). Awaryjnie ustaw `PLUGINS_LOCKED=true`, odtwórz kontenery API i workera albo zatrzymaj worker. Zmienna środowiskowa wymaga odtworzenia procesów. Nie używaj już `PLUGINS_ENABLED=false` jako blokady awaryjnej: zapisany przełącznik CRM ma przed nią pierwszeństwo. Żądanie lub dostarczenie rozpoczęte wcześniej może się zakończyć; odbiorca musi obsługiwać idempotencję.

Ustawieniem platformy zarządza administracyjny `GET/PUT /api/plugins/settings` (body `{"enabled":true}` lub `false`), dostępny również przy wyłączonej platformie. Zwykłe zapisy innych ustawień i reset ich wartości nie nadpisują tego przełącznika. Panel nie uruchamia serwisu workera; dla zdarzeń nadal potrzebny jest opisany profil Compose.

Odinstalowanie zachowuje manifest, konfigurację, storage i historię, aby nie niszczyć danych. Ponowna instalacja wymaga ponownej zgody. W v1 nie ma usuwania danych aplikacji z panelu ani migracji schematu dostawcy.

Stary obraz może odmówić uruchomienia z nowszą rewizją Alembic. Dla rollbacku zachowaj nowy obraz z wyłączoną funkcją albo przywróć sprawdzony backup sprzed migracji i poprzedni obraz. `alembic downgrade` usuwa tabele platformy i jej dane; wykonuj go tylko po zabezpieczeniu danych. Nie cofaj samego kodu przeciwko nowszej bazie.

## Granice dostępu

Każde wywołanie wymaga jednocześnie: aktywnej instalacji, włączenia globalnego i aplikacji, aktywnego użytkownika z zatwierdzonej grupy dostępu, aktualnej zgody, zgodności rewizji i zakresu należącego do manifestu, zatwierdzenia administratora oraz zgody użytkownika. Mutacje klientów dodatkowo wymagają `clients.edit` z istniejącego systemu ról i zespołów.

| Zakres | Operacje | Zasada |
| --- | --- | --- |
| `clients.read` | `clients.list`, `clients.get` | administrator widzi niearchiwalne rekordy; pozostali wyłącznie klientów przypisanych do siebie |
| `clients.write` | `clients.update` | ta sama widoczność i `clients.edit`; pola `name`, `email`, `phone`, `company` |
| `tasks.read` | `tasks.list` | administrator: niearchiwalne zadania; pozostali: przypisanie główne lub wykonawca |
| `reports.read` | `reports.summary` | liczby klientów, statusy i otwarte zadania w powyższym zakresie użytkownika |
| `storage` | `storage.get`, `storage.put`, `storage.delete` | osobno dla pary aplikacja–użytkownik, 100 kluczy po 8 KiB, CAS przez `revision` |
| `app.config` | `app.config.get` | wspólna konfiguracja tej aplikacji zatwierdzona przez administratora; bez sekretów |
| `events.clients` | endpoint subskrypcji | wymaga również `clients.read`; widoczność sprawdzana przy zapisie i przed wysyłką |

Przypisanie i role są sprawdzane ponownie; token nie jest trwałą kopią uprawnień. Zmiana hasła unieważnia tokeny i kody autoryzacyjne. Zgody/subskrypcje są osobnymi uprawnieniami aplikacji i nie wygasają razem z tokenem; użytkownik lub administrator może je cofnąć. Dezaktywacja/usunięcie konta blokuje także worker.

API zwraca tylko zadeklarowane pola. Prywatne notatki, dokumenty, poczta, inne tokeny, hasła, dowolne ścieżki HTTP i SQL są poza kontraktem. Uprawnienia menu nie stanowią polityki dostępu do API; w v1 obowiązuje powyższa, węższa polityka rekordów.

Administrator zatwierdza zaufanego dostawcę. Iframe chroni kontekst CRM, lecz aplikacja może skopiować dane, które użytkownik jawnie jej udostępnił. Brak arbitralnego kodu w rdzeniu nie stanowi gwarancji uczciwości zewnętrznego serwisu.

Storage zwraca `revision` jako nieprzezroczystą liczbę całkowitą bezpieczną dla JavaScript. Zawsze przekaż wersję odczytaną z API; dla nieistniejącego klucza użyj `0`. Nie zakładaj, że pierwsza wersja wynosi `1`: nowe klucze dostają losowy numer, aby usunięcie/odtworzenie klucza nie przyjmowało dawnej wersji CAS.

## Manifest i interfejs

Manifest ma maksymalnie 32 KiB; wersje kontraktu `manifest_version: 1`, `api_version: 1`; `version` jest wersją aplikacji `x.y.z`. Identyfikatory są stabilne i ograniczone do małych liter/cyfr/myślników. Nieznane pola i zakresy są odrzucane. Maksymalnie 8 miejsc osadzenia, 5 dokładnych URI powrotu i 100 aplikacji.

Miejsca: `app.page`, `dashboard.widget`, `client.detail.tab`. Deklaratywny widżet obsługuje `reports.summary`, `clients.list`, `tasks.list`, a wynik renderuje jako bezpieczny tekst JSON. Zewnętrzny widżet wskazuje HTTPS URL na osobnej domenie; manifest nie wstrzykuje HTML, JavaScript, CSS ani metod `crmApp`.

SDK dostawcy:

```javascript
const app = ZenPlugin({hostOrigin: 'https://crm.twoja-domena.pl'});
const context = await app.ready();
const client = await app.call('clients.get', {id: context.entity_id});
const old = await app.call('storage.get', {key: 'preferences'});
await app.call('storage.put', {key: 'preferences', value: {compact: true}, revision: old.revision});
await app.resize(400);
```

Host sprawdza dokładny `origin`, okno źródłowe, losowy kanał i aktualną sesję. Do ramki trafia wyłącznie kontekst `app_id`, `slot`, `entity_id` oraz wynik dozwolonej operacji; JWT i sekrety CRM pozostają w hoście. Ramka nie ma prawa nawigacji nadrzędnej, popupów, kamery, mikrofonu, geolokalizacji ani schowka. Jej własna domena jest dostępna przez `allow-same-origin`; nie wolno hostować jej na domenie CRM. Logout, zmiana widoku/rekordu i odświeżenie zgód zamykają kanał. Każde wywołanie nadal przechodzi przez backend. Limit mostka: 8 operacji równolegle, 32 KiB komunikatu, 1000 identyfikatorów żądań na osadzenie; po wyczerpaniu odśwież widżet. SDK ma timeout odpowiedzi 15 s.

## API aplikacji i autoryzacja

Zarządzanie i zgody: `/api/plugins/*` z **JWT CRM**. Integracje: `/api/plugin-api/v1/*` wyłącznie z **tokenem aplikacji**. Token aplikacji nie otwiera zwykłych endpointów CRM; JWT CRM nie otwiera endpointu integracji. Tokeny przyjmowane są tylko przez `Authorization: Bearer`, nigdy w URL. W bazie przechowywane są hashe tokenów i client secret; sekret HMAC jest szyfrowany stabilnym `SECRET_KEY`. Sekrety zwracane są tylko w odpowiedzi na wydanie/rotację, bez logowania ich do audytu.

```http
POST /api/plugin-api/v1/call
Authorization: Bearer zenapp_...
Content-Type: application/json

{"operation":"clients.list","params":{"page":1,"limit":25,"search":"Firma"}}
```

Listy: maksymalnie 100 rekordów na stronę, 120/min na zgodę aplikacji/użytkownika (limit współdzielony w bazie między procesami). Wywołania z interfejsu: 120/min na użytkownika. Aktywnych tokenów: maksymalnie 50 na zgodę; subskrypcji zdarzeń: 300 na aplikację. Wybrane endpointy wydawania/rejestracji mają dodatkowe limity. JSON do 32 KiB (większe HTTP payloady odrzucane przed parsowaniem, powyżej 64 KiB), storage/konfiguracja do 8 KiB. `409` oznacza m.in. konflikt rewizji; ponownie odczytaj stan.

Zewnętrzny backend OAuth:

1. Generuje kryptograficznie losowe `state`, verifier PKCE (43–128 znaków), challenge SHA-256/base64url i wiąże je z sesją swojego użytkownika.
2. Kieruje użytkownika do `https://crm.twoja-domena.pl/?plugin_authorize=APP_ID&response_type=code&redirect_uri=ENCODED_URI&code_challenge=CHALLENGE&code_challenge_method=S256&state=STATE#plugins`.
3. Użytkownik loguje się do CRM, przyznaje zgodę aplikacji i wybiera **Połącz konto z aplikacją**. Host wydaje dwuminutowy, jednorazowy kod i przekierowuje tylko na dokładny URI z manifestu. Callback dostawcy weryfikuje `state`.
4. Backend dostawcy wykonuje `POST /api/plugin-api/v1/oauth/token`, JSON lub form-urlencoded: `grant_type=authorization_code`, `client_id`, `client_secret`, `code`, `redirect_uri`, `code_verifier`. Client secret zostaje na backendzie dostawcy. Access token: 15 minut; refresh token: maksymalnie 30 dni dla rodziny.
5. Odświeża przez ten sam endpoint z `grant_type=refresh_token`, `client_id`, `client_secret`, `refresh_token`. Atomowo zapisuje nową parę. Nie wysyła równoległych odświeżeń i nie ponawia starego refresh tokenu po niepewnym wyniku; ponowne użycie unieważnia rodzinę. Po błędzie wykonuje ponowną autoryzację użytkownika.

To ograniczony przepływ OAuth dla poufnych aplikacji z backendem. V1 nie implementuje public clients, implicit/device grants, discovery, dynamic client registration, OAuth scopes z parametrów URL ani federacji tożsamości. Google OAuth wykonuje osobno aplikacja dostawcy; token Google nie jest tokenem ZenCRM.

## Zdarzenia i eksploatacja

Backend aplikacji wywołuje `POST /api/plugin-api/v1/subscriptions` z `{"event":"client.updated.v1"}`; `DELETE` z takim samym body usuwa subskrypcję. Dozwolone: `client.created.v1`, `client.updated.v1`, `client.archived.v1`. Działają po instalacji, osobistej zgodzie i utworzeniu sekretów. Zmiana zgody/instalacji/manifestu/sekretów wymaga ponownego dodania subskrypcji.

Zdarzenia powstają przy tworzeniu/edycji przez API klientów, tworzeniu klienta podczas konwersji leada i webhooka leadów, edycji przez API pluginów oraz archiwizacji. Importy/skrypty wykonujące bezpośredni SQL i dowolne inne zapisy ORM nie są automatycznie instrumentowane. Przy dodawaniu nowej ścieżki zapisu należy jawnie wywołać `emit_client_event` w tej samej transakcji. Przywracanie i trwałe usuwanie nie emitują w v1 dodatkowych zdarzeń.

Payload zawiera jedynie `event_id`, `delivery_id`, `event`, `app_id`, `user_id`, `entity_id`, `occurred_at`; brak pełnego rekordu. Stan można pobrać przez API w aktualnym zakresie dostępu. Przykładowy odbiorca w `plugins/examples/remote/webhook.py` weryfikuje surowe bajty i deduplikuje w własnej bazie.

Nagłówki: `X-ZenCRM-Delivery`, `X-ZenCRM-Timestamp`, `X-ZenCRM-Signature: sha256=HEX`. Podpis: HMAC-SHA256 `timestamp + "." + raw_body`. Odbiorca sprawdza stałoczasowo podpis, zgodność delivery ID, app ID oraz okno czasu (np. 5 minut). Zegar serwerów musi być synchronizowany. Delivery ID i event ID pozostają stałe przy ponowieniu; operacje odbiorcy muszą być idempotentne.

Worker przejmuje rekord przez atomową dzierżawę 60 s, maksymalnie 20 na cykl. `2xx` kończy wysyłkę; `408`, `429`, `5xx` i błędy transportu są ponawiane z opóźnieniem do 6 prób/24 godzin; pozostałe statusy kończą jako `failed`. `3xx` nie jest śledzone. Nie ma gwarancji kolejności; możliwe ponowne dostarczenie po awarii pomiędzy odbiorem a zapisaniem potwierdzenia.

HTTPS callback używa walidacji publicznych adresów DNS oraz przypiętego IP połączenia i walidacji certyfikatu dla oryginalnej domeny. Prywatne/mieszane adresy DNS są odrzucane, bez przekierowań. Socket timeout 5 s i watchdog 10 s przerywają również powolny strumień nagłówków HTTP. DNS zależy od resolvera systemowego i nie może być przerwany przez zamknięcie socketu; po przekroczeniu budżetu nie nastąpi już połączenie. Callback pracuje w osobnym serwisie z limitami CPU/pamięci, poza obsługą żądania CRM. Resolver DNS i cały zewnętrzny proces aplikacji dostawcy nie mają twardego limitu czasu narzuconego przez CRM; stosuj sprawny resolver i ograniczenia wyjścia sieciowego na poziomie infrastruktury.

Kolejka oczekujących dostarczeń ma limit 10 000. Po jego przekroczeniu logowany jest błąd i nowe zdarzenie zostaje pominięte, aby zapis CRM mógł się zakończyć. Limit jest kontrolą pojemności, nie ścisłą rezerwacją globalną przy współbieżnych transakcjach. To świadomy tryb ograniczenia szkód; nie używaj v1 jako jedynej ewidencji księgowej/magazynowej. Stan dostarczeń w panelu oraz log `Plugin delivery queue full` wymagają monitoringu; brak automatycznej naprawy/replay z panelu.

Worker usuwa zakończone/niezakończone zdarzenia starsze niż 14 dni, audyt starszy niż 90 dni i wygasłe kody/tokeny; zużyte refresh tokeny zachowuje do końca życia rodziny, aby wykrywać replay. Bez działającego workera retencja nie zachodzi, także przy globalnym wyłączeniu. Przed wyłączeniem na dłużej zaplanuj utrzymanie danych i monitoruj rozmiar bazy.

## Rozwijanie platformy

Nowy zakres lub operacja wymaga jawnej implementacji `manifest.py`, `operations.py`, polityki widoczności i testów odmowy dostępu. Nie rejestruj dowolnych funkcji, tras ani SQL z manifestu. Kontrakt wersjonuj przez osobną wersję API; rozszerzenie zakresów wymaga ponownej instalacji i zgody. Dostawca wersjonuje i migruje własną bazę samodzielnie.

Przed udostępnieniem magazynu potrzebny jest model transakcji/ewidencji w CRM; przed Gmail/Drive należy dodać wąskie operacje, storage provider credentials w backendzie aplikacji i odpowiednie przepływy Google OAuth. Prywatna poczta wymaga osobnej polityki folderów/kont i nie może dziedziczyć administracyjnego odczytu klientów. 2FA wdrażaj przed integracjami przetwarzającymi wrażliwe dane jako funkcję rdzenia.

Podstawy projektu: [aplikacje lokalne Bitrix24](https://apidocs.bitrix24.com/local-integrations/local-apps.html), [miejsca osadzenia](https://apidocs.bitrix24.com/api-reference/widgets/index.html), [OAuth Security BCP — RFC 9700](https://www.rfc-editor.org/rfc/rfc9700), [PKCE — RFC 7636](https://www.rfc-editor.org/rfc/rfc7636).
