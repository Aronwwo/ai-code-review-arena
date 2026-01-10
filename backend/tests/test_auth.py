"""Tests for authentication endpoints."""
import pytest


def test_register_user(client):
    """Test user registration."""
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "Testpass123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert "id" in data


def test_register_duplicate_email(client):
    """Test registration with duplicate email."""
    # First registration
    client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser1",
            "password": "Testpass123"
        }
    )

    # Duplicate registration
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser2",
            "password": "Testpass123"
        }
    )
    assert response.status_code == 400
    assert "zarejestrowany" in response.json()["detail"].lower() or "already registered" in response.json()["detail"].lower()


def test_login(client):
    """Test user login."""
    # Register first
    client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "Testpass123"
        }
    )

    # Login
    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "Testpass123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post(
        "/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "WrongPassword123"
        }
    )
    assert response.status_code == 401
