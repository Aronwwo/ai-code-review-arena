#!/usr/bin/env python3
"""Reset admin password."""
from sqlmodel import Session, select
from app.database import engine
from app.models.user import User
from app.utils.auth import hash_password

with Session(engine) as session:
    # Find admin user
    stmt = select(User).where(User.email == "admin@local.test")
    admin = session.exec(stmt).first()

    if admin:
        # Reset password
        admin.hashed_password = hash_password("Admin123!")
        session.add(admin)
        session.commit()
        print(f"✅ Hasło zresetowane dla: {admin.email}")
        print(f"   Username: {admin.username}")
        print(f"   Nowe hasło: Admin123!")
        print()
        print("Możesz się teraz zalogować:")
        print(f"   Email: {admin.email}")
        print(f"   Hasło: Admin123!")
    else:
        print("❌ Użytkownik admin nie znaleziony")
        print("Tworzę nowego użytkownika admin...")

        admin = User(
            email="admin@local.test",
            username="admin",
            hashed_password=hash_password("Admin123!"),
            is_active=True,
            is_superuser=True
        )
        session.add(admin)
        session.commit()
        print(f"✅ Utworzono użytkownika: {admin.email}")
        print(f"   Username: {admin.username}")
        print(f"   Hasło: Admin123!")
