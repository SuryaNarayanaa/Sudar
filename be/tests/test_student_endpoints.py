"""Test student endpoints."""

import sys
from datetime import date
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestCreateStudent:
    """Test create student endpoint."""

    def test_create_student_success(self, auth_headers, sample_classroom):
        """Test successful student creation."""
        response = auth_headers.post(
            f"/classrooms/{sample_classroom.classroom_id}/students",
            json={
                "rollno": "STU100",
                "student_name": "John Doe",
                "dob": "2010-05-15",
                "grade": 5,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["rollno"] == "STU100"
        assert data["student_name"] == "John Doe"
        assert data["grade"] == 5
        assert str(data["classroom_id"]) == str(sample_classroom.classroom_id)

    def test_create_student_duplicate_rollno(self, auth_headers, sample_classroom, sample_student):
        """Test creating student with duplicate roll number."""
        response = auth_headers.post(
            f"/classrooms/{sample_classroom.classroom_id}/students",
            json={
                "rollno": sample_student.rollno,  # Duplicate
                "student_name": "Another Student",
                "dob": "2010-01-01",
                "grade": 5,
            },
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_student_invalid_grade(self, auth_headers, sample_classroom):
        """Test creating student with invalid grade."""
        response = auth_headers.post(
            f"/classrooms/{sample_classroom.classroom_id}/students",
            json={
                "rollno": "STU200",
                "student_name": "Test Student",
                "dob": "2010-01-01",
                "grade": 15,  # Invalid: > 12
            },
        )

        assert response.status_code == 422  # Validation error

    def test_create_student_wrong_classroom(self, client, test_db, sample_classroom):
        """Test creating student in another teacher's classroom."""
        from api.authUtils import hash_password
        from api.models import Teacher

        # Create another teacher
        other_teacher = Teacher(
            teacher_name="Other",
            email="other2@test.com",
            hashed_password=hash_password("Pass123"),
        )
        test_db.add(other_teacher)
        test_db.commit()

        # Login as other teacher
        response = client.post(
            "/auth/login",
            json={"email": "other2@test.com", "password": "Pass123"},
        )
        client.cookies.set("access_token", response.cookies.get("access_token"))

        # Try to add student to first teacher's classroom
        response = client.post(
            f"/classrooms/{sample_classroom.classroom_id}/students",
            json={
                "rollno": "HACK001",
                "student_name": "Hacker",
                "dob": "2010-01-01",
                "grade": 5,
            },
        )

        assert response.status_code == 404  # Classroom not found for this teacher


class TestGetStudents:
    """Test get students endpoint."""

    def test_get_students_success(self, auth_headers, sample_classroom, sample_student):
        """Test getting all students in a classroom."""
        response = auth_headers.get(f"/classrooms/{sample_classroom.classroom_id}/students")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(s["rollno"] == sample_student.rollno for s in data)

    def test_get_students_empty_classroom(self, auth_headers, sample_classroom):
        """Test getting students from empty classroom."""
        response = auth_headers.get(f"/classrooms/{sample_classroom.classroom_id}/students")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_students_wrong_classroom(self, auth_headers):
        """Test getting students from non-existent classroom."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = auth_headers.get(f"/classrooms/{fake_id}/students")

        assert response.status_code == 404


class TestGetStudent:
    """Test get single student endpoint."""

    def test_get_student_success(self, auth_headers, sample_classroom, sample_student):
        """Test getting a specific student."""
        response = auth_headers.get(
            f"/classrooms/{sample_classroom.classroom_id}/students/{sample_student.rollno}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rollno"] == sample_student.rollno
        assert data["student_name"] == sample_student.student_name
        assert data["grade"] == sample_student.grade

    def test_get_student_not_found(self, auth_headers, sample_classroom):
        """Test getting non-existent student."""
        response = auth_headers.get(f"/classrooms/{sample_classroom.classroom_id}/students/FAKE999")

        assert response.status_code == 404

    def test_get_student_wrong_classroom(self, auth_headers, sample_classroom, sample_student, test_db):
        """Test getting student from wrong classroom."""
        from api.models import Classroom

        # Create another classroom for same teacher
        other_classroom = Classroom(
            teacher_id=sample_classroom.teacher_id,
            classroom_name="Other Class",
        )
        test_db.add(other_classroom)
        test_db.commit()

        # Try to get student from wrong classroom
        response = auth_headers.get(
            f"/classrooms/{other_classroom.classroom_id}/students/{sample_student.rollno}"
        )

        assert response.status_code == 404


class TestUpdateStudent:
    """Test update student endpoint."""

    def test_update_student_name(self, auth_headers, sample_classroom, sample_student):
        """Test updating student name."""
        response = auth_headers.put(
            f"/classrooms/{sample_classroom.classroom_id}/students/{sample_student.rollno}",
            json={"student_name": "Updated Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["student_name"] == "Updated Name"
        assert data["rollno"] == sample_student.rollno

    def test_update_student_grade(self, auth_headers, sample_classroom, sample_student):
        """Test updating student grade."""
        response = auth_headers.put(
            f"/classrooms/{sample_classroom.classroom_id}/students/{sample_student.rollno}",
            json={"grade": 6},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["grade"] == 6

    def test_update_student_dob(self, auth_headers, sample_classroom, sample_student):
        """Test updating student date of birth."""
        new_dob = "2011-06-15"
        response = auth_headers.put(
            f"/classrooms/{sample_classroom.classroom_id}/students/{sample_student.rollno}",
            json={"dob": new_dob},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["dob"] == new_dob

    def test_update_student_multiple_fields(self, auth_headers, sample_classroom, sample_student):
        """Test updating multiple student fields at once."""
        response = auth_headers.put(
            f"/classrooms/{sample_classroom.classroom_id}/students/{sample_student.rollno}",
            json={
                "student_name": "New Name",
                "grade": 7,
                "dob": "2009-12-31",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["student_name"] == "New Name"
        assert data["grade"] == 7
        assert data["dob"] == "2009-12-31"

    def test_update_student_not_found(self, auth_headers, sample_classroom):
        """Test updating non-existent student."""
        response = auth_headers.put(
            f"/classrooms/{sample_classroom.classroom_id}/students/NOTFOUND",
            json={"student_name": "Ghost"},
        )

        assert response.status_code == 404


class TestDeleteStudent:
    """Test delete student endpoint."""

    def test_delete_student_success(self, auth_headers, sample_classroom, sample_student, test_db):
        """Test successful student deletion."""
        from api.models import Student

        # Verify student exists
        student = test_db.query(Student).filter_by(rollno=sample_student.rollno).first()
        assert student is not None

        # Delete student
        response = auth_headers.delete(
            f"/classrooms/{sample_classroom.classroom_id}/students/{sample_student.rollno}"
        )

        assert response.status_code == 204

        # Verify student was deleted
        student = test_db.query(Student).filter_by(rollno=sample_student.rollno).first()
        assert student is None

    def test_delete_student_not_found(self, auth_headers, sample_classroom):
        """Test deleting non-existent student."""
        response = auth_headers.delete(
            f"/classrooms/{sample_classroom.classroom_id}/students/NOTFOUND"
        )

        assert response.status_code == 404

    def test_delete_student_unauthenticated(self, client, sample_classroom, sample_student):
        """Test deleting student without authentication."""
        response = client.delete(
            f"/classrooms/{sample_classroom.classroom_id}/students/{sample_student.rollno}"
        )

        assert response.status_code == 401
