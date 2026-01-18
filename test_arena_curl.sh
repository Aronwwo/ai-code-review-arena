#!/bin/bash
# Test Arena z curl - sprawdza czy backend akceptuje tylko 'general' rolę

echo "🧪 Test Arena - czy akceptuje tylko 'general' rolę"
echo ""

BASE_URL="http://localhost:8000"

# 1. Rejestracja
echo "1️⃣ Rejestracja testowego użytkownika..."
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test_arena_curl@example.com",
    "username": "test_arena_curl",
    "password": "TestPassword123"
  }')
echo "   $(echo $REGISTER_RESPONSE | grep -o '"id":[0-9]*' || echo 'Użytkownik może już istnieć - OK')"

# 2. Logowanie
echo ""
echo "2️⃣ Logowanie..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test_arena_curl@example.com",
    "password": "TestPassword123"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
if [ -z "$TOKEN" ]; then
  echo "   ❌ Błąd logowania"
  exit 1
fi
echo "   ✅ Zalogowano (token: ${TOKEN:0:20}...)"

# 3. Utworzenie projektu
echo ""
echo "3️⃣ Tworzenie projektu..."
PROJECT_RESPONSE=$(curl -s -X POST "$BASE_URL/projects" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Test Arena Project Curl",
    "description": "Projekt testowy"
  }')

PROJECT_ID=$(echo $PROJECT_RESPONSE | grep -o '"id":[0-9]*' | cut -d':' -f2)
if [ -z "$PROJECT_ID" ]; then
  echo "   ❌ Błąd tworzenia projektu"
  exit 1
fi
echo "   ✅ Projekt utworzony (ID: $PROJECT_ID)"

# 4. Dodanie pliku
echo ""
echo "4️⃣ Dodawanie pliku..."
FILE_RESPONSE=$(curl -s -X POST "$BASE_URL/projects/$PROJECT_ID/files" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "test.py",
    "content": "def divide(a, b):\n    return a / b\n\nresult = divide(10, 0)\nprint(result)",
    "language": "python"
  }')
echo "   ✅ Plik dodany"

# 5. TEST GŁÓWNY: Arena z TYLKO 'general'
echo ""
echo "5️⃣ 🎯 TEST GŁÓWNY: Tworzenie Arena z TYLKO 'general' rolą..."
echo ""
echo "📤 Wysyłam request (tylko 'general', BEZ security/performance/style)..."

ARENA_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$BASE_URL/arena/sessions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "project_id": '"$PROJECT_ID"',
    "team_a_config": {
      "general": {
        "provider": "ollama",
        "model": "qwen2.5-coder:latest",
        "temperature": 0.2,
        "max_tokens": 4096
      }
    },
    "team_b_config": {
      "general": {
        "provider": "ollama",
        "model": "deepseek-coder:latest",
        "temperature": 0.2,
        "max_tokens": 4096
      }
    }
  }')

HTTP_CODE=$(echo "$ARENA_RESPONSE" | grep -o 'HTTP_CODE:[0-9]*' | cut -d':' -f2)
RESPONSE_BODY=$(echo "$ARENA_RESPONSE" | sed 's/HTTP_CODE:[0-9]*//')

echo ""
echo "📥 Odpowiedź: Status $HTTP_CODE"

if [ "$HTTP_CODE" = "201" ]; then
  echo ""
  echo "✅ ✅ ✅ SUKCES! Arena akceptuje tylko 'general' rolę!"
  echo ""
  echo "Szczegóły odpowiedzi:"
  echo "$RESPONSE_BODY" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE_BODY"
  echo ""
  echo "🎉 Arena działa poprawnie!"
else
  echo ""
  echo "❌ BŁĄD: Status $HTTP_CODE"
  echo "Odpowiedź:"
  echo "$RESPONSE_BODY"
  echo ""
  echo "⚠️  Arena NIE działa - sprawdź backend!"
fi

echo ""
echo "============================================================"
echo "TEST ZAKOŃCZONY"
echo "============================================================"
