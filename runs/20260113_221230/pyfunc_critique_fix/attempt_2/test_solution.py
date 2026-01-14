"""Tests for normalize_phone function."""

import pytest
from solution import normalize_phone


def test_ten_digits():
    """Test 10-digit phone number formatting."""
    assert normalize_phone("1234567890") == "123-456-7890"


def test_ten_digits_with_symbols():
    """Test stripping non-digits from 10-digit number."""
    assert normalize_phone("(123) 456-7890") == "123-456-7890"
    assert normalize_phone("123.456.7890") == "123-456-7890"


def test_eleven_digits_with_leading_one():
    """Test 11-digit number starting with 1."""
    assert normalize_phone("11234567890") == "123-456-7890"
    assert normalize_phone("1-123-456-7890") == "123-456-7890"


def test_invalid_length():
    """Test that invalid lengths raise ValueError."""
    with pytest.raises(ValueError):
        normalize_phone("123456789")  # 9 digits
    with pytest.raises(ValueError):
        normalize_phone("12345678901")  # 11 digits not starting with 1
    with pytest.raises(ValueError):
        normalize_phone("123456789012")  # 12 digits


def test_eleven_digits_not_starting_with_one():
    """Test 11 digits not starting with 1 raises ValueError."""
    with pytest.raises(ValueError):
        normalize_phone("21234567890")
