# Profesjonalny Prompt Testowy dla Claude Code

## Kontekst projektu
Aplikacja AI Code Review Arena to system wieloagentowego przeglądu kodu, który wykorzystuje 4 wyspecjalizowanych agentów AI (general, security, performance, style) do analizy kodu. Moderator został całkowicie usunięty z aplikacji - agenci zapisują issues bezpośrednio do bazy danych z informacją `agent_role`.

## Zadanie do wykonania

Przeprowadź kompleksowe testowanie aplikacji po usunięciu moderatora. Zadbaj o następujące aspekty:

### 1. Weryfikacja usunięcia moderatora
- [ ] Sprawdź, że w kodzie backend (`backend/app/orchestrators/review.py`) nie ma żadnych odniesień do moderatora (MODERATOR_PROMPT, _run_moderator, _store_moderator_issues)
- [ ] Zweryfikuj, że `conduct_review()` kończy się bezpośrednio po zakończeniu agentów (bez wywołania moderatora)
- [ ] Sprawdź, że `ReviewCreate` schema nie zawiera `moderator_config`
- [ ] Zweryfikuj, że frontend (`ReviewConfigDialog.tsx`) nie ma zakładki/tab "Moderator"
- [ ] Sprawdź, że `ReviewDetail.tsx` nie wyświetla sekcji "Raport Moderatora"
- [ ] Upewnij się, że wszystkie API endpoints nie wymagają `moderator_config`

### 2. Weryfikacja działania agentów
- [ ] Sprawdź, że każdy agent (general, security, performance, style) uruchamia się poprawnie
- [ ] Zweryfikuj, że issues są zapisywane z polem `agent_role` wskazującym na odpowiedniego agenta
- [ ] Sprawdź, że `_store_issue()` poprawnie przypisuje `agent_role` do każdego issue
- [ ] Zweryfikuj, że frontend poprawnie wyświetla issues z informacją o agencie (badge z `agent_role`)

### 3. Test funkcjonalny z rzeczywistym kodem
- [ ] Uruchom backend aplikacji (sprawdź czy się uruchamia bez błędów)
- [ ] Utwórz nowy projekt w aplikacji
- [ ] Dodaj testowy plik Python z znanymi błędami:
```python
def add(a, b)
    return a + b

nums = [1, 2, 3
total = sum(nums)
print("Total: " + total)

for i in range(3):
    print(nums[i+1])
```
- [ ] Utwórz nowy review z wszystkimi 4 agentami (general, security, performance, style)
- [ ] Użyj dostępnych modeli Ollama (np. `qwen2.5-coder:7b` lub `deepseek-coder:6.7b`)
- [ ] Poczekaj na zakończenie review
- [ ] Sprawdź, czy review zakończył się ze statusem "completed" (bez błędów)

### 4. Weryfikacja wyświetlania issues
- [ ] Sprawdź, czy sekcja "Problemy" na stronie ReviewDetail wyświetla wszystkie znalezione issues
- [ ] Zweryfikuj, że każdy issue ma przypisanego agenta (wyświetla się badge z rolą: "Poprawność Kodu", "Bezpieczeństwo", "Wydajność", "Jakość i Styl")
- [ ] Sprawdź, czy issues zawierają poprawne informacje: tytuł, opis, linia, plik, sugestie poprawki
- [ ] Zweryfikuj, że nie ma duplikatów issues (ten sam problem od tego samego agenta)
- [ ] Sprawdź, czy liczniki błędów (Błędy, Ostrzeżenia, Informacje) są poprawne

### 5. Weryfikacja odpowiedzi agentów
- [ ] Sprawdź sekcję "Odpowiedzi agentów" na stronie ReviewDetail
- [ ] Zweryfikuj, że każdy agent ma wyświetloną swoją odpowiedź (raw_output)
- [ ] Sprawdź, czy odpowiedzi są czytelne i nie zawierają surowego JSON (chyba że to błąd parsowania)
- [ ] Zweryfikuj, że agenci zwracają sensowne odpowiedzi (nie placeholdery typu "tytuł problemu po polsku")
- [ ] Sprawdź, czy timeout'y agentów są poprawnie obsługiwane

### 6. Weryfikacja jakości odpowiedzi agentów
- [ ] Sprawdź, czy General Agent poprawnie wykrywa błędy składniowe w testowym kodzie (brak dwukropka, brak nawiasu)
- [ ] Zweryfikuj, czy Security Agent nie zgłasza fałszywych alarmów (np. "SQL Injection" w prostym `def add(a, b)`)
- [ ] Sprawdź, czy Performance Agent nie zgłasza absurdalnych problemów
- [ ] Zweryfikuj, czy Style Agent zgłasza rzeczywiste problemy stylu kodu
- [ ] Sprawdź, czy issues zawierają konkretne informacje (numery linii, sugestie poprawek)

