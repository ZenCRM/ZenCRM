# Przegląd bezpieczeństwa nowych funkcji — 4 października 2026

Aktualizacja po niezależnym audycie: poprawiono izolację błędnych wiadomości, wspólną blokadę i limity synchronizacji, pobieranie załączników po zmianie sesji, limity procesu renderowania szablonów oraz szyfrowanie SMTP powiadomień. Aktualny opis zmian, testów i ograniczeń znajduje się w [SECURITY_AUDIT_20261004.md](SECURITY_AUDIT_20261004.md). Poniższy tekst dokumentuje wcześniejszy etap wdrożenia.

Zakres: skrzynki osobiste i zespołowe, synchronizacja IMAP, SMTP, HTML wiadomości i stopek, załączniki, powiązania z klientami, ustawienie mailto/CRM oraz szablony dokumentów. Przegląd kodu, testy regresji i lokalna weryfikacja w Chrome; bez testu penetracyjnego środowiska produkcyjnego lub rzeczywistych kont pocztowych.

## Znalezione i poprawione problemy

1. **SSRF przez konfigurację serwerów pocztowych.** Dowolny host pozwalał inicjować połączenia do usług wewnętrznych. Transport sprawdza teraz wszystkie wyniki DNS, odrzuca adresy niepubliczne, multicast i prywatne adresy mapowane IPv4/IPv6. Socket łączy się bezpośrednio ze sprawdzonym adresem; nie wykonuje drugiego rozwiązywania DNS. TLS nadal sprawdza certyfikat względem oryginalnej nazwy hosta. Ochrona działa przy każdym połączeniu, także istniejących skrzynek. Podejście opiera się na [zaleceniach OWASP dotyczących SSRF i DNS](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html). Skutek: serwery pocztowe dostępne wyłącznie pod prywatnym adresem IP są blokowane.

2. **Przekazanie zapisanego hasła do zmienionego serwera.** Osoba zarządzająca skrzynką mogła zmienić host bez znajomości zapisanego hasła. Teraz zmiana hosta IMAP lub SMTP wymaga ponownego wpisania hasła, przed zmianą danych i próbą połączenia.

3. **Nadmierna alokacja pamięci przez IMAP.** Deklarowany rozmiar MIME nie gwarantował rzeczywistego rozmiaru odpowiedzi. Transport odrzuca zbyt duży literal przed odczytem bufora; dodatkowo sprawdzamy faktyczną długość odpowiedzi. Limity: 512 KiB dla nagłówków i domyślnego literalu, 2 MiB dla części tekstowej, 8 MiB łącznie dla tekstu wiadomości i 50 MiB dla pobieranego załącznika w postaci transportowej. Załączniki nadal pobierane są wyłącznie na żądanie.

## Zweryfikowane zabezpieczenia

- API wymaga aktywnego użytkownika i ważnego JWT. Hasła skrzynek nie są serializowane ani ujawniane w odpowiedziach API; w bazie są szyfrowane Fernet kluczem pochodzącym z sekretu aplikacji.
- Skrzynki osobiste pozostają prywatne również wobec innych administratorów. Skrzynki zespołu i licznik nieprzeczytanych wiadomości obejmują tylko członków tego zespołu. Zarządzanie ustawieniami zespołowymi wymaga uprawnień lidera lub administratora będącego członkiem zespołu.
- Historia klienta, szczegóły maili i załączniki korzystają z dostępnych skrzynek. Testy obejmują odmowę dostępu do cudzych wiadomości.
- SMTP i IMAP wymagają TLS z weryfikacją certyfikatu. STARTTLS jest wykonywany przed logowaniem. UDW występuje w kopercie wysyłki, bez ujawniania go w nagłówku wiadomości.
- HTML jest wyświetlany w iframe bez `allow-scripts` i `allow-same-origin`, z CSP i `no-referrer`. Odebrane wiadomości przechodzą sanitizację; stopki zachowują CSS i układ, ale usuwają skrypty, zdarzenia i niebezpieczne schematy URL. Test w Chrome potwierdził blokadę skryptów i dostępu do dokumentu rodzica.
- Treść tekstowa, tematy i odbiorcy są wyświetlane jako tekst lub escapowane; walidacja ogranicza wstrzykiwanie nagłówków. Załączniki są zwracane do pobrania, bez automatycznego wykonania lub zapisu.
- Szablony dokumentów renderuje Jinja SandboxedEnvironment z autoescape. Testy bezpieczeństwa obejmują także izolację HTML oraz zakaz odczytu plików lokalnych przez generowanie PDF.
- Spóźnione odpowiedzi licznika z poprzedniej sesji są ignorowane; licznik zeruje się przy wylogowaniu.

