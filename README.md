# FitZone — aplikacja internetowa siłowni

Polska aplikacja React + Django REST Framework + PostgreSQL. Aktualna ścieżka wdrożenia: Vercel Hobby + Neon Free. Konfiguracja Render pozostaje jako alternatywa. Frontend i API działają pod jednym adresem. Płatności przez zewnętrzne API Stripe, wyłącznie w trybie testowym.

## Publikacja bez karty — Vercel + Neon

Vercel obsługuje Django i pliki statyczne React. Neon Free udostępnia PostgreSQL bez karty i bez limitu czasu planu, z limitami zużycia. Vercel Hobby służy projektom osobistym i niekomercyjnym — projekt zaliczeniowy z fikcyjną siłownią i testowymi płatnościami pasuje do tego zastosowania. Nie wybieraj wersji Pro, trial ani płatnej bazy. Jeżeli rejestracja mimo to wymaga karty, przerwij ją.

1. Utwórz konto na https://vercel.com/signup, wybierając użytek osobisty / Hobby i logowanie przez GitHub.
2. Utwórz konto na https://console.neon.tech i projekt `fitzone` w planie Free. Wybierz region europejski. Zapisz dane połączenia wyłącznie w ustawieniach hostingu, nie w repozytorium i nie w czacie.
3. W Vercel zaimportuj `KaczkaDaw1d/Fitzone`. Root Directory: główny katalog repozytorium (`.`). Framework: Django. `vercel.json` definiuje komendę budowania React.
4. W **Environment Variables** ustaw dla **Production**:

| Zmienna | Wartość |
|---|---|
| `DJANGO_SECRET_KEY` | Długi, losowy sekret wygenerowany lokalnie lub przez narzędzie wdrożeniowe |
| `DJANGO_DEBUG` | `0` |
| `DATABASE_URL` | Connection string z Neon, najlepiej pooled, z `sslmode=require` |
| `DATABASE_URL_UNPOOLED` | Opcjonalne bezpośrednie połączenie Neon do migracji |
| `SEED_DEMO` | `1` — przykładowa oferta i grafik |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Opcjonalnie dane nowego administratora; usuń obie zmienne po utworzeniu konta |

5. Wdróż projekt. Podczas produkcyjnego builda powstaje frontend, wykonywane są migracje i opcjonalne dodanie danych. Vercel automatycznie wykonuje `collectstatic` i udostępnia zasoby przez CDN. Budowa w środowisku Preview nie wykonuje migracji.
6. Adres produkcyjny zostanie przypisany przez Vercel; aplikacja rozpoznaje zmienne `VERCEL_URL` i `VERCEL_PROJECT_PRODUCTION_URL`. Możesz jawnie ustawić `PUBLIC_URL` na docelowy adres HTTPS. Dla własnej domeny dodaj również `DJANGO_ALLOWED_HOSTS`.
7. Zarejestruj konto klienta. Stripe skonfiguruj później zgodnie z sekcją poniżej, używając adresu Vercel jako adresu webhooka.

Nie podłączaj podglądów Preview do produkcyjnej bazy. Dla podglądów ustaw osobną gałąź bazy Neon i zmienne o zakresie Preview. Samo pomijanie migracji nie blokuje zapisu przez uruchomioną aplikację. Darmowe plany mają limity zużycia i mogą wstrzymać usługę po ich przekroczeniu.

Dokumentacja: https://vercel.com/docs/frameworks/full-stack/django, https://vercel.com/docs/plans/hobby, https://neon.com/pricing.

## Co działa

- Rejestracja, logowanie, wylogowanie; sesje Django, ciasteczka HttpOnly, CSRF oraz walidacja haseł.
- Oferta karnetów pobierana z bazy.
- Grafik z wyborem dnia, klubu i rodzaju zajęć.
- Rezerwacja tylko z karnetem ważnym w terminie zajęć; limit miejsc, brak duplikatów, anulowanie własnej rezerwacji.
- Panel klienta: aktywny i przyszłe karnety, rezerwacje, historia zamówień.
- Stripe Checkout: kwota ustalana na serwerze; podpisane webhooki, weryfikacja kwoty, waluty i identyfikatora sesji; ponowne dostarczenie zdarzenia nie dodaje drugiego karnetu.
- Kolejny zakup przedłuża okres dostępu. Nie ma automatycznych obciążeń ani odnawiania.
- Django Admin do zarządzania ofertą, trenerami zapisanymi przy zajęciach, lokalizacjami i grafikiem. Zamówienia i karnety są w panelu tylko do odczytu.
- Dockerfile, konfiguracja Render i CI z bazą PostgreSQL oraz testem równoczesnej rezerwacji ostatniego miejsca.

Kluby, ceny i trenerzy są przykładowymi danymi edukacyjnymi. To nie jest oferta istniejącej siłowni. Nie ma funkcji resetowania hasła ani wysyłki e-maili w tej wersji.

