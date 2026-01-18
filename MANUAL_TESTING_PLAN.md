# Plan Testów Manualnych - AI Code Review Arena

## ✅ Wprowadzone poprawki
- [x] Zwiększenie `max_tokens` z 2048 do 4096
- [x] Zwiększenie `timeout_seconds` z 180s do 300s (5 minut)
- [x] Paralelizacja agentów (general first, then specialized agents in parallel)
- [x] Retry logic z exponential backoff (3 próby: 2s, 4s, 8s)
- [x] Aktualizacja dokumentacji (usunięcie moderatora)

---

## 🟡 P2: Test Security Agent + Wszystkich Agentów

### Przygotowanie testowego projektu z lukami bezpieczeństwa

#### Krok 1: Utwórz nowy projekt
1. Zaloguj się do aplikacji
2. Przejdź do "Projekty" → "Nowy projekt"
3. Nazwa: `Test Security Vulnerabilities`
4. Opis: `Projekt testowy z różnymi lukami bezpieczeństwa`

#### Krok 2: Dodaj pliki z lukami bezpieczeństwa

**Plik 1: `app.py` - SQL Injection, Hardcoded Secrets**
```python
import os
import sqlite3
from flask import Flask, request

app = Flask(__name__)

# Hardcoded API key - BŁĄD BEZPIECZEŃSTWA
API_KEY = "sk-1234567890abcdef"
DATABASE_PASSWORD = "admin123"

def get_user_data(username):
    # SQL Injection vulnerability
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)  # BŁĄD: SQL Injection
    return cursor.fetchall()

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    
    # No password hashing - BŁĄD BEZPIECZEŃSTWA
    user = get_user_data(username)
    if user and user[0]['password'] == password:
        return "Login successful"
    return "Login failed"

@app.route('/api/data')
def get_data():
    api_key = request.headers.get('X-API-Key')
    if api_key == API_KEY:  # Hardcoded key comparison
        return {"data": "sensitive information"}
    return {"error": "Unauthorized"}
```

**Plik 2: `utils.py` - XSS, Command Injection**
```python
import subprocess
from flask import request, make_response

def process_file(filename):
    # Command Injection vulnerability
    result = subprocess.run(f"cat /tmp/{filename}", shell=True)  # BŁĄD: shell=True
    return result.stdout

def render_template(content):
    # XSS vulnerability - no escaping
    html = f"<div>{content}</div>"  # BŁĄD: content not escaped
    return make_response(html)

def eval_user_input(user_code):
    # Code injection vulnerability
    result = eval(user_code)  # BŁĄD: eval() on user input
    return result

def deserialize_data(data):
    import pickle
    # Pickle deserialization vulnerability
    obj = pickle.loads(data)  # BŁĄD: unsafe deserialization
    return obj
```

**Plik 3: `auth.py` - Weak Authentication**
```python
import hashlib

def hash_password(password):
    # Weak hashing - MD5 is broken
    return hashlib.md5(password.encode()).hexdigest()

def verify_password(password, hash):
    return hash_password(password) == hash

# No rate limiting on login attempts
def login_attempt(username, password):
    # Vulnerable to brute force
    user = get_user(username)
    if verify_password(password, user.password_hash):
        return True
    return False

# Weak session management
SESSION_SECRET = "secret123"  # Too short and predictable
```

#### Krok 3: Utwórz Review z wszystkimi agentami
1. Kliknij "Rozpocznij Review"
2. Wybierz tryb: **Council**
3. Aktywuj wszystkich 4 agentów:
   - ✅ Poprawność Kodu (General)
   - ✅ Bezpieczeństwo (Security)
   - ✅ Wydajność (Performance)
   - ✅ Jakość i Styl (Style)
4. Ustaw modele Ollama (np. `qwen2.5-coder:7b` lub `deepseek-coder:6.7b`)
5. Ustaw timeout: **300 sekund** (5 minut)
6. Ustaw max_tokens: **4096**
7. Kliknij "Rozpocznij Review"

