#!/usr/bin/env python3
"""Create an admin user with a unique username/email.

Usage:
  python scripts/create_admin.py --email admin2@local.test --username admin2 --password Admin123!
"""
import argparse
import os
import sys

from sqlmodel import Session, select

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, create_db_and_tables
from app.models.user import User
from app.utils.auth import hash_password


def main():
    parser = argparse.ArgumentParser(description="Create admin user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    create_db_and_tables()

    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == args.email)).first()
        if existing:
            print(f"User already exists: {args.email}")
            return

        existing_username = session.exec(select(User).where(User.username == args.username)).first()
        if existing_username:
            print(f"Username already exists: {args.username}")
            return

        admin = User(
            email=args.email,
            username=args.username,
            hashed_password=hash_password(args.password),
            is_active=True,
            is_superuser=True,
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)

        print("Admin account created.")
        print(f"Email: {args.email}")
        print(f"Username: {args.username}")
        print(f"Password: {args.password}")


if __name__ == "__main__":
    main()

