import os
import sqlite3

# Przykładowy kod z celowymi błędami do demonstracji AI Code Review Arena
# Ten plik zawiera 8 różnych kategorii problemów

# 1. SQL Injection vulnerability
def get_user(username):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # NIEBEZPIECZNE: SQL injection
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()

# 2. Hardcoded credentials
DATABASE_PASSWORD = "admin123"  # Hardcoded password - BAD!
API_KEY = "sk-1234567890abcdef"  # Hardcoded API key - BAD!
SECRET_TOKEN = "supersecret123"  # Never hardcode secrets!

# 3. No error handling
def read_file(filename):
    file = open(filename, 'r')  # Może się nie udać
    content = file.read()
    # Brak zamknięcia pliku - resource leak
    return content

# 4. Inefficient code - O(n²) algorithm
def find_duplicates(items):
    duplicates = []
    for i in range(len(items)):  # O(n²) - inefficient
        for j in range(i + 1, len(items)):
            if items[i] == items[j]:
                duplicates.append(items[i])
    return duplicates

# 5. Poor style and naming
def x(a,b,c):  # Niejasna nazwa funkcji
    return a+b*c   # Brak spacji, nieczytelne

# 6. Unused variables
def calculate_total(prices):
    tax_rate = 0.23  # Unused variable
    total = sum(prices)
    discount = 0.1  # Unused variable
    subtotal = 0   # Unused variable
    return total

# 7. No input validation
def divide(a, b):
    return a / b  # Co jeśli b = 0?

def process_age(age):
    # Brak walidacji czy age jest liczbą dodatnią
    return age * 365  # Dni w życiu

# 8. Sensitive data logging
def login(username, password):
    print(f"Login attempt: {username}:{password}")  # BAD - logging password!
    # Sprawdzanie credentials
    if username == "admin" and password == DATABASE_PASSWORD:
        print(f"Success! Token: {SECRET_TOKEN}")  # BAD - logging secret token!
        return True
    return False

# 9. Więcej problemów bezpieczeństwa
def execute_command(user_input):
    # Command injection vulnerability
    os.system(f"ls {user_input}")  # NIEBEZPIECZNE!

def unsafe_deserialization(data):
    import pickle
    # Pickle deserialization bez walidacji - niebezpieczne!
    return pickle.loads(data)

# 10. Race condition
class Counter:
    def __init__(self):
        self.count = 0

    def increment(self):
        # Brak synchronizacji - race condition w multi-threading
        temp = self.count
        temp += 1
        self.count = temp

# 11. Memory leak potential
def process_large_file(filename):
    all_lines = []
    with open(filename, 'r') as f:
        for line in f:
            all_lines.append(line)  # Ładuje cały plik do pamięci!
    return all_lines

# 12. Poor exception handling
def risky_operation():
    try:
        result = 10 / 0
        return result
    except:  # Złapanie wszystkich wyjątków - zbyt szerokie
        pass  # Ignorowanie błędu - bardzo złe!

# 13. Hardcoded paths
LOG_FILE = "/Users/admin/logs/app.log"  # Hardcoded path - nie działa na innych systemach
CONFIG_PATH = "C:\\Windows\\config.ini"  # Windows-specific path

# 14. No password hashing
def create_user(username, password):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # Zapisywanie hasła w plain text!
    cursor.execute(f"INSERT INTO users VALUES ('{username}', '{password}')")
    conn.commit()

# 15. Weak random number generation
import random
def generate_session_token():
    # random.random() nie jest kryptograficznie bezpieczne!
    return str(random.random())

# 16. Missing HTTPS
API_ENDPOINT = "http://api.example.com/sensitive-data"  # Powinno być https://

# 17. Debugging code left in production
DEBUG = True
if DEBUG:
    print("Database password:", DATABASE_PASSWORD)
    print("API Key:", API_KEY)

# 18. Global mutable state
GLOBAL_USER_DATA = {}  # Globalne zmienne - złe praktyki

def update_user(user_id, data):
    GLOBAL_USER_DATA[user_id] = data  # Trudne do testowania i debug'owania

# 19. No timeout on network requests
import urllib.request
def fetch_data(url):
    # Brak timeout - może zawiesić się na zawsze
    response = urllib.request.urlopen(url)
    return response.read()

# 20. Integer overflow potential
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num  # Brak sprawdzania overflow (w innych językach problem)
    return total
