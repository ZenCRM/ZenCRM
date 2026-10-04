# Audyt bezpieczeństwa CRM po dodaniu poczty — 4 października 2026

Wynik pierwotnego audytu: **1 problem o wysokim priorytecie (P1) i 4 problemy o średnim priorytecie (P2)**. Trzy dotyczą nowego modułu poczty; dwa istniały przed dzisiejszymi zmianami. Ustalenia odtworzono lokalnie przy użyciu bazy w pamięci i atrap transportu. Sam audyt nie zmieniał kodu ani nie wysyłał rzeczywistych wiadomości. Opis ustaleń poniżej dokumentuje stan przed naprawą.

## Poprawki wprowadzone po audycie

| Ustalenie | Zmiana |
| --- | --- |
| A1 | Błędne UID są trwale oznaczane `content_version=-1`, z bezpiecznym komunikatem. Poprawne wiadomości są zatwierdzane osobno; kolejny błąd nie wycofuje ich zapisu. Po odrzuceniu treści połączenie IMAP jest zamykane, a pozostałe UID przetwarzane w nowym połączeniu. |
| A2 | Ręczna i okresowa synchronizacja korzystają z tej samej atomowej blokady w bazie. Żądanie do zajętej skrzynki zwraca 409. Kosztowne żądania mają wspólny limit 12/min/użytkownika oraz maksymalnie dwa równoległe żądania HTTP na proces; zmiany odczytu mają limit 60/min. Transport IMAP ma termin 60 s oraz wspólny budżet odpowiedzi 64 MiB, także przy ponownych połączeniach. |
| A3 | Żądanie załącznika ma `AbortController`; wylogowanie je anuluje. Token i obiekt stanu są sprawdzane po odpowiedzi i odczycie blobu. Nieaktualna odpowiedź nie tworzy pobrania; użyte blob URL są zwalniane. |
| A4 | Renderowanie i walidacja szablonów odbywają się w osobnym procesie: 128 MiB pamięci, 2 s CPU, 3 s czasu rzeczywistego, 2 MiB wyniku. Windows używa Job Object, Unix limitów `resource`; brak możliwości ich ustawienia powoduje odmowę renderowania. Jeden renderer działa na proces aplikacji. Podgląd wymaga uprawnienia tworzenia lub edycji szablonów i ma limit 30/min/użytkownika. |
| A5 | `Setting.set_value` szyfruje hasło SMTP dla obu API ustawień. Odczyt transportu odszyfrowuje wersjonowany zapis; uszkodzone szyfrowanie nie jest traktowane jak jawne hasło. Przygotowanie aplikacji/`seed.py` migruje dotychczasowy zapis raz, pod istniejącą blokadą aktualizacji bazy. |

`MAILBOX_ENCRYPTION_KEY` jest teraz pobierany ze środowiska i sprawdzany pod kątem minimalnej długości 32 znaków. Puste ustawienie zachowuje dotychczasowy klucz `SECRET_KEY`. Osobny klucz nie zmienia klucza hasła SMTP powiadomień. Rotacja klucza wymaga migracji; istniejące backupy mogą zawierać poprzednie jawne hasło.

Dodano regresje w `tests/test_security_mail_fixes.py`, `tests/test_mail_attachment_session.cjs`, testach transportu i kluczy. Skrypty `tools/security_audit_20261004.py` i `.cjs` sprawdzają teraz bezpieczne zachowanie po naprawie. Nie są już próbami oczekującymi odtworzenia podatności.

Walidacja poprawek: pełny zestaw Python — 215 testów, wynik OK, 9 testów backupów pominięto z powodu braku wymaganych narzędzi CLI. Pełny frontend — 53/53, w tym cztery nowe testy pobierania załączników. Po końcowym uzupełnieniu transportu jego siedem testów przeszło. Sprawdzono, że błędny UID jest pomijany przy kolejnej próbie, zerwanie połączenia zachowuje wcześniejszy zapis, zajęta skrzynka zwraca 409, limit pracy zwraca 429, renderowanie przekraczające pamięć/CPU/rozmiar jest odrzucane, a kolejne poprawne renderowanie nadal działa. Migracja hasła SMTP przy przygotowaniu aplikacji przeszła i jest idempotentna; oba API ustawień zapisują szyfrogram, a odpowiedzi maskują sekret.

