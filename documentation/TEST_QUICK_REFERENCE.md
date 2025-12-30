# Quick Reference: Test Commands & Documentation

## 📚 Documentation Index

| File | Purpose | Size |
|------|---------|------|
| [backlog.md](backlog.md) | Overall project progress & prioritization | 145 lines |
| [TASKS.md](TASKS.md) | Detailed breakdown of 71 tests with logging suite | 507 lines |
| [TEST_ROADMAP.md](TEST_ROADMAP.md) | 5-phase expansion plan for 150+ tests | 425 lines |
| [project-specifications.md](project-specifications.md) | Architecture & system design | 205 lines |

---

## 🧪 Test Execution Commands

### Run All Tests
```bash
# All tests with summary
.venv/bin/python -m pytest tests/ -v

# All tests with output capture disabled (see print statements)
.venv/bin/python -m pytest tests/ -v -s

# Stop at first failure
.venv/bin/python -m pytest tests/ -x

# Verbose with short traceback
.venv/bin/python -m pytest tests/ -v --tb=short
```

### Run Specific Test Suites
```bash
# Models only
uv run python -m pytest tests/test_models.py -v

# Auth only
uv run python -m pytest tests/services/test_auth_service.py tests/api/test_auth_routes.py -v

# Upload/Retrieve only
uv run python -m pytest tests/api/test_upload_routes.py tests/e2e/ -v

# Filebase service only
uv run python -m pytest tests/services/test_filebase_service.py -v

# Logging tests only
uv run python -m pytest tests/test_logging.py -v

# E2E tests only
uv run python -m pytest tests/e2e/ -v

# Health check only
uv run python -m pytest tests/test_health.py -v
```

### Run Individual Tests
```bash
# Run specific test class
uv run python -m pytest tests/test_models.py::TestUserModel -v

# Run specific test function
uv run python -m pytest tests/test_models.py::TestUserModel::test_create_user -v

# Run logging configuration tests
uv run python -m pytest tests/test_logging.py::TestLoggingConfiguration -v

# Run E2E upload test
uv run python -m pytest tests/e2e/test_e2e_filebase_integration.py::TestServiceE2EFilebaseIntegrationAPI::test_api_upload_retrieve_audit_flow -v
```

### Coverage Reports
```bash
# Generate coverage report
uv run python -m pytest tests/ --cov=core --cov-report=html

# View HTML report
open htmlcov/index.html

# Terminal coverage report
uv run python -m pytest tests/ --cov=core --cov-report=term-missing
```

### Test Collection & Discovery
```bash
# List all tests without running
uv run python -m pytest tests/ --collect-only

# Count total tests
uv run python -m pytest tests/ --collect-only -q

# List tests with details
uv run python -m pytest tests/ --collect-only -v
```

---

## 📊 Current Test Status

```
Total:           71 ✅ passing + 1 ⊘ skipped = 72 collected
Categories:      7 (models, auth, services, API, E2E, logging, health)
Pass Rate:       98.6%
Code Coverage:   ~45%
Execution Time:  ~39.85 seconds

Breakdown:
├─ Models:              10 tests ✅
├─ Auth Services:        4 tests ✅
├─ Filebase Service:     9 tests ✅
├─ Upload Routes:        5 tests ✅
├─ Logging Tests:       16 tests ✅ (NEW - US-008)
├─ E2E Flows:            8 tests ✅ (1 skipped)
└─ Health/Misc:          3 tests ✅

User Stories Coverage (US-001 to US-008): 100% ✅
├─ US-001: Health Check & Monitoring
├─ US-002: Authentication & API Key Management
├─ US-003: File Upload Service
├─ US-004: Audit Logging & Compliance
├─ US-005: Content Pinning
├─ US-006: Security & Rate Limiting
├─ US-007: Error Handling
└─ US-008: Logging, Audit & Monitoring ✅ JUST COMPLETED
```

---

## 🔍 Test File Locations

```
tests/
├─ conftest.py                          # Global pytest fixtures
├─ __init__.py
├─ test_health.py                       # Health endpoint (1 test)
├─ test_models.py                       # Models (10 tests)
├─ test_logging.py                      # Logging & audit (16 tests) NEW
├─ api/
│  ├─ test_auth_routes.py              # Auth endpoints (2 tests)
│  └─ test_upload_routes.py            # Upload/retrieve (5 tests)
├─ services/
│  ├─ test_auth_service.py             # Auth logic (2 tests)
│  └─ test_filebase_service.py         # Filebase integration (9 tests)
└─ e2e/
   └─ test_e2e_filebase_integration.py # Full stack flows (9 tests)
```