## Pozostałe ograniczenia

Pełny HTML i zdalne grafiki poszerzają powierzchnię ataku. Grafiki w stopkach mogą rejestrować adres IP i wyświetlenie; to zaakceptowane wcześniej zachowanie. Odebrane maile wymagają osobnego zezwolenia na zdalne obrazy. Nie ma gwarancji, że każdy zewnętrzny klient pocztowy zachowa się identycznie wobec wysłanej stopki.

Treści wiadomości i metadane są przechowywane w bazie bez dodatkowego szyfrowania kolumn. Dostęp do bazy, kopii zapasowych oraz sekretu aplikacji nadal wymaga ochrony administracyjnej. Utrata lub zmiana sekretu bez migracji uniemożliwi odszyfrowanie zapisanych haseł.

Połączenia są synchroniczne i mają timeout, ale równoległe wywołania synchronizacji mogą obciążać procesy serwera. Nie wdrożono rozproszonego limitowania wywołań ani infrastrukturalnej kontroli ruchu wychodzącego. Publiczne serwery pocztowe mogą używać niestandardowych portów; reguły firewall powinny odpowiadać polityce wdrożenia.

Testy używają atrap IMAP/SMTP; nie sprawdzają konfiguracji dostawcy poczty, zapory, produkcyjnych kluczy, wersji wszystkich zależności ani kompromitacji konta pocztowego. Wynik jest przeglądem zmian, nie certyfikacją całej aplikacji.

## Walidacja

- 48 testów Python: poczta, transport i istniejące zabezpieczenia aplikacji.
- 25 testów Python: kontrakt API, migracje bazy, istniejąca poczta, uprawnienia i ustawienia.
- 21 testów frontend: poczta, obsługa odbiorców, licznik, izolacja sesji i kontrakt komponentów.
- Chrome: licznik 46 → 45 po odczycie, brak dostępu skryptów stopki do rodzica i brak błędów JavaScript.

W środowisku Windows brak bibliotek natywnych WeasyPrint; testy zabezpieczeń PDF przeszły, w tym odrzucenie zasobów zewnętrznych przez ścieżkę zapasową. Pełne renderowanie WeasyPrint nie zostało tu potwierdzone.

## Aktualizacja: sprawdzanie poczty i formatowanie odebranych maili

Dodano serwerowy proces sprawdzający skrzynki według ustawienia 5, 10, 15, 30 lub 60 minut (domyślnie 5). Działa podczas pracy aplikacji również bez otwartej przeglądarki. Cykl procesu uruchamia się co 30 sekund; termin sprawdzenia może się przesunąć o ten czas oraz czas obsługi innych skrzynek. Blokada w bazie ogranicza równoległą pracę procesów okresowych nad tą samą skrzynką; wygasa po godzinie w razie awarii procesu. Błędy mają odroczone ponowienie, a logi nie zawierają haseł ani treści wiadomości. Zmienianie częstotliwości wymaga dotychczasowych uprawnień do ustawień skrzynki. Proces można wyłączyć administracyjnie przez `MAIL_POLLING_ENABLED=false`.

Filtr odebranego HTML zachowuje teraz tło (`background`), klasy, bezpieczne bloki CSS i formatowanie stopek. Deklaracje CSS są parsowane przez tinycss2; odrzucamy odwołania `url()`, `@import`, aktywne wyrażenia i nieobsługiwane reguły. CSP i sandbox pozostają aktywne. Zdalne obrazy odebranych maili nadal wymagają zezwolenia; załączniki nadal pobierane są wyłącznie na żądanie. Zmieniono wersję przetwarzania odebranych wiadomości, aby synchronizacja mogła odtworzyć formatowanie ze źródła IMAP; zwykła synchronizacja obejmuje ostatnie 100 wiadomości, pełna synchronizacja odświeża również starszą historię.

Aktualna walidacja: 51 testów poczty/transportu/bezpieczeństwa, 12 testów kontraktu API i migracji oraz 22 testy frontendowe. Chrome potwierdził zapis częstotliwości 15 minut i granatowe tło oryginalnej stopki (`rgb(20, 33, 61)`) w odebranej wiadomości, przy domyślnym widoku HTML.