Test frontendu daty zadania korzystał z rzeczywistego zegara obok zamrożonego zegara komponentu. Dopasowano jego datę referencyjną do istniejącej fixture; kod działania zadań nie zmienił się. Kontrakt frontendu zaktualizowano wyłącznie dla dwóch celowo zmienionych metod: pobierania załącznika i wylogowania.

Końcowa regresja po ostatnich zmianach transportu: **46/46 testów poczty, transportu i napraw bezpieczeństwa**. Limity Job Object sprawdzono na Windows, również na kosztownych szablonach. Ścieżka Unix została przejrzana w kodzie; lokalny silnik Docker Linux był niedostępny, więc nie wykonano jej w kontenerze. Ograniczenie natywnych bibliotek WeasyPrint pozostaje takie jak w pierwotnym audycie. `git diff --check` nie wykazał błędów.

## Zakres i metoda

Przejrzano aktualny katalog roboczy, w tym niezacommitowane i nowe pliki, względem HEAD `6570f08`. Zakres obejmuje API skrzynek, IMAP/SMTP, automatyczne sprawdzanie poczty, szyfrowanie haseł, uprawnienia osobiste i zespołowe, powiązania z klientami, HTML/CSS wiadomości i stopek, załączniki, cykl sesji frontendu, edytor i podgląd szablonów, zmiany ustawień i profilu, migracje, globalne zabezpieczenia API oraz konfigurację obrazu i wdrożenia.

Istniejący `SECURITY_MAIL_REVIEW.md` potraktowano jako wcześniejszy opis, a nie dowód bezpieczeństwa. Aktualne zachowanie zweryfikowano niezależnie. Przegląd nie jest pełnym testem penetracyjnym wszystkich funkcji CRM.

## Ustalenia

### A1 — P1: pojedynczy e-mail blokuje synchronizację całej partii

**Kod:** `app/services/mailbox_service.py:156`, `app/services/mailbox_service.py:190`, `app/api/mailboxes.py:257`, `app/services/mailbox_worker.py:30`.

W pętli synchronizacji przekroczenie limitu 2 MiB przez jedną część tekstową powoduje wyjątek. Cała transakcja jest wycofywana, a pozostałe wiadomości nie są przetwarzane. Nie ma zapisu stanu „pominięta wiadomość” ani odrębnej obsługi błędów pojedynczego UID. Kolejny cykl odczytuje ponownie tę samą wiadomość i ponownie przerywa pracę.

**Warunek ataku:** zewnętrzny nadawca może dostarczyć wiadomość z częścią tekstową ponad limit do podłączonej skrzynki. Nie potrzebuje konta CRM. Wiadomość musi znajdować się w synchronizowanym oknie ostatnich 100 UID. Wystarczą też niektóre nieobsługiwane/błędne struktury MIME powodujące wyjątek.

**Dowód:** atrapa IMAP zwróciła poprawny UID 1, UID 2 z deklarowaną częścią tekstową 2 097 153 bajtów i poprawny UID 3. Dwie kolejne synchronizacje zwróciły HTTP 400; baza zawierała 0 wiadomości; UID 3 nie został odwiedzony. Nie alokowano dużego payloadu. Odtworzenie dowodzi także wycofania poprawnej wiadomości przetworzonej przed błędem.

**Skutek:** odbiór nowej poczty w CRM może być zablokowany do usunięcia problematycznej wiadomości z serwera albo jej wypadnięcia z ostatnich 100 UID. Pełna synchronizacja ponownie trafi na ten UID.

**Naprawa:** izolować zapis i błędy poszczególnych wiadomości; zapisywać pominięty UID z przyczyną i pozwalać kontynuować kolejne UID. Zachować limity pobierania. Jeśli odrzucenie literalu zostawia sesję IMAP w nieprawidłowym stanie, zakończyć połączenie i wznowić pozostałe UID w nowej sesji, bez ponawiania blokującej wiadomości w nieskończoność.

### A2 — P2: ręczna synchronizacja omija blokadę i nie ma limitu równoległych operacji

**Kod:** `app/api/mailboxes.py:242`, `app/api/mailboxes.py:254`, `app/services/mailbox_worker.py:15`, `app/services/mailbox_service.py:128`, `entrypoint.sh:26`.

