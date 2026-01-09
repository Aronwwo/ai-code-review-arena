"""Initialize database with sample data."""
import asyncio
from sqlmodel import Session, select
from app.database import engine
from app.models.user import User
from app.models.project import Project
from app.models.file import File
from app.utils.auth import hash_password


def create_sample_data():
    """Create sample data for testing."""
    with Session(engine) as session:
        # Check if data already exists
        statement = select(User).where(User.email == "demo@example.com")
        existing_user = session.exec(statement).first()

        if existing_user:
            print("Sample data already exists. Skipping...")
            return

        # Create demo user
        demo_user = User(
            email="demo@example.com",
            username="demo",
            hashed_password=hash_password("demo123"),
            is_active=True
        )
        session.add(demo_user)
        session.commit()
        session.refresh(demo_user)

        print(f"Created demo user: {demo_user.email}")

        # Create sample project
        project = Project(
            name="Sample Web App",
            description="A demo project for testing the AI Code Review Arena",
            owner_id=demo_user.id
        )
        session.add(project)
        session.commit()
        session.refresh(project)

        print(f"Created project: {project.name}")

        # Add sample files
        sample_files = [
            {
                "name": "app.py",
                "language": "python",
                "content": '''"""Main application module."""
from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

@app.route('/api/users/<user_id>')
def get_user(user_id):
    # SQL injection vulnerability - user input not sanitized
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id = {user_id}"  # VULNERABLE!
    cursor.execute(query)
    result = cursor.fetchone()
    conn.close()
    return jsonify(result)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data['username']
    password = data['password']

    # Hardcoded API key - security issue
    API_KEY = "sk-1234567890abcdef"

    # Password not hashed - security issue
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?",
                   (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"success": True, "api_key": API_KEY})
    return jsonify({"success": False}), 401

if __name__ == '__main__':
    app.run(debug=True)
'''
            },
            {
                "name": "utils.py",
                "language": "python",
                "content": '''"""Utility functions."""

def processData(data):  # Style issue - should be process_data
    results = []
    # Performance issue - N+1 query pattern
    for item in data:
        # This would cause a separate DB query for each item
        details = fetch_details(item.id)
        results.append(details)
    return results

def fetch_details(item_id):
    """Fetch details for an item."""
    # Simulated database query
    import time
    time.sleep(0.1)  # Performance issue - blocking operation
    return {"id": item_id, "data": "..."}

def load_file(filename):
    # Missing error handling
    with open(filename, 'r') as f:
        data = f.read()  # Performance issue - loads entire file into memory
    return data
'''
            }
        ]

        for file_data in sample_files:
            file = File(
                project_id=project.id,
                name=file_data["name"],
                content=file_data["content"],
                language=file_data["language"],
                size_bytes=len(file_data["content"].encode('utf-8')),
                content_hash=File.compute_hash(file_data["content"])
            )
            session.add(file)
            print(f"Added file: {file.name}")

        session.commit()

        print("\n✅ Sample data created successfully!")
        print("\nDemo credentials:")
        print("  Email: demo@example.com")
        print("  Password: demo123")
        print("\nYou can now:")
        print("  1. Login with these credentials")
        print("  2. View the 'Sample Web App' project")
        print("  3. Run a code review on the sample files")
        print("  4. See realistic security, performance, and style issues")


if __name__ == "__main__":
    create_sample_data()
