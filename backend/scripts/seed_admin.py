#!/usr/bin/env python3
"""Seed admin account for AI Code Review Arena.

This script is idempotent - it will create the admin account if it doesn't exist,
or skip if it already exists.

Admin credentials:
  Email:    admin@local.test
  Password: Admin123!
  Username: admin
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.database import engine, create_db_and_tables
from app.models.user import User
from app.utils.auth import hash_password


ADMIN_EMAIL = "admin@local.test"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin123!"


def seed_admin():
    """Create admin account if it doesn't exist."""
    # Ensure tables exist
    create_db_and_tables()

    with Session(engine) as session:
        # Check if admin already exists
        statement = select(User).where(User.email == ADMIN_EMAIL)
        existing = session.exec(statement).first()

        if existing:
            print(f"Admin account already exists: {ADMIN_EMAIL}")
            print("Skipping creation.")
            return existing

        # Create admin account
        admin = User(
            email=ADMIN_EMAIL,
            username=ADMIN_USERNAME,
            hashed_password=hash_password(ADMIN_PASSWORD),
            is_active=True,
            is_superuser=True
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)

        print("=" * 50)
        print("  Admin account created successfully!")
        print("=" * 50)
        print()
        print("  Credentials:")
        print(f"    Email:    {ADMIN_EMAIL}")
        print(f"    Password: {ADMIN_PASSWORD}")
        print(f"    Username: {ADMIN_USERNAME}")
        print()
        print("=" * 50)

        return admin


def seed_demo_data():
    """Optionally seed demo project and files."""
    with Session(engine) as session:
        # Check if demo project exists
        from app.models.project import Project

        statement = select(Project).where(Project.name == "Demo Project")
        existing = session.exec(statement).first()

        if existing:
            print("Demo project already exists. Skipping.")
            return

        # Get admin user
        admin_stmt = select(User).where(User.email == ADMIN_EMAIL)
        admin = session.exec(admin_stmt).first()

        if not admin:
            print("Admin not found. Run seed_admin first.")
            return

        # Create demo project
        project = Project(
            name="Demo Project",
            description="A sample project with intentional issues for testing code review",
            owner_id=admin.id
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        # Add sample files
        from app.models.file import File

        sample_code = '''"""Sample module with intentional issues."""

# Security issue: hardcoded credentials
API_KEY = "sk-12345-secret-key"
DATABASE_PASSWORD = "admin123"

def get_user(user_id):
    """Get user by ID - has SQL injection vulnerability."""
    import sqlite3
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    # VULNERABLE: String interpolation in SQL
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchone()

def process_items(items):
    """Process items - has N+1 query issue."""
    results = []
    for item in items:
        # N+1 problem: query in loop
        details = fetch_item_details(item.id)
        results.append(details)
    return results

def getUserName(userId):
    """Get username - style issue: camelCase instead of snake_case."""
    pass

class user:
    """User class - style issue: should be PascalCase."""
    pass
'''

        file = File(
            project_id=project.id,
            name="sample.py",
            content=sample_code,
            language="python",
            size_bytes=len(sample_code.encode('utf-8')),
            content_hash=File.compute_hash(sample_code)
        )
        session.add(file)
        session.commit()

        print(f"Created demo project: {project.name}")


if __name__ == "__main__":
    seed_admin()
    seed_demo_data()
