"""Pytest configuration and shared fixtures for backend tests."""

import os
import sys
from datetime import date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add parent directory to path to import api module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")

from api.database import Base, get_db  # noqa: E402
from api.main import app  # noqa: E402
from api.models import Activity, Classroom, Student, Subject, Teacher  # noqa: E402


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh in-memory SQLite database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign key constraints for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):  # noqa: ARG001
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield TestingSessionLocal()

    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_db):  # noqa: ARG001
    """Create a test client with database dependency override."""
    return TestClient(app)


@pytest.fixture
def sample_teacher(test_db):
    """Create a sample teacher for testing."""
    from api.authUtils import hash_password

    teacher = Teacher(
        teacher_name="Test Teacher",
        email="teacher@test.com",
        hashed_password=hash_password("TestPass123"),
    )
    test_db.add(teacher)
    test_db.commit()
    test_db.refresh(teacher)
    return teacher


@pytest.fixture
def auth_headers(client, sample_teacher):
    """Get authentication headers for a test teacher."""
    response = client.post(
        "/auth/login",
        json={"email": "teacher@test.com", "password": "TestPass123"},
    )
    assert response.status_code == 200

    # Extract access_token from cookies
    cookies = response.cookies
    access_token = cookies.get("access_token")
    assert access_token is not None

    # Return client with cookies set
    client.cookies.set("access_token", access_token)
    return client


@pytest.fixture
def sample_classroom(test_db, sample_teacher):
    """Create a sample classroom for testing."""
    classroom = Classroom(
        teacher_id=sample_teacher.teacher_id,
        classroom_name="Test Classroom",
    )
    test_db.add(classroom)
    test_db.commit()
    test_db.refresh(classroom)
    return classroom


@pytest.fixture
def sample_student(test_db, sample_classroom):
    """Create a sample student for testing."""
    student = Student(
        rollno="STU001",
        classroom_id=sample_classroom.classroom_id,
        student_name="Test Student",
        dob=date(2010, 1, 1),
        grade=5,
    )
    test_db.add(student)
    test_db.commit()
    test_db.refresh(student)
    return student


@pytest.fixture
def sample_subject(test_db, sample_classroom):
    """Create a sample subject for testing."""
    subject = Subject(
        classroom_id=sample_classroom.classroom_id,
        subject_name="Mathematics",
    )
    test_db.add(subject)
    test_db.commit()
    test_db.refresh(subject)
    return subject


@pytest.fixture
def sample_activity(test_db, sample_subject):
    """Create a sample activity for testing."""
    from api.models import ActivityType

    activity = Activity(
        subject_id=sample_subject.subject_id,
        title="Sample Worksheet",
        type=ActivityType.WORKSHEET,
    )
    test_db.add(activity)
    test_db.commit()
    test_db.refresh(activity)
    return activity