#### Krok 4: Obserwuj wykonanie
1. Sprawdź logi backendu - powinieneś zobaczyć:
   ```
   🤖 [1/4] Uruchamiam GENERAL agenta (wykrywanie błędów składniowych)...
   ✅ [1/4] General agent zakończony pomyślnie
   ✅ No syntax errors found - specialized agents will run IN PARALLEL
   🚀 Uruchamiam 3 specjalistycznych agentów RÓWNOLEGLE...
   🤖 [2/4] Uruchamiam security agent...
   🤖 [3/4] Uruchamiam performance agent...
   🤖 [4/4] Uruchamiam style agent...
   ```

2. Sprawdź frontend - powinieneś widzieć status "running" i postęp agentów

3. Poczekaj na zakończenie (powinno zająć ~3-5 minut zamiast 12-15)

#### Krok 5: Weryfikacja wyników Security Agent
1. Przejdź do strony ReviewDetail po zakończeniu
2. Sprawdź sekcję **"Problemy"**
3. Filtruj po kategorii **"security"**
4. Zweryfikuj, że Security Agent znalazł:
   - ✅ SQL Injection w `get_user_data()` (linia z `f"SELECT * FROM users WHERE username = '{username}'"`)
   - ✅ Hardcoded API keys (`API_KEY = "sk-1234567890abcdef"`)
   - ✅ Command Injection (`subprocess.run(f"cat /tmp/{filename}", shell=True)`)
   - ✅ XSS vulnerability (`f"<div>{content}</div>"` bez escaping)
   - ✅ Unsafe eval (`eval(user_code)`)
   - ✅ Weak hashing (MD5)
   - ✅ Weak session secret

5. Sprawdź, że każdy issue ma:
   - ✅ Badge z "Bezpieczeństwo" (Security agent)
   - ✅ Tytuł po polsku
   - ✅ Opis problemu
   - ✅ Numer linii
   - ✅ Sugestię poprawki

#### Krok 6: Weryfikacja wszystkich agentów
1. Sprawdź General Agent - powinien znaleźć:
   - Błędy składniowe (jeśli są)
   - Brakujące importy
   - TypeErrors

2. Sprawdź Performance Agent - powinien znaleźć:
   - Potencjalne problemy z wydajnością
   - N+1 queries (jeśli dotyczy)
   - Brak indeksów w bazie

3. Sprawdź Style Agent - powinien znaleźć:
   - Problemy z nazewnictwem
   - Brak dokumentacji (docstrings)
   - Code smells
   - Długie funkcje

#### Krok 7: Sprawdź jakość odpowiedzi
✅ **Każda odpowiedź powinna:**
- Nie zawierać placeholderów typu "tytuł problemu po polsku"
- Mieć konkretne numery linii
- Zawierać sensowne sugestie poprawek
- Być w języku polskim
- Nie być surowym JSON (tylko w sekcji "Odpowiedzi agentów" jako raw_output)

---

## 🟡 P2: Weryfikacja Jakości Odpowiedzi Wszystkich Agentów

### Test Case 1: Kod bez błędów składniowych, z problemami bezpieczeństwa
**Plik testowy: `secure_app.py`**
```python
def secure_function(data):
    """This is a secure function."""
    import hashlib
    password_hash = hashlib.sha256(data.encode()).hexdigest()
    return password_hash

# Hardcoded secret - Security should catch this
SECRET_KEY = "my-secret-key-12345"
```

**Oczekiwane wyniki:**
- ✅ General Agent: Brak błędów składniowych → specialized agents uruchamiają się równolegle
- ✅ Security Agent: Znajduje hardcoded secret
- ✅ Performance Agent: Może zgłosić import wewnątrz funkcji (opcjonalnie)
- ✅ Style Agent: Może zgłosić brak type hints

### Test Case 2: Kod z błędami składniowymi
**Plik testowy: `syntax_errors.py`**
```python
def broken_function(a, b
    return a + b

numbers = [1, 2, 3
total = sum(numbers
```

**Oczekiwane wyniki:**
- ✅ General Agent: Znajduje błędy składniowe (brak dwukropka, brak nawiasu)
- ✅ Security, Performance, Style: **POMINIĘTE** (log: "Skipping {role} agent - syntax errors found by general")
- ✅ Review kończy się szybciej (tylko general agent)

