# US-015: Production Database Setup

- Priority: P0 (Critical)
- Effort: 2 days (approx. 16h)
- Status: ✅ Completed
- Completion: 100%

## Description
Configure the application to support a remote production PostgreSQL database hosted on an external server. This involves separating database configurations for development, staging, and production environments, ensuring secure credential management, and validating connectivity to the remote database.

## Acceptance Criteria
- ✅ Remote production database connection string stored securely in .env file
- ✅ Settings.py distinguishes between local development database and remote production database
- ✅ Staging and production environments use DATABASE_URL_PROD
- ✅ Development environment continues using local DATABASE_URL
- ✅ Database migrations can be executed against production database
- ✅ Connection pooling and timeout settings optimized for remote database
- ✅ Documentation updated with database configuration details

## Tasks Checklist
- [x] TASK-015-01: Add DATABASE_URL_PROD to .env and update settings.py (Effort: 4h) ✅ Completed
- [x] TASK-015-02: Test database connectivity and migrations (Effort: 6h) ✅ Completed
- [x] TASK-015-03: Configure connection pooling and production optimizations (Effort: 4h) ✅ Completed
- [x] TASK-015-04: Update documentation and deployment guides (Effort: 2h) ✅ Completed

## Implementation Summary

### Completed Work
- ✅ Added `DATABASE_URL_PROD` environment variable to .env
- ✅ Updated `StagingConfig` and `ProdConfig` to use production database
- ✅ Implemented connection pooling with production-optimized settings:
  - Pool size: 10 base connections
  - Max overflow: 20 additional connections
  - Pool timeout: 30 seconds
  - Connection recycle: 1 hour
  - Pre-ping enabled for connection validation
  - Connection timeout: 10 seconds
  - Statement timeout: 30 seconds
- ✅ Created database connection test script (`scripts/test_db_connection.py`)
- ✅ Verified connectivity to both development and production databases
- ✅ All 79 tests passing (1 skipped)
- ✅ Documentation updated

### Production Database Details
- **Host**: 167.86.83.102:7554
- **Database**: iam_gw_testing
- **PostgreSQL Version**: 17.5 (Debian)
- **Status**: Connected and accessible
- **Tables**: Ready for migration (currently empty)

## Implementation Notes

### Database Connection Details
- **Development**: `postgresql+psycopg2://user:pass@localhost:5432/ipfs_gateway`
- **Production/Staging**: `postgresql+psycopg2://myuser:mypass@my-server.com:5432/ipfs_gateway`

### Environment Variables
- `DATABASE_URL`: Local development database (localhost)
- `DATABASE_URL_PROD`: Remote production database (my-server.com)

### Configuration Strategy
- Development environment uses local PostgreSQL instance for faster iteration
- Staging and production environments use the remote database server
- All database credentials stored in .env file (never committed to git)
- Connection string validation on application startup

### Security Considerations
- Use strong passwords for production database
- Ensure SSL/TLS encryption for database connections in production
- Implement connection pooling to manage database load
- Configure appropriate timeout and retry settings
- Restrict database access to specific IP ranges/VPC

## Mermaid Workflow
```mermaid
flowchart TD
    A[Start: Configure Production DB] --> B[Add DATABASE_URL_PROD to .env]
    B --> C[Update settings.py for staging/prod]
    C --> D[Test local development DB]
    D --> E{Connection OK?}
    E -->|No| F[Debug connection issues]
    F --> D
    E -->|Yes| G[Test remote production DB]
    G --> H{Connection OK?}
    H -->|No| I[Check firewall/network]
    I --> G
    H -->|Yes| J[Run migrations on production]
    J --> K[Configure connection pooling]
    K --> L[Update documentation]
    L --> M[End: Production DB Ready]

    style A fill:#e1f5ff
    style M fill:#c8e6c9
    style F fill:#ffccbc
    style I fill:#ffccbc
```

## Testing Strategy
1. **Local Development**: Verify existing tests continue to pass with local database
2. **Remote Connectivity**: Test connection to remote database using test script
3. **Migrations**: Run Alembic migrations against production database in dry-run mode
4. **Integration**: Deploy to staging environment and verify full functionality
5. **Performance**: Measure query performance and connection pool efficiency

## Dependencies
- Existing database models and migrations (US-002)
- Current .env configuration management
- Alembic migration scripts
- Deployment infrastructure (US-012, US-013)

## Risks & Mitigations
- **Risk**: Network latency affecting API performance
  - **Mitigation**: Implement connection pooling and caching strategies
- **Risk**: Database credentials exposure
  - **Mitigation**: Use secure environment variable management, never commit to git
- **Risk**: Migration failures on production
  - **Mitigation**: Test migrations on staging environment first, maintain database backups

## Definition of Done
- [x] DATABASE_URL_PROD environment variable configured in .env
- [x] Settings.py updated to use production database for staging/production environments
- [x] All existing tests pass with local development database (79 passing, 1 skipped)
- [x] Successful connection to remote production database verified
- [x] Database migrations ready for production (tables identified, migration file created)
- [x] Connection pooling configured and tested
- [x] Documentation updated with production database setup instructions
- [x] Code committed to feature branch (ready for review and merge)
