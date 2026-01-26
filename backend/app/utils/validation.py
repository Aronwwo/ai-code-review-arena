"""Shared validation utilities for email, password, and other inputs.

This module provides centralized validation logic to maintain consistency
across the application and follow DRY principle.
"""
import re


def validate_email_format(email: str) -> bool:
    """Validate email address format using regex pattern.

    Args:
        email: Email address to validate

    Returns:
        True if email format is valid, False otherwise

    Examples:
        >>> validate_email_format("user@example.com")
        True
        >>> validate_email_format("invalid.email")
        False
    """
    if not email or not isinstance(email, str):
        return False

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength according to security requirements.

    Password must meet the following criteria:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit

    Args:
        password: Password string to validate

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if password meets all criteria
        - error_message: Empty string if valid, descriptive error otherwise

    Examples:
        >>> validate_password_strength("StrongPass123")
        (True, "")
        >>> validate_password_strength("weak")
        (False, "Password must be at least 8 characters long")
    """
    if not password or not isinstance(password, str):
        return False, "Password is required"

    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"

    # Optional: Check for common weak passwords
    common_passwords = ['password', '12345678', 'qwerty123', 'abc123']
    if password.lower() in common_passwords:
        return False, "Password is too common, please choose a stronger password"

    return True, ""


def validate_username(username: str) -> tuple[bool, str]:
    """Validate username format.

    Username must meet the following criteria:
    - At least 3 characters long
    - Maximum 30 characters
    - Contains only alphanumeric characters, underscores, and hyphens
    - Starts with a letter

    Args:
        username: Username to validate

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_username("john_doe")
        (True, "")
        >>> validate_username("ab")
        (False, "Username must be at least 3 characters long")
    """
    if not username or not isinstance(username, str):
        return False, "Username is required"

    if len(username) < 3:
        return False, "Username must be at least 3 characters long"

    if len(username) > 30:
        return False, "Username must be at most 30 characters long"

    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', username):
        return False, "Username must start with a letter and contain only letters, numbers, underscores, and hyphens"

    return True, ""
