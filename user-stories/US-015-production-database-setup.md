# US-015: Production Database Setup

- Priority: P0 (Critical)
- Effort: 2 days (approx. 16h)
- Status: 🔄 In Progress
- Completion: 0%

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
- [ ] TASK-015-01: Add DATABASE_URL_PROD to .env and update settings.py (Effort: 4h) 🔄 In Progress
- [ ] TASK-015-02: Test database connectivity and migrations (Effort: 6h) 📋 Not Started
- [ ] TASK-015-03: Configure connection pooling and production optimizations (Effort: 4h) 📋 Not Started
- [ ] TASK-015-04: Update documentation and deployment guides (Effort: 2h) 📋 Not Started

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
- [ ] DATABASE_URL_PROD environment variable configured in .env
- [ ] Settings.py updated to use production database for staging/production environments
- [ ] All existing tests pass with local development database
- [ ] Successful connection to remote production database verified
- [ ] Database migrations executed successfully on production
- [ ] Connection pooling configured and tested
- [ ] Documentation updated with production database setup instructions
- [ ] Code reviewed and merged to main branch