## Struktura

```
backend/config/       konfiguracja Django
backend/gym/          modele, API, płatności, testy, panel admina
frontend/src/         interfejs React i CSS
compose.yaml          PostgreSQL na potrzeby lokalnego developmentu
Dockerfile            wspólny obraz frontendu i backendu
render.yaml           aplikacja i PostgreSQL na Render
.github/workflows/    testy backendu/PostgreSQL i build frontendu
```

## Uruchomienie lokalne — standardowo z PostgreSQL

Potrzebujesz Python 3.12+, Node.js 22+, pnpm 11 i Docker Desktop do lokalnej bazy. W PowerShell, z katalogu projektu:

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
corepack enable
corepack prepare pnpm@11.25.0 --activate
docker compose up -d db
Copy-Item backend/.env.example backend/.env
cd frontend
pnpm install --frozen-lockfile
pnpm build
cd ..
./Start-FitZone.ps1
```

Otwórz **http://127.0.0.1:8000**. Zarejestruj własne konto. Skrypt startowy wykonuje migracje, dodaje grafik i zbiera pliki statyczne. Zmiana React wymaga ponownego `pnpm build`.

Szybki podgląd bez Dockera: w `backend/.env` ustaw `DJANGO_DEBUG=1` i usuń albo zakomentuj `DATABASE_URL`. Wtedy używana jest SQLite. To tylko wygoda lokalna — produkcja wymusza PostgreSQL. SQLite nie daje takiej samej ochrony równoczesnych zapisów jak PostgreSQL. Dane z lokalnej bazy nie przenoszą się automatycznie na hosting.

### Development React z automatycznym odświeżaniem

Pierwszy terminal:

```powershell
cd backend
../.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
```

Drugi terminal:

```powershell
cd frontend
pnpm dev
```

Otwórz **http://localhost:5173/static/app/**. W `.env` ustaw wtedy `PUBLIC_URL=http://localhost:5173`. Korzystaj konsekwentnie z `localhost`, aby adres odpowiadał konfiguracji CSRF. Vite przekazuje API do Django, więc przeglądarka widzi jeden serwer.

### Administrator

```powershell
cd backend
../.venv/Scripts/python.exe manage.py createsuperuser
```

Panel: **http://127.0.0.1:8000/admin/**. Konto administratora jest osobne od konta klienta i nie powstaje automatycznie.

## Publikacja online — masz już GitHub

### 1. Repozytorium

Na GitHub utwórz puste repozytorium `fitzone` (najlepiej prywatne, bez automatycznego README). Następnie w katalogu projektu:

```powershell
git init -b main
git add .
git commit -m "Add FitZone gym application"
git remote add origin https://github.com/TWOJ_LOGIN/fitzone.git
git push -u origin main
```

Zastąp `TWOJ_LOGIN` swoim loginem. `.env`, lokalna baza i środowisko Python są ignorowane. Nie dodawaj kluczy Stripe do plików śledzonych przez Git.

### 2. Konto Render i wdrożenie

1. Wejdź na https://dashboard.render.com i utwórz konto przez GitHub.
2. Przyznaj dostęp do repozytorium `fitzone`.
3. Wybierz **New → Blueprint** i wskaż repozytorium.
4. Render odczyta `render.yaml`: jeden serwis Docker i jedna baza PostgreSQL w regionie Frankfurt.
5. **Konfiguracja używa bezpłatnych planów `free`.** To wariant demonstracyjny: aplikacja zasypia po 15 minutach bez ruchu, a baza PostgreSQL wygasa po 30 dniach. Przed terminem zaliczenia zadbaj o dalszą dostępność bazy. Plan płatny wymaga osobnej decyzji o kosztach. Dokumentacja ograniczeń: https://render.com/docs/free.
6. Aplikacja automatycznie używa adresu HTTPS przypisanego przez Render. Jeżeli później podłączysz własną domenę, dodaj `PUBLIC_URL=https://twoja-domena.pl` i tę domenę do `DJANGO_ALLOWED_HOSTS` w Environment.
7. Klucze Stripe dodasz później w Environment. Strona i logowanie działają bez Stripe, a zakup pokazuje informację o braku konfiguracji.
8. Poczekaj na status **Live**. Migracje uruchamiają się przy starcie obrazu. Ten sposób jest przeznaczony dla pojedynczej instancji projektu; przy skalowaniu przenieś migracje do osobnego kroku przed wdrożeniem.
9. `SEED_DEMO=1` automatycznie dodaje ofertę i grafik przy starcie. Darmowy plan nie udostępnia Shell. Aby utworzyć administratora, dodaj w **Environment** dwie prywatne zmienne: `ADMIN_EMAIL` i `ADMIN_PASSWORD` (silne hasło, co najmniej 10 znaków), a następnie zapisz i wdróż usługę ponownie. Nie wpisuj ich do repozytorium ani do czatu. Istniejące konto klienta nie zostanie podniesione do roli administratora. Po utworzeniu konta usuń obie zmienne z Environment. Zwykłe konto klienta możesz założyć na stronie. Na płatnym planie alternatywnie wykonaj w Shell:

