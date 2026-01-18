#!/usr/bin/env python3
"""Prosty test manualny Arena - sprawdza czy endpoint akceptuje tylko 'general' rolę."""
import requests
import json

# Konfiguracja
BASE_URL = "http://localhost:8000"

print("🧪 Test Arena - czy akceptuje tylko 'general' rolę\n")

# 1. Rejestracja testowego użytkownika
print("1️⃣ Rejestracja testowego użytkownika...")
register_data = {
    "email": "test_arena@example.com",
    "username": "test_arena_user",
    "password": "TestPassword123"
}

try:
    r = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    if r.status_code == 201:
        print("   ✅ Zarejestrowano")
    elif r.status_code == 400 and "już istnieje" in r.text:
        print("   ℹ️  Użytkownik już istnieje - OK")
    else:
        print(f"   ⚠️  Status: {r.status_code}")
except Exception as e:
    print(f"   ⚠️  Użytkownik już istnieje - kontynuuję: {e}")

# 2. Logowanie
print("\n2️⃣ Logowanie...")
login_data = {
    "email": "test_arena@example.com",
    "password": "TestPassword123"
}
r = requests.post(f"{BASE_URL}/auth/login", json=login_data)
if r.status_code != 200:
    print(f"   ❌ Błąd logowania: {r.status_code} - {r.text}")
    exit(1)

token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"   ✅ Zalogowano (token: {token[:20]}...)")

# 3. Utworzenie projektu
print("\n3️⃣ Tworzenie projektu testowego...")
project_data = {
    "name": f"Test Arena Project",
    "description": "Projekt do testowania Arena"
}
r = requests.post(f"{BASE_URL}/projects", json=project_data, headers=headers)
if r.status_code != 201:
    print(f"   ❌ Błąd tworzenia projektu: {r.status_code} - {r.text}")
    exit(1)

project_id = r.json()["id"]
print(f"   ✅ Projekt utworzony (ID: {project_id})")

# 4. Dodanie pliku do projektu
print("\n4️⃣ Dodawanie pliku testowego...")
file_data = {
    "name": "test.py",
    "content": """def divide(a, b):
    return a / b  # Bug: brak sprawdzenia dzielenia przez zero

result = divide(10, 0)
print(result)
""",
    "language": "python"
}
r = requests.post(f"{BASE_URL}/projects/{project_id}/files", json=file_data, headers=headers)
if r.status_code != 201:
    print(f"   ❌ Błąd dodawania pliku: {r.status_code} - {r.text}")
    exit(1)

print(f"   ✅ Plik dodany")

# 5. TEST GŁÓWNY: Utworzenie sesji Arena z TYLKO 'general' rolą
print("\n5️⃣ 🎯 TEST GŁÓWNY: Utworzenie Arena z TYLKO 'general' rolą...")
arena_data = {
    "project_id": project_id,
    "team_a_config": {
        "general": {
            "provider": "ollama",
            "model": "qwen2.5-coder:latest",
            "temperature": 0.2,
            "max_tokens": 4096
        }
        # ✅ Brak security, performance, style - tylko general!
    },
    "team_b_config": {
        "general": {
            "provider": "ollama",
            "model": "deepseek-coder:latest",
            "temperature": 0.2,
            "max_tokens": 4096
        }
        # ✅ Brak security, performance, style - tylko general!
    }
}

print(f"\n📤 Wysyłam request:\n{json.dumps(arena_data, indent=2, ensure_ascii=False)}\n")

r = requests.post(f"{BASE_URL}/arena/sessions", json=arena_data, headers=headers)

print(f"📥 Odpowiedź: Status {r.status_code}")

if r.status_code == 201:
    response_data = r.json()
    print(f"\n✅ ✅ ✅ SUKCES! Arena akceptuje tylko 'general' rolę!\n")
    print(f"Arena Session ID: {response_data['id']}")
    print(f"Status: {response_data['status']}")
    print(f"Team A config: {response_data['team_a_config']}")
    print(f"Team B config: {response_data['team_b_config']}")
    print(f"\n🎉 Arena działa poprawnie!")
else:
    print(f"\n❌ BŁĄD: {r.status_code}")
    print(f"Odpowiedź: {r.text}")
    print(f"\n⚠️  Arena NIE działa poprawnie - sprawdź backend!")

print("\n" + "="*60)
print("TEST ZAKOŃCZONY")
print("="*60)
