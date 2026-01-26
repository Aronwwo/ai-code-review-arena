"""Tests for JWT token validation including type checking."""
import pytest
from fastapi import HTTPException
from jose import jwt
from app.config import settings
from app.api.deps import get_current_user_from_token
from app.models.user import User
from sqlmodel import Session


class TestJWTValidation:
    """Test JWT token validation and security."""

    def test_valid_jwt_token(self, session: Session):
        """Test that valid JWT token with int user_id works."""
        # Create test user
        user = User(
            email="jwt@test.com",
            hashed_password="hashed",
            username="jwtuser"
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        # Create valid token
        payload = {"user_id": user.id, "sub": user.email}
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

        # Should not raise
        result = get_current_user_from_token(token, session)
        assert result.id == user.id

    def test_jwt_with_string_user_id(self, session: Session):
        """Test that JWT with string user_id is rejected."""
        # Create token with string user_id (injection attempt)
        payload = {"user_id": "1 OR 1=1", "sub": "hacker@test.com"}
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            get_current_user_from_token(token, session)

        assert exc_info.value.status_code == 401
        assert "Invalid token format" in str(exc_info.value.detail)

    def test_jwt_with_float_user_id(self, session: Session):
        """Test that JWT with float user_id is rejected."""
        payload = {"user_id": 1.5, "sub": "test@test.com"}
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_from_token(token, session)

        assert exc_info.value.status_code == 401

    def test_jwt_with_null_user_id(self, session: Session):
        """Test that JWT with null user_id is rejected."""
        payload = {"user_id": None, "sub": "test@test.com"}
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_from_token(token, session)

        assert exc_info.value.status_code == 401

    def test_jwt_with_negative_user_id(self, session: Session):
        """Test that JWT with negative user_id fails to find user."""
        payload = {"user_id": -1, "sub": "test@test.com"}
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

        # Should not crash, but user won't be found
        with pytest.raises(HTTPException) as exc_info:
            get_current_user_from_token(token, session)

        # User not found in database
        assert exc_info.value.status_code == 401

    def test_jwt_with_array_user_id(self, session: Session):
        """Test that JWT with array user_id is rejected."""
        payload = {"user_id": [1, 2, 3], "sub": "test@test.com"}
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_from_token(token, session)

        assert exc_info.value.status_code == 401
        assert "Invalid token format" in str(exc_info.value.detail)

    def test_jwt_with_object_user_id(self, session: Session):
        """Test that JWT with object user_id is rejected."""
        payload = {"user_id": {"id": 1}, "sub": "test@test.com"}
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_from_token(token, session)

        assert exc_info.value.status_code == 401
