# Quick Reference: Test Commands & Documentation

## 📚 Documentation Index

| File | Purpose | Size |
|------|---------|------|
| [backlog.md](backlog.md) | Overall project progress & prioritization | 109 lines |
| [TASKS.md](TASKS.md) | Detailed breakdown of all 39 tests | 421 lines |
| [TEST_ROADMAP.md](TEST_ROADMAP.md) | 5-phase expansion plan for 150+ tests | 413 lines |
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
.venv/bin/python -m pytest tests/test_models.py -v

# Auth only
.venv/bin/python -m pytest tests/services/test_auth_service.py tests/api/test_auth_routes.py -v

# Upload/Retrieve only
.venv/bin/python -m pytest tests/api/test_upload_routes.py tests/e2e/ -v

# Filebase service only
.venv/bin/python -m pytest tests/services/test_filebase_service.py -v

# E2E tests only
.venv/bin/python -m pytest tests/e2e/ -v

# Health check only
.venv/bin/python -m pytest tests/test_health.py -v
```

### Run Individual Tests
```bash
# Run specific test class
.venv/bin/python -m pytest tests/test_models.py::TestUserModel -v

# Run specific test function
.venv/bin/python -m pytest tests/test_models.py::TestUserModel::test_create_user -v

# Run E2E upload test
.venv/bin/python -m pytest tests/e2e/test_e2e_filebase_integration.py::TestServiceE2EFilebaseIntegrationAPI::test_api_upload_retrieve_audit_flow -v
```

### Coverage Reports
```bash
# Generate coverage report
.venv/bin/python -m pytest tests/ --cov=core --cov-report=html

# View HTML report
open htmlcov/index.html

# Terminal coverage report
.venv/bin/python -m pytest tests/ --cov=core --cov-report=term-missing
```

### Test Collection & Discovery
```bash
# List all tests without running
.venv/bin/python -m pytest tests/ --collect-only

# Count total tests
.venv/bin/python -m pytest tests/ --collect-only -q

# List tests with details
.venv/bin/python -m pytest tests/ --collect-only -v
```

---

## 📊 Current Test Status

```
Total:           39 ✅ passing + 1 ⊘ skipped = 40 collected
Categories:      6 (models, auth, services, API, E2E, health)
Pass Rate:       97.5%
Code Coverage:   ~35%
Execution Time:  ~17.6 seconds

Breakdown:
├─ Models:              10 tests ✅
├─ Auth Services:        4 tests ✅
├─ Filebase Service:     9 tests ✅
├─ Upload Routes:        5 tests ✅
├─ E2E Flows:            8 tests ✅ (1 skipped)
└─ Health/Misc:          3 tests ✅
```

---

## 🔍 Test File Locations

```
tests/
├─ conftest.py                          # Global pytest fixtures
├─ __init__.py
├─ test_health.py                       # Health endpoint (1 test)
├─ test_models.py                       # Models (10 tests)
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

### Current (Phase 1: Foundation ✅)
- 39 tests passing
- 4/14 user stories complete
- ~35% code coverage

### Phase 2 Target (3-4 weeks)
- +30-37 new tests
- 69-76 total tests
- US-005, US-006, US-007 complete
- ~45% code coverage

### Phase 3 Target (weeks 5-6)
- +15-20 new tests
- 84-96 total tests
- Performance benchmarks
- ~55% code coverage

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
   # Full suite
   .venv/bin/python -m pytest tests/ -v
   
   # Specific category
   .venv/bin/python -m pytest tests/e2e/ -v
   ```

3. **Plan Phase 2**
   - Schedule US-005 (Content Pinning)
   - Schedule US-006 (Security)
   - Assign test coverage goals

4. **Setup CI/CD** (US-011)
   - GitHub Actions workflow
   - Pre-commit hooks
   - Coverage thresholds

---

## 📞 Support Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [SQLModel Testing Guide](https://sqlmodel.tiangolo.com/)
- [boto3 Testing](https://docs.getboto3.org/)
- [VCR.py HTTP Recording](https://vcrpy.readthedocs.io/)

---

**Last Updated**: December 30, 2025  
**Status**: ✅ All tests passing | ✅ Documentation complete | ✅ Ready for Phase 2
