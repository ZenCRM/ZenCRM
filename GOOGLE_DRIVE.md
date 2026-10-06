# Google Drive w ZenCRM

Integracja udostępnia własny widok w menu, wyszukiwanie i listę plików, wysyłanie plików do 10 MB oraz zapis bieżącego podsumowania CSV ze Studia raportów. Tworzy folder ZenCRM na dysku użytkownika. Nie nadpisuje, nie usuwa ani nie udostępnia plików.

## Konfiguracja administratora

1. W Google Cloud utwórz projekt, włącz Google Drive API i skonfiguruj ekran zgody OAuth. Przy trybie testowym dodaj użytkowników testowych.
2. Utwórz klienta OAuth typu **Web application**. Dodaj dokładny adres przekierowania `https://ADRES-CRM/api/plugins/google-drive/callback`. Integracja wyświetla ten adres administratorowi. Dla lokalnego developmentu dopuszczalny jest HTTP na localhost.
3. Ustaw `GOOGLE_DRIVE_CLIENT_ID` i `GOOGLE_DRIVE_CLIENT_SECRET` w środowisku serwera. Docker Compose przekazuje te zmienne. Zachowaj stały, losowy `SECRET_KEY` o długości minimum 32 znaków; służy do szyfrowania tokenów. Ustaw publiczny adres CRM w ustawieniach firmy lub `PUBLIC_BASE_URL`. Uruchom ponownie serwer po zmianie środowiska.
4. Włącz platformę pluginów w ustawieniach. Użytkownik dodaje **Google Drive** ze sklepu, zatwierdza zakres i otwiera aplikację z menu, następnie wybiera **Połącz konto Google**.
5. Studio raportów udostępnia przycisk **Zapisz na Dysku Google**. Zapis następuje wyłącznie po kliknięciu użytkownika, dla aktualnie wygenerowanego raportu.

Klucz klienta i tokeny pozostają na serwerze. Nie umieszczaj ich w manifeście, konfiguracji frontendowej ani repozytorium.

## Zakres dostępu i odłączanie

OAuth używa `drive.file`, zgodnie z [dokumentacją zakresów Google Drive](https://developers.google.com/workspace/drive/api/guides/api-specific-auth). Widok pokazuje pliki utworzone przez tę integrację i oznaczone dla zgody danego użytkownika CRM. Nie jest przeglądarką całego dysku; nie zawiera Google Picker ani automatycznej synchronizacji.

PKCE, jednorazowy stan z ciasteczkiem HttpOnly i dziesięciominutowym terminem oraz kontrola użytkownika, hasła, zgody i rewizji aplikacji chronią proces połączenia. Tokeny są szyfrowane i przechowywane osobno dla zgody użytkownika. Cofnięcie zgody w CRM usuwa lokalne dane połączenia. **Odłącz konto Google** dodatkowo próbuje unieważnić token w Google; gdy Google jest niedostępne, aplikacja informuje o konieczności ręcznego usunięcia dostępu w ustawieniach konta Google. Pliki pozostają na dysku.

Zmiana klucza szyfrowania, konfiguracji OAuth, hasła lub zgody może wymagać ponownego połączenia. Google może również wygasić token, szczególnie przy ekranie zgody pozostającym w trybie testowym.

Testy automatyczne używają zastąpionych odpowiedzi Google i sprawdzają OAuth, szyfrowanie, prywatność plików, upload oraz odłączenie. Przed produkcją należy wykonać próbę na rzeczywistym kliencie OAuth i koncie Google.