### Test Case 3: Kod z wieloma problemami
**Plik testowy: `complex_issues.py`**
```python
import sqlite3
import subprocess

def insecure_function(user_input):
    # SQL Injection
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    conn = sqlite3.connect('db.sqlite')
    cursor = conn.cursor()
    cursor.execute(query)
    
    # Command Injection
    subprocess.run(f"echo {user_input}", shell=True)
    
    # Performance: N+1 queries in loop
    for user in users:
        cursor.execute(f"SELECT * FROM orders WHERE user_id = {user.id}")
    
    # Style: no docstring, bad naming
    x = [a for a in range(1000) if a % 2 == 0]
    return x

# Hardcoded credentials
DB_PASSWORD = "password123"
API_KEY = "sk-test-key"
```

**Oczekiwane wyniki:**
- ✅ General Agent: Brak błędów składniowych
- ✅ Security Agent: SQL Injection, Command Injection, Hardcoded credentials
- ✅ Performance Agent: N+1 queries problem
- ✅ Style Agent: Brak docstring, złe nazewnictwo

### Test Case 4: Kod bez problemów
**Plik testowy: `clean_code.py`**
```python
"""Module with clean, secure code."""

import hashlib
from typing import List

def hash_password(password: str) -> str:
    """Hash password using SHA-256.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password as hex string
    """
    return hashlib.sha256(password.encode()).hexdigest()

def validate_input(user_input: str) -> bool:
    """Validate user input.
    
    Args:
        user_input: User-provided input
        
    Returns:
        True if input is valid
    """
    if not user_input:
        return False
    if len(user_input) > 100:
        return False
    return True
```

**Oczekiwane wyniki:**
- ✅ Wszystkie agenci: Brak issues lub tylko drobne sugestie
- ✅ Odpowiedzi powinny być pozytywne ("Kod jest poprawny", "Brak problemów")

---

## 🟢 P3: Test Arena Mode - Porównanie Zespołów

### Krok 1: Utwórz projekt testowy
- Nazwa: `Arena Test Project`
- Dodaj plik z problemami: `test_code.py` (użyj kodu z Test Case 3 powyżej)

### Krok 2: Utwórz Arena Session
1. Kliknij "Rozpocznij Review"
2. Wybierz tryb: **Arena**
3. **Zespół A:**
   - General: `qwen2.5-coder:7b`
   - Security: `qwen2.5-coder:7b`
   - Performance: `deepseek-coder:6.7b`
   - Style: `deepseek-coder:6.7b`
4. **Zespół B:**
   - General: `deepseek-coder:6.7b`
   - Security: `deepseek-coder:6.7b`
   - Performance: `qwen2.5-coder:7b`
   - Style: `qwen2.5-coder:7b`
5. Kliknij "Rozpocznij Review"

### Krok 3: Obserwuj równoległe wykonanie
- Oba zespoły powinny działać **równolegle**
- Sprawdź logi - powinny być osobne wątki dla Team A i Team B

### Krok 4: Porównaj wyniki
1. Po zakończeniu przejdź do Arena Detail
2. Sprawdź:
   - ✅ Liczba issues znalezionych przez Zespół A
   - ✅ Liczba issues znalezionych przez Zespół B
   - ✅ Jakość issues (czy są sensowne)
   - ✅ Czy agenci z różnych modeli dają różne perspektywy

### Krok 5: Głosowanie
1. Przejrzyj wyniki obu zespołów
2. Kliknij "Zespół A jest lepszy" lub "Zespół B jest lepszy"
3. Zweryfikuj, że głos został zapisany
4. Sprawdź, czy ranking ELO się zaktualizował

---

## 🟢 P3: Test Ranking ELO - Głosowanie

### Krok 1: Przygotuj dane testowe
1. Utwórz **minimum 5-10 Arena sessions** z różnymi zespołami
2. Dla każdej sesji zagłosuj na jeden z zespołów

