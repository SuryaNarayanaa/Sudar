# Backend Test Suite

Comprehensive test suite for the Sudar backend API.

┌─────────────────────────────────────────────────────────────────┐
│                    PYTEST EXECUTION STARTS                      │
└─────────────────────────────────────────┬───────────────────────┘
                                          │
                                          ▼
                ┌─────────────────────────────────────┐
                │  conftest.py - Setup Phase          │
                │  (Runs before EVERY test)           │
                └─────────────────┬───────────────────┘
                                  │
                    ┌─────────────┴──────────────┐
                    ▼                            ▼
        ┌──────────────────────┐    ┌──────────────────────┐
        │  test_db Fixture     │    │  client Fixture      │
        │  (Fresh SQLite DB)   │    │  (TestClient)        │
        │  - Create tables     │    │  - Override get_db   │
        │  - Foreign keys ON   │    │  - Ready to use      │
        └──────────────────────┘    └──────────────────────┘
                    │                            │
                    └─────────────┬──────────────┘
                                  ▼
                ┌─────────────────────────────────────┐
                │  Optional: Create Sample Data       │
                │  (Fixtures like sample_teacher,     │
                │   sample_classroom, etc.)           │
                └─────────────────┬───────────────────┘
                                  │
                                  ▼
                ┌─────────────────────────────────────┐
                │  RUN ACTUAL TEST                    │
                └─────────────────┬───────────────────┘
                                  │
                                  ▼
                ┌─────────────────────────────────────┐
                │  CLEANUP & TEARDOWN                 │
                │  - Drop all tables                  │
                │  - Clear app overrides              │
                │  - Close DB connection              │
                └─────────────────────────────────────┘
## Test Coverage

### Authentication Tests (`test_auth_endpoints.py`)
- Send verification code (new email, existing email, code updates)
- Signup (success, invalid code, expired code, weak password)
- Login (success, wrong password, non-existent email)
- Forgot password (existing and non-existent emails)
- Reset password (success, invalid code, expired code)
- Get current user (authenticated and unauthenticated)
- Logout (success and unauthenticated)

### Authentication Utilities Tests (`test_auth_utils.py`)
- Password hashing and verification
- Password validation rules
- Verification code generation
- JWT token creation and decoding

### Classroom Tests (`test_classroom_endpoints.py`)
- Create classroom (success, validation)
- Get all classrooms
- Get single classroom (success, not found, wrong teacher)
- Update classroom
- Delete classroom (with cascade)

### Student Tests (`test_student_endpoints.py`)
- Create student (success, duplicate rollno, invalid grade)
- Get all students
- Get single student
- Update student (name, grade, DOB, multiple fields)
- Delete student

### Subject Tests (`test_subject_endpoints.py`)
- Create subject
- Get all subjects
- Get single subject
- Update subject
- Delete subject (with cascade to activities)

### Main Application Tests (`test_main.py`)
- Root endpoint
- Health check endpoint

## Running Tests

### Prerequisites

1. **Install dependencies:**
   ```bash
   cd be
   uv pip install -e .[dev]
   # or using pip:
   pip install -e .[dev]
   ```

2. **Environment setup:**
   Tests use an in-memory SQLite database, so no external services are needed.

### Run All Tests

```bash
# From the be/ directory
pytest

# With verbose output
pytest -v

# With coverage
pytest --cov=api --cov-report=html

# Run specific test file
pytest tests/test_auth_endpoints.py

# Run specific test class
pytest tests/test_auth_endpoints.py::TestSignup

# Run specific test
pytest tests/test_auth_endpoints.py::TestSignup::test_signup_success
```

### Generate HTML Test Report

```bash
# Generate interactive HTML report
pytest --html=reports/backend-test-report.html --self-contained-html

# Open the report in your browser
# Windows: start reports/backend-test-report.html
# Linux: xdg-open reports/backend-test-report.html
# Mac: open reports/backend-test-report.html
```

### Run Tests with Coverage Report

```bash
# Generate coverage report
pytest --cov=api --cov-report=html --cov-report=term

# View coverage report
# The HTML report will be in htmlcov/index.html
```

## Test Architecture

### Fixtures (conftest.py)

The test suite uses pytest fixtures for setup:

- **`test_db`**: Fresh in-memory SQLite database for each test
- **`client`**: FastAPI test client with database override
- **`sample_teacher`**: Pre-created teacher for authentication tests
- **`auth_headers`**: Authenticated client with cookies set
- **`sample_classroom`**: Pre-created classroom for testing
- **`sample_student`**: Pre-created student for testing
- **`sample_subject`**: Pre-created subject for testing
- **`sample_activity`**: Pre-created activity for testing

### Test Organization

Tests are organized by endpoint groups:
- Authentication endpoints and utilities
- Classroom CRUD operations
- Student CRUD operations  
- Subject CRUD operations
- Application health checks

Each test class focuses on a specific endpoint operation (Create, Read, Update, Delete).

## Test Database

Tests use an in-memory SQLite database that:
- Is created fresh for each test
- Has foreign key constraints enabled
- Uses the same models as production
- Cleans up automatically after tests

## CI/CD Integration

To run tests in CI/CD:

```yaml
- name: Run backend tests
  run: |
    cd be
    pip install -e .[dev]
    pytest --html=reports/backend-test-report.html --cov=api
```

## Common Issues

### Import Errors
If you see `ModuleNotFoundError: No module named 'fastapi'`:
```bash
# Make sure dev dependencies are installed
uv pip install -e .[dev]
```

### Database Errors
Tests should use in-memory database automatically. If you see database connection errors, ensure:
- No `DATABASE_URL` environment variable is set (or it's set to `sqlite:///:memory:`)
- SQLAlchemy is properly installed

### Authentication Errors
If authentication tests fail:
- Ensure `SECRET_KEY` environment variable is set or defaults to test value
- Check that bcrypt is properly installed

## Contributing

When adding new endpoints:
1. Add endpoint tests in appropriate test file
2. Add fixtures in `conftest.py` if needed
3. Ensure tests cover success and error cases
4. Run full test suite before committing

## Test Statistics

Total Test Files: 6
- `test_auth_endpoints.py`: ~30 tests
- `test_auth_utils.py`: ~15 tests
- `test_classroom_endpoints.py`: ~15 tests
- `test_student_endpoints.py`: ~25 tests
- `test_subject_endpoints.py`: ~20 tests
- `test_main.py`: 2 tests

**Total: ~100+ test cases** covering all major API functionality.