Proces okresowy uzyskuje blokadę w bazie, ale endpoint `/api/mailboxes/<id>/sync` bezpośrednio wywołuje `sync_inbox`. Nie sprawdza ani nie uzyskuje tej blokady. `mail.busy` chroni tylko jeden stan interfejsu; nie chroni przed wieloma kartami, członkami zespołu lub bezpośrednimi żądaniami HTTP. Nie ma limitowania kosztownych żądań poczty na poziomie API.

**Dowód:** ustawiono aktywną blokadę skrzynki na kolejne 30 minut. Ręczne żądanie nadal zwróciło HTTP 200 i wywołało synchronizację. Odtworzenie potwierdza pominięcie blokady; nie wykonywano ataku obciążeniowego.

**Skutek:** równoległe odczyty tej samej skrzynki, ryzyko konfliktów unikalności i blokad SQLite, nadmiarowe pobrania oraz zajęcie wątków HTTP. Konfiguracja Gunicorn przewiduje 2 procesy po 4 wątki. Timeout 20 sekund dotyczy operacji sieciowych, a nie całego cyklu 100 wiadomości. `SEARCH ALL` dodatkowo pobiera listę wszystkich UID przy każdym żądaniu. Ryzyko wyczerpania zasobów wynika z tych ścieżek; jego skalę produkcyjną trzeba zmierzyć.

**Naprawa:** wspólna atomowa blokada dla pracy ręcznej i okresowej, odpowiedź 409/429 na ponowne uruchomienie, ograniczenie częstotliwości i liczby operacji na użytkownika/skrzynkę. Przenieść kosztowną pracę do kolejki z ograniczoną współbieżnością, limitem całkowitego czasu i budżetem pobieranych danych. Zalecenia odpowiadają [wytycznym OWASP dotyczącym DoS](https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html).

### A3 — P2: załącznik może zostać pobrany po wylogowaniu lub zmianie konta

**Kod:** `frontend/js/modules/mailboxes.js:184`, `frontend/js/modules/mailboxes.js:191`.

`downloadMailAttachment` wysyła żądanie z aktualnym tokenem, ale po oczekiwaniu na odpowiedź i blob nie weryfikuje tożsamości sesji. Wylogowanie zeruje stan poczty, lecz nie anuluje tego żądania. Spóźniona odpowiedź bezwarunkowo tworzy link i uruchamia pobranie.

**Dowód:** rozpoczęto żądanie w sesji A, zmieniono token na sesję B i zastąpiono stan poczty nowym obiektem, a następnie zwrócono atrapę odpowiedzi. Kod wykonał `link.click()` raz. Nie pobrano rzeczywistego pliku.

**Skutek:** na wspólnym komputerze załącznik poprzedniego użytkownika może zostać zapisany już podczas pracy kolejnego użytkownika. Wymaga rozpoczęcia pobierania przed zmianą sesji i opóźnionej odpowiedzi. Nie oznacza to obejścia autoryzacji API: serwer autoryzował pierwotne żądanie użytkownika A.

**Naprawa:** zachować token/generację sesji i sprawdzić je po każdym oczekiwaniu, przed tworzeniem URL i pobraniem. Powiązać żądania załączników z `AbortController`, anulować je przy wylogowaniu i zwalniać utworzone blob URL.

### A4 — P2: podgląd Jinja nie ogranicza zużycia pamięci i CPU

**Problem istniejący przed dzisiejszymi zmianami. Kod:** `app/api/templates.py:126`, `app/api/templates.py:133`, `app/services/render_service.py:66`.

