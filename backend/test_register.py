"""Quick test for registration."""
import sys
sys.path.insert(0, "C:\\Users\\aronw\\Desktop\\programowaniewint\\backend")

from app.database import Session, engine
from app.models.user import User
from app.utils.auth import hash_password

def test_register():
    try:
        with Session(engine) as session:
            # Create user
            user = User(
                email="test@example.com",
                username="testuser",
                hashed_password=hash_password("password123")
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            print(f"✅ User created successfully!")
            print(f"   ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Username: {user.username}")
            return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_register()
    sys.exit(0 if success else 1)
