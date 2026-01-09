"""Tests for email validation."""
import pytest
from app.models.user import validate_email_format


def test_validate_email_format_valid():
    """Test validation accepts valid emails."""
    valid_emails = [
        "user@example.com",
        "test.user@example.co.uk",
        "user+tag@example.com",
        "user_name@example-domain.com",
        "123@example.com",
        "USER@EXAMPLE.COM",  # Should normalize to lowercase
    ]

    for email in valid_emails:
        result = validate_email_format(email)
        assert result == email.lower(), f"Failed for {email}"


def test_validate_email_format_development_tlds():
    """Test validation accepts .test and .local TLDs for development."""
    dev_emails = [
        "admin@local.test",
        "user@localhost.test",
        "test@example.local",
    ]

    for email in dev_emails:
        result = validate_email_format(email)
        assert result == email.lower(), f"Failed for development email {email}"


def test_validate_email_format_invalid_no_at():
    """Test validation rejects emails without @."""
    with pytest.raises(ValueError, match="nieprawidłowy format email"):
        validate_email_format("notanemail.com")


def test_validate_email_format_invalid_empty():
    """Test validation rejects empty email."""
    with pytest.raises(ValueError, match="nieprawidłowy format email"):
        validate_email_format("")


def test_validate_email_format_invalid_no_domain():
    """Test validation rejects email without domain."""
    with pytest.raises(ValueError, match="nieprawidłowy format email"):
        validate_email_format("user@")


def test_validate_email_format_invalid_no_username():
    """Test validation rejects email without username."""
    with pytest.raises(ValueError, match="nieprawidłowy format email"):
        validate_email_format("@example.com")


def test_validate_email_format_invalid_no_tld():
    """Test validation rejects email without TLD."""
    with pytest.raises(ValueError, match="nieprawidłowy format email"):
        validate_email_format("user@example")


def test_validate_email_format_invalid_spaces():
    """Test validation rejects emails with spaces."""
    with pytest.raises(ValueError, match="nieprawidłowy format email"):
        validate_email_format("user name@example.com")


def test_validate_email_format_invalid_special_chars():
    """Test validation rejects emails with invalid special characters."""
    invalid_emails = [
        "user#@example.com",
        "user@exam ple.com",
        "user@@example.com",
    ]

    for email in invalid_emails:
        with pytest.raises(ValueError, match="nieprawidłowy format email"):
            validate_email_format(email)


def test_validate_email_format_normalizes_case():
    """Test validation normalizes email to lowercase."""
    email = "User.Name@Example.COM"
    result = validate_email_format(email)
    assert result == "user.name@example.com"


def test_validate_email_format_strips_nothing():
    """Test validation doesn't strip whitespace (should fail instead)."""
    with pytest.raises(ValueError, match="nieprawidłowy format email"):
        validate_email_format(" user@example.com ")


def test_validate_email_format_multiple_dots():
    """Test validation accepts multiple dots in username."""
    email = "user.name.test@example.com"
    result = validate_email_format(email)
    assert result == email.lower()


def test_validate_email_format_hyphen_domain():
    """Test validation accepts hyphens in domain."""
    email = "user@my-domain.com"
    result = validate_email_format(email)
    assert result == email


def test_validate_email_format_subdomain():
    """Test validation accepts subdomains."""
    email = "user@mail.example.com"
    result = validate_email_format(email)
    assert result == email


def test_validate_email_format_long_tld():
    """Test validation accepts long TLDs."""
    email = "user@example.photography"
    result = validate_email_format(email)
    assert result == email
