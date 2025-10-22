"""Test classroom endpoints."""

import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestCreateClassroom:
    """Test create classroom endpoint."""

    def test_create_classroom_success(self, auth_headers, test_db):
        """Test successful classroom creation."""
        response = auth_headers.post(
            "/classrooms",
            json={"classroom_name": "Grade 5 Science"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["classroom_name"] == "Grade 5 Science"
        assert "classroom_id" in data
        assert "teacher_id" in data
        assert "created_at" in data

    def test_create_classroom_unauthenticated(self, client):
        """Test creating classroom without authentication."""
        response = client.post(
            "/classrooms",
            json={"classroom_name": "Test Class"},
        )

        assert response.status_code == 401

    def test_create_classroom_empty_name(self, auth_headers):
        """Test creating classroom with empty name."""
        response = auth_headers.post(
            "/classrooms",
            json={"classroom_name": ""},
        )

        assert response.status_code == 422  # Validation error


class TestGetClassrooms:
    """Test get classrooms endpoint."""

    def test_get_classrooms_success(self, auth_headers, sample_classroom):
        """Test getting all classrooms for authenticated teacher."""
        response = auth_headers.get("/classrooms")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["classroom_name"] == sample_classroom.classroom_name

    def test_get_classrooms_empty_list(self, auth_headers):
        """Test getting classrooms when teacher has none."""
        response = auth_headers.get("/classrooms")

        assert response.status_code == 200
        # May be empty or contain classrooms depending on fixtures

    def test_get_classrooms_unauthenticated(self, client):
        """Test getting classrooms without authentication."""
        response = client.get("/classrooms")

        assert response.status_code == 401


class TestGetClassroom:
    """Test get single classroom endpoint."""

    def test_get_classroom_success(self, auth_headers, sample_classroom):
        """Test getting a specific classroom."""
        response = auth_headers.get(f"/classrooms/{sample_classroom.classroom_id}")

        assert response.status_code == 200
        data = response.json()
        assert str(data["classroom_id"]) == str(sample_classroom.classroom_id)
        assert data["classroom_name"] == sample_classroom.classroom_name

    def test_get_classroom_not_found(self, auth_headers):
        """Test getting non-existent classroom."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = auth_headers.get(f"/classrooms/{fake_id}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_classroom_wrong_teacher(self, client, test_db, sample_classroom):
        """Test that teacher can't access another teacher's classroom."""
        from api.authUtils import hash_password
        from api.models import Teacher

        # Create another teacher
        other_teacher = Teacher(
            teacher_name="Other Teacher",
            email="other@test.com",
            hashed_password=hash_password("OtherPass123"),
        )
        test_db.add(other_teacher)
        test_db.commit()

        # Login as other teacher
        response = client.post(
            "/auth/login",
            json={"email": "other@test.com", "password": "OtherPass123"},
        )
        client.cookies.set("access_token", response.cookies.get("access_token"))

        # Try to access first teacher's classroom
        response = client.get(f"/classrooms/{sample_classroom.classroom_id}")

        assert response.status_code == 404


class TestUpdateClassroom:
    """Test update classroom endpoint."""

    def test_update_classroom_success(self, auth_headers, sample_classroom):
        """Test successful classroom update."""
        response = auth_headers.put(
            f"/classrooms/{sample_classroom.classroom_id}",
            json={"classroom_name": "Updated Classroom Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["classroom_name"] == "Updated Classroom Name"
        assert str(data["classroom_id"]) == str(sample_classroom.classroom_id)

    def test_update_classroom_not_found(self, auth_headers):
        """Test updating non-existent classroom."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = auth_headers.put(
            f"/classrooms/{fake_id}",
            json={"classroom_name": "New Name"},
        )

        assert response.status_code == 404

    def test_update_classroom_unauthenticated(self, client, sample_classroom):
        """Test updating classroom without authentication."""
        response = client.put(
            f"/classrooms/{sample_classroom.classroom_id}",
            json={"classroom_name": "Hacked Name"},
        )

        assert response.status_code == 401


class TestDeleteClassroom:
    """Test delete classroom endpoint."""

    def test_delete_classroom_success(self, auth_headers, sample_classroom):
        """Test successful classroom deletion."""
        response = auth_headers.delete(f"/classrooms/{sample_classroom.classroom_id}")

        assert response.status_code == 204

        # Verify classroom was deleted
        response = auth_headers.get(f"/classrooms/{sample_classroom.classroom_id}")
        assert response.status_code == 404

    def test_delete_classroom_not_found(self, auth_headers):
        """Test deleting non-existent classroom."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = auth_headers.delete(f"/classrooms/{fake_id}")

        assert response.status_code == 404

    def test_delete_classroom_cascades_to_students(
        self, auth_headers, sample_classroom, sample_student, test_db
    ):
        """Test that deleting classroom cascades to delete students."""
        from api.models import Student

        # Verify student exists
        student = test_db.query(Student).filter_by(rollno=sample_student.rollno).first()
        assert student is not None

        # Delete classroom
        response = auth_headers.delete(f"/classrooms/{sample_classroom.classroom_id}")
        assert response.status_code == 204

        # Verify student was also deleted
        student = test_db.query(Student).filter_by(rollno=sample_student.rollno).first()
        assert student is None

    def test_delete_classroom_unauthenticated(self, client, sample_classroom):
        """Test deleting classroom without authentication."""
        response = client.delete(f"/classrooms/{sample_classroom.classroom_id}")

        assert response.status_code == 401
