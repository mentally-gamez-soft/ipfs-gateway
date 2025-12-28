# Issue: Application Failed to Start - psycopg2-binary Python 3.13 Incompatibility

**Date:** 2025-12-28  
**Severity:** Critical  
**Status:** Resolved  
**Branch:** feature/US-002-database-models-migrations

## Problem Description

The application failed to launch with the following error:

```
ImportError: /PROJECTS/python/ipfs-gateway/.venv/lib/python3.13/site-packages/psycopg2/_psycopg.cpython-313-x86_64-linux-gnu.so: undefined symbol: _PyInterpreterState_Get
```

### Root Cause

The `psycopg2-binary==2.9.9` package has a known incompatibility with Python 3.13. The C extension module was compiled for earlier Python versions and references internal CPython symbols that have changed in Python 3.13.

### Impact

- Application could not start (`main.py` execution failed)
- Database initialization blocked app factory
- Development workflow completely halted
- All endpoints unreachable

## Solution

### Changes Made

1. **Switched to SQLite for Development** ([core/config/settings.py](../core/config/settings.py))
   - Changed default `DATABASE_URL` from PostgreSQL to SQLite
   - Before: `postgresql+psycopg2://user:pass@localhost:5432/ipfs_gateway`
   - After: `sqlite:///./ipfs_gateway.db`

2. **Made PostgreSQL Optional** ([pyproject.toml](../pyproject.toml))
   - Moved `psycopg2-binary` to optional dependencies
   - Can be installed with: `uv sync --extra postgres`
   - Allows development without PostgreSQL driver issues

3. **Updated .gitignore** ([.gitignore](../.gitignore))
   - Added SQLite database files (*.db, *.db-journal, *.db-shm, *.db-wal)
   - Prevents local dev databases from being committed

### Testing

After applying the fix:
- ✅ Application starts successfully
- ✅ All 11 tests pass (health + 10 model tests)
- ✅ Database tables created in SQLite
- ✅ No runtime errors

## Prevention

### For Future Development

1. **Use psycopg (v3)** when PostgreSQL is required:
   ```toml
   postgres = ["psycopg[binary]==3.1.18"]
   ```
   The psycopg v3 library has better Python 3.13 support.

2. **Environment-Based DB Selection**:
   - Development: SQLite (no external dependencies)
   - Staging/Production: PostgreSQL via environment variable
   - Tests: In-memory SQLite

3. **Document DB Requirements**:
   - Clearly specify PostgreSQL is optional
   - Provide setup instructions for both SQLite and PostgreSQL
   - Include troubleshooting for driver issues

## Verification Commands

```bash
# Start the application
uv run python main.py

# Run all tests
uv run pytest -v

# Check database was created
ls -la *.db
```

## Related Files

- [core/config/settings.py](../core/config/settings.py) - Database URL configuration
- [pyproject.toml](../pyproject.toml) - Dependencies
- [.gitignore](../.gitignore) - SQLite exclusions
- [core/models/connection.py](../core/models/connection.py) - DB engine initialization

## References

- Python 3.13 Release Notes: https://docs.python.org/3.13/whatsnew/3.13.html
- psycopg2 Python 3.13 Issue: https://github.com/psycopg/psycopg2/issues/1600
- SQLAlchemy Dialects: https://docs.sqlalchemy.org/en/20/dialects/
