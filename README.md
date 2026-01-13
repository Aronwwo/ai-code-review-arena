# AI Code Review Arena

Aplikacja do przegladania kodu przez wielu agentow AI. Wgraj kod, a agenci (Security, Performance, Style, General) przeanalizuja go i stworza raport.

## Szybki Start

### Wymagania
- Python 3.10+
- Node.js 18+

### Uruchomienie

1. **Backend** (terminal 1):
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

2. **Frontend** (terminal 2):
```bash
cd frontend
npm install
npm run dev
```

3. **Otworz przegladarke**: http://localhost:3000

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
- **ollama** - lokalne modele (wymaga zainstalowanego Ollama)

## Konfiguracja (opcjonalna)

Edytuj `backend/.env`:
```env
# Baza danych
DATABASE_URL=sqlite:///./data/code_review.db

# Klucze API (opcjonalne)
GROQ_API_KEY=your-key-here
GEMINI_API_KEY=your-key-here
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
- `GET /projects` - lista projektow
- `POST /projects` - nowy projekt
- `POST /projects/{id}/files` - dodaj plik
- `POST /projects/{id}/reviews` - uruchom przeglad
- `GET /reviews/{id}` - szczegoly przegladu

Pelna dokumentacja API: http://localhost:8000/docs

## Tryby przegladu

- **Council** - agenci wspolpracuja i tworza wspolny raport
- **Arena** - agenci debatuja, moderator wydaje werdykt

## Rozwiazywanie problemow

1. **Blad logowania** - sprawdz czy haslo ma min 8 znakow, wielka litere i cyfre
2. **Blad bazy danych** - usun `backend/data/code_review.db` i uruchom ponownie
3. **Blad timeout** - zwieksz timeout_seconds w konfiguracji przegladu
4. **Frontend nie dziala** - sprawdz czy backend dziala na porcie 8000

## Licencja

MIT
