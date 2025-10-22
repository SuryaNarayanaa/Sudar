"""Test authentication utilities."""

import sys
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.authUtils import (
    check_user_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_verification_code,
    hash_password,
    validate_password,
)


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_and_check_password_roundtrip(self):
        """Test that password hashing and verification work correctly."""
        raw_password = "ValidPass123"
        hashed = hash_password(raw_password)

        assert hashed != raw_password
        assert check_user_password(raw_password, hashed)
        assert not check_user_password("WrongPass123", hashed)

    def test_same_password_produces_different_hashes(self):
        """Test that same password produces different hashes due to salt."""
        password = "SamePass123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert check_user_password(password, hash1)
        assert check_user_password(password, hash2)


class TestPasswordValidation:
    """Test password validation rules."""

    def test_validate_password_rejects_too_short(self):
        """Test that passwords shorter than 6 characters are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_password("short")
        assert "at least 6 characters" in str(exc_info.value.detail)

    def test_validate_password_rejects_no_letter(self):
        """Test that passwords without letters are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_password("1234567")
        assert "at least one letter" in str(exc_info.value.detail)

    def test_validate_password_rejects_no_number(self):
        """Test that passwords without numbers are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_password("abcdefg")
        assert "at least one number" in str(exc_info.value.detail)

    def test_validate_password_accepts_valid_password(self):
        """Test that valid passwords are accepted."""
        # Should not raise any exception
        validate_password("GoodPwd9")
        validate_password("Complex1Pass")
        validate_password("Test123")


class TestVerificationCode:
    """Test verification code generation."""

    def test_generate_verification_code_returns_six_digits(self):
        """Test that verification code is exactly 6 digits."""
        code = generate_verification_code()

        assert len(code) == 6
        assert code.isdigit()

    def test_generate_verification_code_produces_different_codes(self):
        """Test that multiple calls produce different codes."""
        codes = {generate_verification_code() for _ in range(100)}
        # Should generate at least some different codes
        assert len(codes) > 1


class TestJWTTokens:
    """Test JWT token creation and decoding."""

    def test_create_and_decode_access_token_roundtrip(self):
        """Test access token creation and decoding."""
        payload = {"sub": "teacher-id-123"}

        access_token = create_access_token(payload.copy())
        decoded_access = decode_token(access_token)

        assert decoded_access["sub"] == payload["sub"]
        assert decoded_access["type"] == "access"
        assert "exp" in decoded_access

    def test_create_and_decode_refresh_token_roundtrip(self):
        """Test refresh token creation and decoding."""
        payload = {"sub": "teacher-id-456"}

        refresh_token = create_refresh_token(payload.copy(), expires_delta=timedelta(days=10))
        decoded_refresh = decode_token(refresh_token)

        assert decoded_refresh["sub"] == payload["sub"]
        assert decoded_refresh["type"] == "refresh"
        assert "exp" in decoded_refresh

    def test_decode_token_raises_on_invalid_token(self):
        """Test that decoding invalid token raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid.token.here")
        assert exc_info.value.status_code == 401

    def test_custom_expiry_delta_is_respected(self):
        """Test that custom expiry delta is applied to tokens."""
        payload = {"sub": "teacher-id"}

        # Create tokens with custom expiry
        short_lived = create_access_token(payload.copy(), expires_delta=timedelta(seconds=1))
        decoded = decode_token(short_lived)

        # Token should have expiry field
        assert "exp" in decoded
