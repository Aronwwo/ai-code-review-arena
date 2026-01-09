"""Tests for file content validation."""
import pytest
from app.api.files import validate_code_content


def test_validate_code_content_valid_python():
    """Test validation of valid Python code."""
    code = """
def hello_world():
    print("Hello, World!")
    return True
"""
    result = validate_code_content(code, "test.py")
    assert result["valid"] is True
    assert len(result["errors"]) == 0
    assert len(result["warnings"]) == 0


def test_validate_code_content_empty():
    """Test validation rejects empty content."""
    result = validate_code_content("", "test.py")
    assert result["valid"] is False
    assert any("puste" in err.lower() for err in result["errors"])


def test_validate_code_content_too_short():
    """Test validation rejects very short content."""
    result = validate_code_content("abc", "test.py")
    assert result["valid"] is False
    assert any("minimum" in err.lower() for err in result["errors"])


def test_validate_code_content_whitespace_only():
    """Test validation rejects whitespace-only content."""
    result = validate_code_content("   \n\n\t\t   ", "test.py")
    assert result["valid"] is False
    assert any("puste" in err.lower() or "whitespace" in err.lower() for err in result["errors"])


def test_validate_code_content_non_printable_characters():
    """Test validation warns about non-printable characters."""
    code_with_null = "def test():\x00\n    pass"
    result = validate_code_content(code_with_null, "test.py")
    assert len(result["warnings"]) > 0
    assert any("non-printable" in warn.lower() for warn in result["warnings"])


def test_validate_code_content_repeated_lines():
    """Test validation warns about repeated content."""
    repeated_code = "print('test')\n" * 100
    result = validate_code_content(repeated_code, "test.py")
    assert len(result["warnings"]) > 0
    assert any("powtarzające" in warn.lower() or "repeated" in warn.lower() for warn in result["warnings"])


def test_validate_code_content_normal_repetition():
    """Test validation allows normal code repetition."""
    normal_code = """
def test1():
    return True

def test2():
    return True

def test3():
    return True
"""
    result = validate_code_content(normal_code, "test.py")
    # Should be valid - normal function definitions
    assert result["valid"] is True


def test_validate_code_content_various_languages():
    """Test validation works with different file extensions."""
    js_code = "function test() { return true; }"
    result = validate_code_content(js_code, "test.js")
    assert result["valid"] is True

    java_code = "public class Test { public static void main(String[] args) {} }"
    result = validate_code_content(java_code, "Test.java")
    assert result["valid"] is True

    cpp_code = "#include <iostream>\nint main() { return 0; }"
    result = validate_code_content(cpp_code, "test.cpp")
    assert result["valid"] is True


def test_validate_code_content_unicode():
    """Test validation handles Unicode characters properly."""
    unicode_code = """
def привет():  # Russian comment
    return "cześć"  # Polish greeting
"""
    result = validate_code_content(unicode_code, "test.py")
    assert result["valid"] is True


def test_validate_code_content_long_file():
    """Test validation handles large files."""
    long_code = "# Comment\n" * 1000 + "def test():\n    pass"
    result = validate_code_content(long_code, "test.py")
    assert result["valid"] is True