### Krok 2: Sprawdź ranking ELO
1. Przejdź do sekcji "Rankingi" (jeśli istnieje) lub sprawdź w bazie danych
2. Zweryfikuj, że:
   - ✅ Modele mają przypisane ELO rating
   - ✅ ELO aktualizuje się po każdym głosie
   - ✅ Zwycięzcy mają wyższy rating
   - ✅ Przegrany ma niższy rating

### Krok 3: Sprawdź logikę ELO
```python
# W bazie danych sprawdź tabelę rankings lub podobną
# ELO powinno działać według formuły:
# new_rating = old_rating + K * (score - expected_score)
# gdzie K=32, score=1 dla zwycięzcy, score=0 dla przegranego
```

---

## 🟢 P3: Load Testing - Równoczesne Reviews

### Test Case 1: 3 równoczesne reviews
1. Utwórz **3 różne projekty** (lub użyj tego samego)
2. **Jednocześnie** uruchom 3 review (otwórz 3 zakładki w przeglądarce)
3. Obserwuj:
   - ✅ Czy backend obsługuje równoczesne requesty
   - ✅ Czy WebSocket events nie kolidują
   - ✅ Czy baza danych nie ma deadlocków
   - ✅ Czy timeouty działają poprawnie

### Test Case 2: Review z timeoutem
1. Ustaw bardzo krótki timeout (np. 10 sekund)
2. Uruchom review z dużym plikiem
3. Zweryfikuj:
   - ✅ Agent kończy się z timeout po 10 sekundach
   - ✅ Retry logic działa (3 próby)
   - ✅ Review kończy się poprawnie mimo timeoutów

### Test Case 3: Review z wieloma dużymi plikami
1. Dodaj projekt z **10+ plikami** (każdy >1000 linii)
2. Uruchom review
3. Zweryfikuj:
   - ✅ Backend nie crashuje
   - ✅ Agenci otrzymują pełny kod (nie obcięty)
   - ✅ Response time jest akceptowalny (<10 minut)

---

## 📋 Checklist końcowy

### Funkcjonalność
- [ ] General agent uruchamia się pierwszy (sekwencyjnie)
- [ ] Specjalistyczni agenci uruchamiają się równolegle (jeśli brak błędów składniowych)
- [ ] Specjalistyczni agenci są pomijani jeśli general znajdzie błędy składniowe
- [ ] Retry logic działa (3 próby z exponential backoff)
- [ ] Timeout działa poprawnie (300 sekund)
- [ ] Issues są zapisywane z `agent_role`

### Jakość odpowiedzi
- [ ] Security agent znajduje SQL Injection
- [ ] Security agent znajduje hardcoded secrets
- [ ] Security agent znajduje Command Injection
- [ ] Security agent znajduje XSS vulnerabilities
- [ ] Wszyscy agenci nie zwracają placeholderów
- [ ] Wszyscy agenci zwracają konkretne numery linii
- [ ] Wszyscy agenci zwracają sensowne sugestie

### UI/UX
- [ ] Sekcja "Problemy" wyświetla wszystkie issues
- [ ] Każdy issue ma badge z agent_role
- [ ] Sekcja "Odpowiedzi agentów" jest rozwijana
- [ ] Status review aktualizuje się na żywo (WebSocket)
- [ ] Przyciski "Wznów", "Zatrzymaj", "Usuń" działają

### Arena Mode
- [ ] Dwa zespoły uruchamiają się równolegle
- [ ] Wyniki obu zespołów są wyświetlane
- [ ] Głosowanie działa
- [ ] Ranking ELO aktualizuje się

### Performance
- [ ] Review z 4 agentami kończy się w <5 minut (z paralelizacją)
- [ ] Backend obsługuje równoczesne reviews
- [ ] Nie ma memory leaks
- [ ] Baza danych nie ma deadlocków

---

## 🐛 Znalezione problemy - Raport

**Data testów:** _______________
**Wersja:** _______________

### Błędy krytyczne
- 

### Błędy średnie
- 

### Ulepszenia
- 

### Uwagi
- 

---

## ✅ Podpis testera
**Przetestowane przez:** _______________
**Data:** _______________
**Status:** ☐ Przetestowane pomyślnie | ☐ Znaleziono problemy
