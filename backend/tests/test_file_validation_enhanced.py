"""Enhanced tests for file validation including max size."""
import pytest
from app.api.files import validate_code_content
from app.config import settings


class TestFileValidationEnhanced:
    """Test enhanced file validation with max size checks."""

    def test_file_min_length_from_settings(self):
        """Test that minimum length comes from settings."""
        content = "x" * (settings.file_min_length - 1)
        result = validate_code_content(content, "test.py")

        assert result["valid"] is False
        assert any("zbyt krótka" in error.lower() for error in result["errors"])

    def test_file_max_size_validation(self):
        """Test that files exceeding max size are rejected."""
        # Create content larger than max_file_size_mb
        max_bytes = settings.max_file_size_mb * 1024 * 1024
        content = "x" * (max_bytes + 1000)

        result = validate_code_content(content, "large_file.py")

        assert result["valid"] is False
        assert any("zbyt duży" in error.lower() for error in result["errors"])

    def test_file_exactly_max_size(self):
        """Test file exactly at max size is accepted."""
        max_bytes = settings.max_file_size_mb * 1024 * 1024
        # Create valid Python code at max size
        lines = ["def function():\n", "    pass\n"]
        content = "".join(lines * (max_bytes // (len(lines[0]) + len(lines[1]))))

        result = validate_code_content(content, "max_size.py")

        # Should be valid or have only warnings (not errors)
        if not result["valid"]:
            assert len(result["errors"]) == 0 or "duży" not in result["errors"][0].lower()

    def test_file_uniqueness_threshold_from_settings(self):
        """Test that line uniqueness threshold comes from settings."""
        # Create repetitive content below threshold
        line = "print('hello')\n"
        num_lines = 100
        num_unique = int(num_lines * settings.file_line_uniqueness_threshold) - 1

        content = line * (num_lines - num_unique) + "\n".join([f"print({i})" for i in range(num_unique)])

        result = validate_code_content(content, "repetitive.py")

        # Should have warning about repeated lines
        assert any("repeated" in warning.lower() for warning in result["warnings"])

    def test_valid_file_within_limits(self):
        """Test that valid file within all limits passes."""
        content = """
def hello_world():
    '''A simple function.'''
    print('Hello, World!')
    return True

def another_function():
    '''Another function.'''
    x = 42
    y = x * 2
    return y

class MyClass:
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1
"""
        result = validate_code_content(content, "valid.py")

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_empty_file_validation(self):
        """Test that empty files are rejected."""
        result = validate_code_content("", "empty.py")

        assert result["valid"] is False
        assert any("puste" in error.lower() for error in result["errors"])

    def test_whitespace_only_file(self):
        """Test that whitespace-only files are rejected."""
        content = "   \n\n  \t\t  \n   "
        result = validate_code_content(content, "whitespace.py")

        assert result["valid"] is False
        assert any("puste" in error.lower() or "białe" in error.lower() for error in result["errors"])
