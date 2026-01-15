# AI Code Review Arena

Aplikacja do przegladania kodu przez wielu agentow AI. Wgraj kod, a agenci (Security, Performance, Style, General) przeanalizuja go i stworza raport.

## Szybki Start

### Wymagania
- Python 3.10+
- Node.js 18+
- npm 9+ (lub pnpm/yarn, ale komendy w README sa pod npm)

### Uruchomienie (reczne)

1. **Backend** (terminal 1):
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2. **Frontend** (terminal 2):
```bash
cd frontend
npm install
npm run dev
```

3. **Otworz przegladarke**: http://localhost:5173

### Uruchomienie (skroty z root)

Z katalogu glownego projektu:
```bash
# backend
npm run dev:backend

# frontend
npm run dev:frontend
```

## Jak uzywac

1. **Zarejestruj sie** - kliknij "Zarejestruj sie" i utworz konto (email, haslo min 8 znakow z wielka litera i cyfra)

2. **Zaloguj sie** - uzyj swojego emaila i hasla

3. **Utworz projekt** - kliknij "Nowy projekt" i dodaj nazwe

4. **Dodaj pliki** - wklej kod do projektu (moze byc Python, JavaScript, itp.)

5. **Uruchom przeglad** - kliknij "Nowy przeglad", wybierz agentow (np. security, general) i provider (mock do testow)

6. **Zobacz wyniki** - agenci przeanalizuja kod i pokaza znalezione problemy

## Providery AI

- **mock** - do testow, nie wymaga kluczy API (generuje przykladowe wyniki)
- **groq** - szybkie API, darmowy tier (wymaga klucza z https://console.groq.com)
- **gemini** - Google AI (wymaga klucza z https://makersuite.google.com)
- **openai** - OpenAI API (wymaga klucza z https://platform.openai.com)
- **deepseek** - DeepSeek API (wymaga klucza z https://platform.deepseek.com)
- **perplexity** - Perplexity API (wymaga klucza z https://www.perplexity.ai)
- **ollama** - lokalne modele (wymaga zainstalowanego Ollama)

Po ustawieniu API key modele sa pobierane automatycznie. W ustawieniach jest tez przycisk "Odswiez modele" per provider.

## Konfiguracja (opcjonalna)

Edytuj `backend/.env`:
```env
# Baza danych
DATABASE_URL=sqlite:///./data/code_review.db

# Klucze API (opcjonalne)
GROQ_API_KEY=your-key-here
GEMINI_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
DEEPSEEK_API_KEY=your-key-here
PERPLEXITY_API_KEY=your-key-here
```

## Struktura projektu

```
programowaniewint/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── api/       # Endpointy REST
│   │   ├── models/    # Modele bazy danych
│   │   ├── orchestrators/  # Logika przegladow
│   │   └── providers/ # Integracje z AI
│   └── data/          # Baza SQLite
├── frontend/          # React frontend
│   └── src/
│       ├── components/  # Komponenty UI
│       ├── pages/       # Strony aplikacji
│       └── contexts/    # Stan aplikacji
└── README.md
```

## API Endpoints

- `POST /auth/register` - rejestracja
- `POST /auth/login` - logowanie
- `POST /auth/logout` - wylogowanie (czyści ciasteczka)
- `POST /auth/refresh` - odśwież tokeny (cookies lub body)
- `GET /auth/me` - bieżący użytkownik
- `GET /projects` - lista projektow
- `POST /projects` - nowy projekt
- `POST /projects/{id}/files` - dodaj plik
- `POST /projects/{id}/reviews` - uruchom przeglad
- `GET /reviews/{id}` - szczegoly przegladu

Pelna dokumentacja API: http://localhost:8000/docs

## Auth i CSRF (nowy flow)

- Logowanie ustawia **httpOnly cookies**: `access_token` i `refresh_token`.
- Frontend wysyła **CSRF token** w nagłówku `X-CSRF-Token` dla metod POST/PUT/PATCH/DELETE.
- CSRF jest przechowywany w ciasteczku `csrf_token` (dostępne dla JS).

W praktyce nic nie musisz konfigurować – axios ma `withCredentials: true`.

## Testy

Z katalogu glownego:
```bash
npm test
```

Tylko backend:
```bash
cd backend
python -m pytest tests -v
```

Tylko frontend (CI, przechodzi bez testow):
```bash
cd frontend
npm run test:ci
```

## Tryby przegladu

- **Council** - agenci wspolpracuja i tworza wspolny raport
- **Arena** - agenci debatuja, moderator wydaje werdykt

## Rozwiazywanie problemow

1. **Blad logowania** - sprawdz czy haslo ma min 8 znakow, wielka litere i cyfre
2. **Blad bazy danych** - usun `backend/data/code_review.db` i uruchom ponownie
3. **Blad timeout** - zwieksz timeout_seconds w konfiguracji przegladu
4. **Frontend nie dziala** - sprawdz czy backend dziala na porcie 8000
5. **Brak modeli** - ustaw API key lub uruchom Ollama i pobierz model

## Licencja

MIT
