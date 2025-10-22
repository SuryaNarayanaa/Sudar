"""Test subject endpoints."""

import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestCreateSubject:
    """Test create subject endpoint."""

    def test_create_subject_success(self, auth_headers, sample_classroom):
        """Test successful subject creation."""
        response = auth_headers.post(
            f"/classrooms/{sample_classroom.classroom_id}/subjects",
            json={"subject_name": "Physics"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["subject_name"] == "Physics"
        assert "subject_id" in data
        assert str(data["classroom_id"]) == str(sample_classroom.classroom_id)
        assert "created_at" in data

    def test_create_subject_empty_name(self, auth_headers, sample_classroom):
        """Test creating subject with empty name."""
        response = auth_headers.post(
            f"/classrooms/{sample_classroom.classroom_id}/subjects",
            json={"subject_name": ""},
        )

        assert response.status_code == 422  # Validation error

    def test_create_subject_wrong_classroom(self, client, test_db, sample_classroom):
        """Test creating subject in another teacher's classroom."""
        from api.authUtils import hash_password
        from api.models import Teacher

        # Create another teacher
        other_teacher = Teacher(
            teacher_name="Other",
            email="other3@test.com",
            hashed_password=hash_password("Pass123"),
        )
        test_db.add(other_teacher)
        test_db.commit()

        # Login as other teacher
        response = client.post(
            "/auth/login",
            json={"email": "other3@test.com", "password": "Pass123"},
        )
        client.cookies.set("access_token", response.cookies.get("access_token"))

        # Try to add subject to first teacher's classroom
        response = client.post(
            f"/classrooms/{sample_classroom.classroom_id}/subjects",
            json={"subject_name": "Hacked Subject"},
        )

        assert response.status_code == 404


class TestGetSubjects:
    """Test get subjects endpoint."""

    def test_get_subjects_success(self, auth_headers, sample_classroom, sample_subject):
        """Test getting all subjects in a classroom."""
        response = auth_headers.get(f"/classrooms/{sample_classroom.classroom_id}/subjects")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(str(s["subject_id"]) == str(sample_subject.subject_id) for s in data)

    def test_get_subjects_empty_classroom(self, auth_headers, sample_classroom):
        """Test getting subjects from classroom with no subjects."""
        response = auth_headers.get(f"/classrooms/{sample_classroom.classroom_id}/subjects")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_subjects_wrong_classroom(self, auth_headers):
        """Test getting subjects from non-existent classroom."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = auth_headers.get(f"/classrooms/{fake_id}/subjects")

        assert response.status_code == 404

    def test_get_subjects_unauthenticated(self, client, sample_classroom):
        """Test getting subjects without authentication."""
        response = client.get(f"/classrooms/{sample_classroom.classroom_id}/subjects")

        assert response.status_code == 401


class TestGetSubject:
    """Test get single subject endpoint."""

    def test_get_subject_success(self, auth_headers, sample_classroom, sample_subject):
        """Test getting a specific subject."""
        response = auth_headers.get(
            f"/classrooms/{sample_classroom.classroom_id}/subjects/{sample_subject.subject_id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert str(data["subject_id"]) == str(sample_subject.subject_id)
        assert data["subject_name"] == sample_subject.subject_name
        assert str(data["classroom_id"]) == str(sample_classroom.classroom_id)

    def test_get_subject_not_found(self, auth_headers, sample_classroom):
        """Test getting non-existent subject."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = auth_headers.get(f"/classrooms/{sample_classroom.classroom_id}/subjects/{fake_id}")

        assert response.status_code == 404

    def test_get_subject_wrong_classroom(self, auth_headers, sample_classroom, sample_subject, test_db):
        """Test getting subject from wrong classroom."""
        from api.models import Classroom

        # Create another classroom for same teacher
        other_classroom = Classroom(
            teacher_id=sample_classroom.teacher_id,
            classroom_name="Other Class",
        )
        test_db.add(other_classroom)
        test_db.commit()

        # Try to get subject from wrong classroom
        response = auth_headers.get(
            f"/classrooms/{other_classroom.classroom_id}/subjects/{sample_subject.subject_id}"
        )

        assert response.status_code == 404


class TestUpdateSubject:
    """Test update subject endpoint."""

    def test_update_subject_success(self, auth_headers, sample_classroom, sample_subject):
        """Test successful subject update."""
        response = auth_headers.put(
            f"/classrooms/{sample_classroom.classroom_id}/subjects/{sample_subject.subject_id}",
            json={"subject_name": "Advanced Mathematics"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["subject_name"] == "Advanced Mathematics"
        assert str(data["subject_id"]) == str(sample_subject.subject_id)

    def test_update_subject_not_found(self, auth_headers, sample_classroom):
        """Test updating non-existent subject."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = auth_headers.put(
            f"/classrooms/{sample_classroom.classroom_id}/subjects/{fake_id}",
            json={"subject_name": "Ghost Subject"},
        )

        assert response.status_code == 404

    def test_update_subject_empty_name(self, auth_headers, sample_classroom, sample_subject):
        """Test updating subject with empty name."""
        response = auth_headers.put(
            f"/classrooms/{sample_classroom.classroom_id}/subjects/{sample_subject.subject_id}",
            json={"subject_name": ""},
        )

        assert response.status_code == 422  # Validation error

    def test_update_subject_unauthenticated(self, client, sample_classroom, sample_subject):
        """Test updating subject without authentication."""
        response = client.put(
            f"/classrooms/{sample_classroom.classroom_id}/subjects/{sample_subject.subject_id}",
            json={"subject_name": "Hacked Name"},
        )

        assert response.status_code == 401


class TestDeleteSubject:
    """Test delete subject endpoint."""

    def test_delete_subject_success(self, auth_headers, sample_classroom, sample_subject, test_db):
        """Test successful subject deletion."""
        from api.models import Subject

        # Verify subject exists
        subject = test_db.query(Subject).filter_by(subject_id=sample_subject.subject_id).first()
        assert subject is not None

        # Delete subject
        response = auth_headers.delete(
            f"/classrooms/{sample_classroom.classroom_id}/subjects/{sample_subject.subject_id}"
        )

        assert response.status_code == 204

        # Verify subject was deleted
        subject = test_db.query(Subject).filter_by(subject_id=sample_subject.subject_id).first()
        assert subject is None

    def test_delete_subject_not_found(self, auth_headers, sample_classroom):
        """Test deleting non-existent subject."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = auth_headers.delete(f"/classrooms/{sample_classroom.classroom_id}/subjects/{fake_id}")

        assert response.status_code == 404

    def test_delete_subject_cascades_to_activities(
        self, auth_headers, sample_classroom, sample_subject, sample_activity, test_db
    ):
        """Test that deleting subject cascades to delete activities."""
        from api.models import Activity

        # Verify activity exists
        activity = test_db.query(Activity).filter_by(activity_id=sample_activity.activity_id).first()
        assert activity is not None

        # Delete subject
        response = auth_headers.delete(
            f"/classrooms/{sample_classroom.classroom_id}/subjects/{sample_subject.subject_id}"
        )
        assert response.status_code == 204

        # Verify activity was also deleted
        activity = test_db.query(Activity).filter_by(activity_id=sample_activity.activity_id).first()
        assert activity is None

    def test_delete_subject_unauthenticated(self, client, sample_classroom, sample_subject):
        """Test deleting subject without authentication."""
        response = client.delete(
            f"/classrooms/{sample_classroom.classroom_id}/subjects/{sample_subject.subject_id}"
        )

        assert response.status_code == 401