```bash
python manage.py seed_demo
python manage.py createsuperuser
```

10. Otwórz adres usługi. Przetestuj rejestrację oraz logowanie. Panel admina będzie pod `/admin/`.

`seed_demo` tworzy przykładowe zajęcia na 14 dni od momentu uruchomienia. Po upływie tego czasu uruchom polecenie ponownie albo dodaj własny grafik w panelu. Nie tworzy kont z publicznym hasłem, karnetów ani fałszywych płatności.

## Konfiguracja płatności Stripe

1. Utwórz konto na https://dashboard.stripe.com i przełącz się do środowiska testowego/sandbox.
2. Pobierz testowy secret key zaczynający się od `sk_test_`.
3. W środowisku testowym utwórz webhook do `https://TWOJ_ADRES/api/stripe/webhook/`.
4. Wybierz zdarzenia `checkout.session.completed` i `checkout.session.async_payment_succeeded`.
5. Skopiuj podpisujący sekret webhooka `whsec_...`.
6. W Render → Environment ustaw `STRIPE_SECRET_KEY` i `STRIPE_WEBHOOK_SECRET`, zapisz i wdróż ponownie.
7. Zarejestruj konto klienta, wybierz karnet i przejdź przez Stripe Checkout. Użyj testowej karty `4242 4242 4242 4242`, przyszłej daty ważności oraz dowolnego trzycyfrowego CVC. Nie używaj rzeczywistych danych karty.
8. Po powrocie na stronę kliknij **Odśwież status** w panelu. Karnet pojawia się dopiero po otrzymaniu potwierdzenia Stripe.

Lokalnie użyj Stripe CLI:

```bash
stripe login
stripe listen --forward-to http://127.0.0.1:8000/api/stripe/webhook/
```

Sekret wypisany przez `stripe listen` wpisz do lokalnego `.env` i uruchom Django ponownie. To inny sekret niż dla hostowanego endpointu. Pełen scenariusz zakupu testuj przez aplikację — samo `stripe trigger` nie posiada identyfikatora rzeczywistego zamówienia z bazy.

## Testy

```powershell
cd backend
../.venv/Scripts/python.exe manage.py check
../.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
../.venv/Scripts/python.exe manage.py test
cd ../frontend
pnpm build
```

Testy sprawdzają CSRF również dla anonimowego logowania/rejestracji, walidację haseł, limity zajęć, własność danych, ważność karnetu, podpisy webhooków, powtórzenia zdarzeń, zgodność kwoty i waluty oraz ceny ustalane na serwerze. Test równoczesnych zapisów uruchamia się tylko na PostgreSQL; GitHub Actions dostarcza tę bazę.

## Model danych i API

Użytkownik → Zamówienia → Karnety; Użytkownik → Rezerwacje → Zajęcia → Lokalizacja. Oferta karnetów znajduje się w `Plan`. Zamówienie przechowuje cenę, nazwę i czas ważności z chwili zakupu, więc późniejsza zmiana oferty nie zmienia zakupionego produktu.

| Endpoint | Zastosowanie |
|---|---|
| `GET /api/csrf/` | Pobranie ciasteczka CSRF |
| `POST /api/auth/register/` | Rejestracja: name, email, password |
| `POST /api/auth/login/` | Logowanie: email, password |
| `POST /api/auth/logout/` | Wylogowanie |
| `GET /api/catalog/` | Karnety, kluby, najbliższe zajęcia |
| `GET /api/me/` | Własne konto, zakupy, karnety, rezerwacje |
| `POST /api/classes/:id/book/` | Rezerwacja zajęć |
| `DELETE /api/bookings/:id/` | Anulowanie własnej rezerwacji |
| `POST /api/checkout/` | Utworzenie płatności: plan_id |
| `POST /api/stripe/webhook/` | Podpisane potwierdzenia Stripe |
| `GET /api/health/` | Stan procesu dla hostingu |

Ograniczenia częstotliwości DRF są podstawową ochroną aplikacyjną i używają pamięci procesu. Dla ruchu produkcyjnego poza prezentacją projektu zastosuj wspólny cache i ochronę na poziomie hostingu. Wersja projektu nie realizuje automatycznego odbierania karnetów po zwrocie ani obsługi sporów; nie należy przełączać jej na rzeczywiste płatności.

## Dokumentacja źródłowa

- Django: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- DRF: https://www.django-rest-framework.org/api-guide/authentication/
- Stripe: https://docs.stripe.com/checkout/fulfillment
- Testy Stripe: https://docs.stripe.com/testing
- Render: https://render.com/docs/deploy-django
- Konfiguracja Render: https://render.com/docs/blueprint-spec