Podgląd dostępny jest dla aktywnych, zalogowanych użytkowników także wtedy, gdy odebrano im uprawnienia tworzenia i edycji szablonów. Nie korzysta z nowej walidacji wielkości treści zapisanych szablonów. Renderowanie działa w procesie aplikacji i nie ma budżetu CPU/pamięci ani rozmiaru wynikowego HTML. Globalny limit żądania 21 MiB nie ogranicza ekspansji wyniku. `SandboxedEnvironment` blokuje niebezpieczny dostęp do obiektów, ale nie ogranicza zużycia zasobów, co wprost opisuje [dokumentacja Jinja](https://jinja.palletsprojects.com/en/stable/sandbox/).

**Dowód:** pracownik z `templates.create=false` i `templates.edit=false` otrzymał 403 przy zapisie, ale 200 przy podglądzie. Źródło `{{ 'x' * 1000000 }}` miało 19 znaków i wygenerowało 1 000 000 bajtów odpowiedzi. Próba była ograniczona do 1 MB; nie wykonywano renderowania zdolnego wyczerpać pamięć komputera.

**Skutek:** zalogowany użytkownik może zwiększać koszt renderowania niezależnie od wielkości źródła i obciążyć cały CRM. Brak uprawnień do zapisu szablonów nie usuwa tej możliwości. Nie stwierdzono wykonania kodu poza sandboxem.

**Naprawa:** dodać odpowiednie uprawnienie do podglądu, walidację wejścia i limitowanie wywołań. Renderować w odizolowanym procesie z twardymi limitami pamięci/czasu i ograniczać rozmiar wyniku. Samo obcięcie HTML po pełnym renderowaniu nie zapobiega wcześniejszej alokacji pamięci.

### A5 — P2: hasło SMTP powiadomień nadal jest zapisywane jawnie

**Problem istniejący przed dzisiejszymi zmianami. Kod:** `app/api/emails.py:124`, `app/api/emails.py:126`, `app/services/email_service.py:43`.

Nowe skrzynki szyfrują hasła Fernet, ale osobny moduł SMTP powiadomień zapisuje `smtp_password` bez szyfrowania w `settings.value`. Maskowanie odpowiedzi API nie chroni bazy ani jej kopii.

**Dowód:** zapis testowego hasła przez endpoint administratora zwrócił 200; odczyt z testowej bazy był identyczny z wejściowym hasłem. Użyto fikcyjnej wartości; nie odczytywano rzeczywistych sekretów CRM.

**Skutek:** osoba mająca dostęp do kopii bazy uzyskuje hasło SMTP powiadomień bez posiadania klucza aplikacji. Znaczenie zależy od tego, czy moduł jest skonfigurowany i jakie uprawnienia ma konto SMTP.

**Naprawa:** migrować istniejące wartości do szyfrowania, używać sekretu chronionego oddzielnie od kopii danych i obsługiwać rotację klucza. Zachować maskowanie i ograniczenie API do administratorów.

## Zabezpieczenia potwierdzone w sprawdzonym zakresie

- Globalna kontrola API wymaga ważnego JWT i aktywnego użytkownika; zmiana hasła unieważnia dotychczasowe tokeny.
- Osobiste skrzynki są izolowane również od pozostałych administratorów. Dostęp do zespołowych wymaga członkostwa; zarządzanie wymaga lidera lub administratora należącego do zespołu. Wiadomości, powiązania historii i załączniki są filtrowane według dostępnych skrzynek.
- Nowe hasła skrzynek nie są serializowane; szyfrowanie Fernet korzysta z klucza wyprowadzonego z sekretu. Zmiana nazwy hosta wymaga ponownego podania hasła.
- Nowy transport wymaga TLS z weryfikacją certyfikatu. Adresy DNS są sprawdzane przed połączeniem, a połączenie jest przypięte do sprawdzonego adresu. Testy obejmują prywatne IP, metadane chmurowe, multicast, adresy mapowane i sieci przejściowe IPv6.
- Odebrane HTML jest filtrowane; CSS blokuje zdalne odwołania. Iframe wiadomości i stopek ma sandbox bez skryptów i bez `allow-same-origin` oraz CSP. Zdalne obrazy odebranej poczty wymagają świadomego włączenia. Jest to ocena kodu i testów; w tym audycie nie wykonywano ponownej próby w prawdziwej przeglądarce.
- Temat i adresy wysyłki blokują CR/LF; UDW trafia do koperty SMTP bez nagłówka Bcc. Odpowiedzi/przekazania muszą wskazywać wiadomość z tej samej skrzynki.
- Załączniki pobierane są na żądanie, z kontrolą właściciela, identyfikatora części, limitu literału i nagłówkiem pobrania. Nie są automatycznie wykonywane.
- HTML błędów podglądu szablonu jest escapowany. Renderowanie PDF ogranicza zasoby do `data:`; testy bezpieczeństwa ścieżki zapasowej przeszły.
- Obraz wyklucza `.env`, lokalne bazy i uploady; proces startowy przechodzi na użytkownika bez uprawnień root.

## Dodatkowe uwagi operacyjne

Treści i metadane poczty zwiększają ilość poufnych danych w bazie oraz backupach. Kopia `security.sqlite` lub sekret aplikacji razem z zaszyfrowanymi hasłami umożliwiają ich odszyfrowanie; backup wymaga osobnej ochrony. Nie sprawdzano uprawnień rzeczywistych backupów.

`MAILBOX_ENCRYPTION_KEY` jest obsługiwany przez usługę jako opcja konfiguracji Flask, ale `Config` nie pobiera go ze zmiennej środowiskowej. Samo ustawienie takiej zmiennej w zwykłym wdrożeniu nie przełączy klucza — nadal używany będzie `SECRET_KEY`. Należy udokumentować rzeczywistą konfigurację i przygotować migrację przed rotacją sekretu. Nie potwierdzono, aby aktualne wdrożenie zakładało użycie osobnego klucza.

Stary moduł SMTP powiadomień dopuszcza tryb `none`; administrator może więc skonfigurować logowanie i wysyłkę bez TLS. Nowy moduł skrzynek nie dopuszcza tego trybu. Nie sprawdzano faktycznego ustawienia produkcyjnego. Podstawowy Compose publikuje HTTP; wariant Caddy przewiduje HTTPS. Należy ocenić faktyczny sposób dostępu do instalacji.

## Weryfikacja i odtwarzanie

Przeszło **125 testów: 95 Python i 30 frontendowych**. Obejmują pocztę i transport (32), `test*security*.py` (35), kontrakt API, migracje, ustawienia, role, SMTP i limitowanie logowania (28) oraz frontend poczty, menu, profilu i paska bocznego (30). Dodatkowo odtworzono pięć ustaleń powyżej. `git diff --check` nie wykazał błędów białych znaków; Git zgłosił jedynie ostrzeżenia o konwersji LF/CRLF w istniejących zmianach.

Skan [OSV](https://osv.dev/) przez `https://api.osv.dev/v1/querybatch` objął wszystkie 68 przypiętych zależności `requirements.txt`: **0 zgłoszonych podatności dla podanych wersji**, bez różnic wersji względem lokalnego venv. To wynik bazy znanych podatności, nie dowód braku nieznanych błędów. Nie skanowano pakietów systemowych ani rzeczywistego obrazu produkcyjnego.

```powershell
.\venv\Scripts\python.exe tools/security_audit_20261004.py
node tools/security_audit_20261004.cjs
.\venv\Scripts\python.exe tools/security_audit_dependencies_20261004.py
```

Pierwsze dwa skrypty działają offline na atrapach i pokazują obecne słabości. Ich asercje dokumentują podatności, a nie oczekiwane zachowanie po naprawie; nie są włączone do standardowego zestawu regresji. Trzeci wysyła do OSV wyłącznie publiczne nazwy i wersje pakietów.

Na Windows brakuje biblioteki natywnej `libgobject-2.0-0`, więc pełny renderer WeasyPrint nie został zweryfikowany. Testy sprawdzające odmowę odczytu plików przez fallback PDF przeszły. Nie testowano rzeczywistych kont IMAP/SMTP, zapory, serwera produkcyjnego ani nie wykonywano celowego przeciążenia aplikacji.

## Kolejność napraw

1. A1: izolacja problematycznych wiadomości i trwałe pomijanie błędnego UID.
2. A2: wspólna blokada, limity kosztownych operacji i budżety synchronizacji.
3. A3: anulowanie pobrań oraz sprawdzanie sesji po operacjach asynchronicznych.
4. A4: ograniczenie zasobów renderowania i uprawnienie podglądu.
5. A5: migracja jawnego hasła SMTP powiadomień oraz ochrona kluczy i backupów.

A1–A5 zostały objęte poprawkami opisanymi na początku dokumentu. Przy wdrożeniu należy wykonać standardowe przygotowanie aplikacji (`seed.py` w obrazie Docker), zachować klucz instalacji i uwzględnić ochronę istniejących backupów.
