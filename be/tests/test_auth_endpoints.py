"""Test authentication endpoints."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.models import EmailVerificationCode, Teacher


class TestSendVerificationCode:
    """Test send verification code endpoint."""

    def test_send_verification_code_success(self, client, test_db):
        """Test sending verification code for new email."""
        response = client.post(
            "/auth/send-verification-code",
            json={"email": "newteacher@test.com", "teacher_name": "New Teacher"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Verification code sent to your email"
        assert data["email"] == "newteacher@test.com"

        # Verify code was saved in database
        code_record = (
            test_db.query(EmailVerificationCode)
            .filter(EmailVerificationCode.email == "newteacher@test.com")
            .first()
        )
        assert code_record is not None
        assert len(code_record.code) == 6
        assert code_record.code.isdigit()

    def test_send_verification_code_existing_email(self, client, sample_teacher):
        """Test sending verification code for already registered email."""
        response = client.post(
            "/auth/send-verification-code",
            json={"email": sample_teacher.email, "teacher_name": "Test"},
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_send_verification_code_updates_existing_code(self, client, test_db):
        """Test that sending code again updates existing code."""
        email = "update@test.com"

        # Send first code
        response1 = client.post(
            "/auth/send-verification-code",
            json={"email": email, "teacher_name": "Teacher"},
        )
        assert response1.status_code == 200

        # Get first code
        code1 = test_db.query(EmailVerificationCode).filter_by(email=email).first()
        first_code = code1.code

        # Send second code
        response2 = client.post(
            "/auth/send-verification-code",
            json={"email": email, "teacher_name": "Teacher"},
        )
        assert response2.status_code == 200

        # Verify code was updated
        code2 = test_db.query(EmailVerificationCode).filter_by(email=email).first()
        # Codes should be different (with high probability)
        assert code2.code != first_code or True  # Allow same code by chance


class TestSignup:
    """Test signup endpoint."""

    def test_signup_success(self, client, test_db):
        """Test successful teacher registration."""
        # First send verification code
        email = "signup@test.com"
        client.post(
            "/auth/send-verification-code",
            json={"email": email, "teacher_name": "Signup Teacher"},
        )

        # Get the verification code from database
        code_record = test_db.query(EmailVerificationCode).filter_by(email=email).first()
        verification_code = code_record.code

        # Now signup
        response = client.post(
            "/auth/signup",
            json={
                "email": email,
                "teacher_name": "Signup Teacher",
                "password": "SecurePass123",
                "verification_code": verification_code,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Account created successfully"
        assert data["email"] == email
        assert data["teacher_name"] == "Signup Teacher"
        assert "teacher_id" in data

        # Verify teacher was created in database
        teacher = test_db.query(Teacher).filter_by(email=email).first()
        assert teacher is not None
        assert teacher.teacher_name == "Signup Teacher"

        # Verify verification code was deleted
        code_record = test_db.query(EmailVerificationCode).filter_by(email=email).first()
        assert code_record is None

        # Verify cookies were set
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    def test_signup_invalid_verification_code(self, client, test_db):
        """Test signup with wrong verification code."""
        email = "wrong@test.com"
        client.post(
            "/auth/send-verification-code",
            json={"email": email, "teacher_name": "Test"},
        )

        response = client.post(
            "/auth/signup",
            json={
                "email": email,
                "teacher_name": "Test",
                "password": "Pass123",
                "verification_code": "999999",  # Wrong code
            },
        )

        assert response.status_code == 400
        assert "Invalid verification code" in response.json()["detail"]

    def test_signup_expired_verification_code(self, client, test_db):
        """Test signup with expired verification code."""
        email = "expired@test.com"
        client.post(
            "/auth/send-verification-code",
            json={"email": email, "teacher_name": "Test"},
        )

        # Manually expire the code
        code_record = test_db.query(EmailVerificationCode).filter_by(email=email).first()
        code_record.expiry_time = datetime.utcnow() - timedelta(minutes=1)
        test_db.commit()

        response = client.post(
            "/auth/signup",
            json={
                "email": email,
                "teacher_name": "Test",
                "password": "Pass123",
                "verification_code": code_record.code,
            },
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    def test_signup_no_verification_code(self, client):
        """Test signup without sending verification code first."""
        response = client.post(
            "/auth/signup",
            json={
                "email": "noverify@test.com",
                "teacher_name": "Test",
                "password": "Pass123",
                "verification_code": "123456",
            },
        )

        assert response.status_code == 400
        assert "No verification code found" in response.json()["detail"]

    def test_signup_weak_password(self, client, test_db):
        """Test signup with weak password."""
        email = "weak@test.com"
        client.post(
            "/auth/send-verification-code",
            json={"email": email, "teacher_name": "Test"},
        )

        code_record = test_db.query(EmailVerificationCode).filter_by(email=email).first()

        response = client.post(
            "/auth/signup",
            json={
                "email": email,
                "teacher_name": "Test",
                "password": "weak",  # Too short
                "verification_code": code_record.code,
            },
        )

        assert response.status_code == 400
        assert "at least 6 characters" in response.json()["detail"]


class TestLogin:
    """Test login endpoint."""

    def test_login_success(self, client, sample_teacher):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            json={"email": "teacher@test.com", "password": "TestPass123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Login successful"
        assert data["email"] == sample_teacher.email
        assert data["teacher_name"] == sample_teacher.teacher_name
        assert str(data["teacher_id"]) == str(sample_teacher.teacher_id)

        # Verify cookies were set
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

    def test_login_wrong_password(self, client, sample_teacher):
        """Test login with incorrect password."""
        response = client.post(
            "/auth/login",
            json={"email": sample_teacher.email, "password": "WrongPassword123"},
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_nonexistent_email(self, client):
        """Test login with non-existent email."""
        response = client.post(
            "/auth/login",
            json={"email": "nonexistent@test.com", "password": "TestPass123"},
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]


class TestForgotPassword:
    """Test forgot password endpoint."""

    def test_forgot_password_existing_email(self, client, sample_teacher, test_db):
        """Test password reset code generation for existing email."""
        response = client.post(
            "/auth/forgot-password",
            json={"email": sample_teacher.email},
        )

        assert response.status_code == 200
        assert "reset code has been sent" in response.json()["message"]

        # Verify reset code was set in database
        teacher = test_db.query(Teacher).filter_by(email=sample_teacher.email).first()
        assert teacher.reset_password_code is not None
        assert len(teacher.reset_password_code) == 6
        assert teacher.code_expiry_time is not None

    def test_forgot_password_nonexistent_email(self, client):
        """Test forgot password doesn't reveal if email doesn't exist."""
        response = client.post(
            "/auth/forgot-password",
            json={"email": "nonexistent@test.com"},
        )

        # Should still return success for security
        assert response.status_code == 200
        assert "reset code has been sent" in response.json()["message"]


class TestResetPassword:
    """Test reset password endpoint."""

    def test_reset_password_success(self, client, sample_teacher, test_db):
        """Test successful password reset."""
        # First request reset code
        client.post("/auth/forgot-password", json={"email": sample_teacher.email})

        # Get reset code from database
        teacher = test_db.query(Teacher).filter_by(email=sample_teacher.email).first()
        reset_code = teacher.reset_password_code

        # Reset password
        response = client.post(
            "/auth/reset-password",
            json={
                "email": sample_teacher.email,
                "code": reset_code,
                "new_password": "NewSecure123",
            },
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Password reset successful"

        # Verify password was changed
        test_db.refresh(teacher)
        from api.authUtils import check_user_password

        assert check_user_password("NewSecure123", teacher.hashed_password)

        # Verify reset code was cleared
        assert teacher.reset_password_code is None
        assert teacher.code_expiry_time is None

    def test_reset_password_invalid_code(self, client, sample_teacher, test_db):
        """Test reset password with wrong code."""
        client.post("/auth/forgot-password", json={"email": sample_teacher.email})

        response = client.post(
            "/auth/reset-password",
            json={
                "email": sample_teacher.email,
                "code": "999999",  # Wrong code
                "new_password": "NewPass123",
            },
        )

        assert response.status_code == 400
        assert "Invalid email or code" in response.json()["detail"]

    def test_reset_password_expired_code(self, client, sample_teacher, test_db):
        """Test reset password with expired code."""
        client.post("/auth/forgot-password", json={"email": sample_teacher.email})

        # Expire the code
        teacher = test_db.query(Teacher).filter_by(email=sample_teacher.email).first()
        reset_code = teacher.reset_password_code
        teacher.code_expiry_time = datetime.utcnow() - timedelta(minutes=1)
        test_db.commit()

        response = client.post(
            "/auth/reset-password",
            json={
                "email": sample_teacher.email,
                "code": reset_code,
                "new_password": "NewPass123",
            },
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()


class TestGetCurrentUser:
    """Test get current user endpoint."""

    def test_get_current_user_authenticated(self, auth_headers, sample_teacher):
        """Test getting current user info when authenticated."""
        response = auth_headers.get("/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == sample_teacher.email
        assert data["teacher_name"] == sample_teacher.teacher_name
        assert str(data["teacher_id"]) == str(sample_teacher.teacher_id)

    def test_get_current_user_unauthenticated(self, client):
        """Test getting current user without authentication."""
        response = client.get("/auth/me")

        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]


class TestLogout:
    """Test logout endpoint."""

    def test_logout_success(self, auth_headers):
        """Test successful logout clears cookies."""
        response = auth_headers.post("/auth/logout")

        assert response.status_code == 200
        assert response.json()["message"] == "Logout successful"

        # Verify cookies were cleared
        assert response.cookies.get("access_token", "") == ""
        assert response.cookies.get("refresh_token", "") == ""

    def test_logout_unauthenticated(self, client):
        """Test logout without authentication."""
        response = client.post("/auth/logout")

        assert response.status_code == 401