---

## ⚙️ Key Test Patterns

### Pattern 1: In-Memory SQLite Setup
```python
# For unit tests with fresh database
@pytest.fixture()
def client(monkeypatch):
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    app = create_app()
    
    import core.models.connection as connection
    connection.engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(connection.engine)
    
    yield app.test_client()
```

### Pattern 2: Fresh Session After API Call
```python
# For E2E tests that need to verify DB changes
for session in get_session():
    stmt = select(File).where(File.cid == cid)
    file_record = session.exec(stmt).first()
    break  # Don't reuse fixture session
```

### Pattern 3: boto3 Mock Response
```python
# Proper mock with ResponseMetadata
mock_client.put_object.return_value = {
    "ETag": '"abc123"',
    "ResponseMetadata": {
        "HTTPHeaders": {"x-amz-meta-cid": '"QmXyz"'}
    }
}
```

### Pattern 4: Graceful Skipping
```python
# For tests requiring external services
@pytest.fixture
def filebase_available():
    if not validate_credentials():
        pytest.skip("Filebase unavailable")
```

---

## 🛠️ Common Issues & Fixes

| Issue | Cause | Solution |
|-------|-------|----------|
| "no such table" | Unit test DB not initialized | Use `SQLModel.metadata.create_all()` |
| "not persistent" | Object from different session | Re-query with current session |
| Mock response incomplete | Missing ResponseMetadata | Add `HTTPHeaders` to mock |
| Flaky E2E tests | Filebase credentials invalid | Fixture gracefully skips |

---

## 📈 Progress Tracking

### Current (Phase 2: Enhanced Features ✅)
- 71 tests passing, 1 skipped
- 8/14 user stories complete (57.1%)
- 20/36 days effort complete (55.6%)
- ~45% code coverage
- Latest: US-008 (Logging & Audit Monitoring) ✅

**Recent Additions**:
- 16 new logging tests (Configuration, Audit Persistence, Logging Levels, Request Tracking, Consistency)
- Enhanced logging across all services and routes
- Structured JSON logging with correlation IDs
- Persistent audit logs for all operations

### Phase 3 Target (weeks 7-8)
- +15-25 new tests
- 86-96 total tests
- US-009 (Async Processing), US-010 (Testing & QA)
- ~55% code coverage

### Phase 4 Target (weeks 9-10)
- +20-30 new tests
- 106-126 total tests
- Performance & security benchmarks
- ~65% code coverage

### Final Target (Phase 5)
- 150-180 total tests
- 14/14 user stories complete
- >80% code coverage
- Full CI/CD pipeline

---

## 🎯 Next Actions

1. **Review Documentation**
   ```bash
   # Read current status
   cat documentation/backlog.md
   
   # Read detailed test info
   cat documentation/TASKS.md
   
   # Review expansion plan
   cat documentation/TEST_ROADMAP.md
   ```

2. **Run Tests**
   ```bash
   # Full suite with uv
   uv run python -m pytest tests/ -v
   
   # Logging tests only
   uv run python -m pytest tests/test_logging.py -v
   
   # Coverage report
   uv run python -m pytest tests/ --cov=core --cov-report=term-missing
   ```

3. **Prepare Phase 3**
   - Start US-009 (Async Processing with Celery/Redis)
   - Start US-010 (Testing & Quality Gates)
   - Plan additional test coverage for new features

4. **Setup CI/CD** (US-011)
   - GitHub Actions workflow with pytest
   - Pre-commit hooks for test validation
   - Coverage thresholds (target: >80%)

---

## 📞 Support Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [SQLModel Testing Guide](https://sqlmodel.tiangolo.com/)
- [boto3 Testing](https://docs.getboto3.org/)
- [VCR.py HTTP Recording](https://vcrpy.readthedocs.io/)

---

**Last Updated**: December 31, 2025  
**Status**: ✅ US-008 complete | ✅ 71 tests passing (98.6%) | ✅ 8/14 stories done (57.1%) | ✅ Ready for Phase 3
