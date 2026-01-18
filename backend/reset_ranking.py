#!/usr/bin/env python3
"""Skrypt do wyzerowania rankingu w bazie danych.

Usuwa:
- Wszystkie sesje Arena
- Wszystkie oceny zespołów (TeamRating)
- Wszystkie review
- Wszystkie agentów review
- Wszystkie problemy (issues)
- Wszystkie sugestie

Zachowuje:
- Użytkowników (User)
- Projekty (Project)
- Pliki (File)
"""
import sys
from pathlib import Path

# Dodaj backend do path
sys.path.insert(0, str(Path(__file__).parent))

from sqlmodel import Session, select
from app.database import engine
from app.models.review import Review, ReviewAgent, Issue, Suggestion
from app.models.arena import ArenaSession, TeamRating
from app.models.conversation import Conversation, Message


def reset_ranking():
    """Wyzeruj ranking usuwając dane z bazy."""
    with Session(engine) as session:
        print("🔄 Rozpoczynam zerowanie rankingu...")

        # Policz ile danych przed usunięciem
        arena_count = len(session.exec(select(ArenaSession)).all())
        team_rating_count = len(session.exec(select(TeamRating)).all())
        review_count = len(session.exec(select(Review)).all())
        agent_count = len(session.exec(select(ReviewAgent)).all())
        issue_count = len(session.exec(select(Issue)).all())
        suggestion_count = len(session.exec(select(Suggestion)).all())
        conversation_count = len(session.exec(select(Conversation)).all())
        message_count = len(session.exec(select(Message)).all())

        print(f"\n📊 Obecny stan bazy danych:")
        print(f"  - ArenaSession: {arena_count}")
        print(f"  - TeamRating: {team_rating_count}")
        print(f"  - Review: {review_count}")
        print(f"  - ReviewAgent: {agent_count}")
        print(f"  - Issue: {issue_count}")
        print(f"  - Suggestion: {suggestion_count}")
        print(f"  - Conversation: {conversation_count}")
        print(f"  - Message: {message_count}")

        if arena_count == 0 and review_count == 0 and issue_count == 0:
            print("\n✅ Baza już pusta - ranking już wyzerowany!")
            return

        # Usuń dane w kolejności (od zależnych do niezależnych)
        print("\n🗑️  Usuwam dane...")

        # 1. Messages (zależne od Conversations)
        messages = session.exec(select(Message)).all()
        for m in messages:
            session.delete(m)
        print(f"  ✓ Usunięto {message_count} messages")

        # 2. Conversations (zależne od Reviews)
        conversations = session.exec(select(Conversation)).all()
        for c in conversations:
            session.delete(c)
        print(f"  ✓ Usunięto {conversation_count} conversations")

        # 3. Suggestions (zależne od Issues)
        suggestions = session.exec(select(Suggestion)).all()
        for s in suggestions:
            session.delete(s)
        print(f"  ✓ Usunięto {suggestion_count} suggestions")

        # 4. Issues (zależne od Reviews)
        issues = session.exec(select(Issue)).all()
        for i in issues:
            session.delete(i)
        print(f"  ✓ Usunięto {issue_count} issues")

        # 5. ReviewAgents (zależne od Reviews)
        agents = session.exec(select(ReviewAgent)).all()
        for a in agents:
            session.delete(a)
        print(f"  ✓ Usunięto {agent_count} review agents")

        # 6. TeamRatings (zależne od ArenaSession)
        team_ratings = session.exec(select(TeamRating)).all()
        for tr in team_ratings:
            session.delete(tr)
        print(f"  ✓ Usunięto {team_rating_count} team ratings")

        # 7. Reviews (niezależne)
        reviews = session.exec(select(Review)).all()
        for r in reviews:
            session.delete(r)
        print(f"  ✓ Usunięto {review_count} reviews")

        # 8. ArenaSessions (niezależne)
        arenas = session.exec(select(ArenaSession)).all()
        for arena in arenas:
            session.delete(arena)
        print(f"  ✓ Usunięto {arena_count} arena sessions")

        # Commit wszystkie zmiany
        session.commit()

        print("\n✅ Ranking wyzerowany pomyślnie!")
        print("📊 Zachowane dane:")
        print("  - Użytkownicy (User)")
        print("  - Projekty (Project)")
        print("  - Pliki (File)")


if __name__ == "__main__":
    try:
        reset_ranking()
    except Exception as e:
        print(f"\n❌ Błąd: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