### 7. Sprawdzenie błędów i logów
- [ ] Sprawdź logi backendu podczas review - czy nie ma błędów związanych z moderatorem
- [ ] Zweryfikuj, czy nie ma błędów parsowania JSON w odpowiedziach agentów
- [ ] Sprawdź, czy nie ma błędów w konsoli przeglądarki (F12)
- [ ] Zweryfikuj, czy WebSocket events są poprawnie wysyłane (agent_started, agent_completed, review_completed)

### 8. Test edge cases
- [ ] Sprawdź, co się stanie gdy agent zwróci timeout - czy review się zakończy poprawnie
- [ ] Zweryfikuj, co się stanie gdy agent zwróci błąd - czy nie crashuje aplikacji
- [ ] Sprawdź, co się stanie gdy agent zwróci puste odpowiedzi - czy issues są poprawnie filtrowane
- [ ] Zweryfikuj, co się stanie gdy nie ma żadnych issues - czy aplikacja działa poprawnie
- [ ] Sprawdź, czy działa funkcja "Uruchom ponownie" (recreate) bez moderatora

### 9. Weryfikacja UI/UX
- [ ] Sprawdź, czy strona ReviewDetail jest czytelna bez sekcji "Raport Moderatora"
- [ ] Zweryfikuj, czy nawigacja i przyciski działają poprawnie (Wznów, Zatrzymaj, Usuń, Uruchom ponownie)
- [ ] Sprawdź, czy status review jest poprawnie wyświetlany
- [ ] Zweryfikuj, czy liczniki agentów i issues są poprawne

### 10. Sprawdzenie konsystencji danych
- [ ] Sprawdź, czy w bazie danych issues mają poprawne `agent_role` (nie NULL dla issues od agentów)
- [ ] Zweryfikuj, czy `review.summary` jest NULL dla nowych review (bez moderatora)
- [ ] Sprawdź, czy stare review z moderatorem nadal działają (backward compatibility)
- [ ] Zweryfikuj, czy API endpoint `/reviews/{id}/issues` zwraca poprawne dane z `agent_role`

## Kryteria sukcesu

✅ **Aplikacja działa bez błędów** - backend uruchamia się, frontend działa, nie ma crashy

✅ **Agenci działają poprawnie** - wszyscy 4 agenci uruchamiają się i zwracają sensowne odpowiedzi

✅ **Issues są poprawnie zapisywane** - każdy issue ma `agent_role`, są zapisywane bez duplikatów

✅ **Issues są poprawnie wyświetlane** - sekcja "Problemy" pokazuje wszystkie issues z informacją o agencie

✅ **Odpowiedzi agentów są czytelne** - nie ma surowego JSON, nie ma placeholderów, są sensowne odpowiedzi

✅ **Nie ma odniesień do moderatora** - w kodzie, UI i API nie ma żadnych śladów moderatora

## Instrukcje wykonania

1. **Przeczytaj cały kod** związany z review orchestrator (`backend/app/orchestrators/review.py`) i frontend (`ReviewDetail.tsx`, `ReviewConfigDialog.tsx`)

2. **Sprawdź wszystkie punkty z listy powyżej** - wykonaj systematycznie każdy test

3. **Dokumentuj znalezione problemy** - jeśli znajdziesz błędy, zapisz je wraz z lokalizacją w kodzie

4. **Napraw znalezione problemy** - jeśli znajdziesz błędy, popraw je natychmiast

5. **Zweryfikuj naprawy** - po naprawie błędów, sprawdź ponownie czy wszystko działa

6. **Przetestuj z rzeczywistymi modelami Ollama** - użyj `qwen2.5-coder:7b` lub `deepseek-coder:6.7b` i sprawdź jakość odpowiedzi

7. **Raport końcowy** - podsumuj co sprawdziłeś, co działa, co naprawiłeś (jeśli coś)

## Uwagi techniczne

- Upewnij się, że Ollama jest uruchomiony (`ollama serve`) przed testowaniem z modelami Ollama
- Sprawdź, czy modele są dostępne: `ollama list`
- Jeśli modele nie są dostępne, pobierz je: `ollama pull qwen2.5-coder:7b`
- Sprawdź logi backendu w czasie rzeczywistym podczas review
- Używaj narzędzi deweloperskich przeglądarki (F12) do sprawdzania błędów frontendu

## Oczekiwany rezultat

Po wykonaniu wszystkich testów, aplikacja powinna działać **całkowicie bez moderatora** - tylko 4 agenci zapisują issues bezpośrednio do bazy, a użytkownik widzi wszystkie issues w sekcji "Problemy" z informacją o tym, który agent znalazł każdy problem.
