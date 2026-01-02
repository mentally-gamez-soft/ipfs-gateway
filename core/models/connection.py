from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel
from flask import Flask
from typing import Generator
import logging

logger = logging.getLogger(__name__)

engine = None


def init_db(app: Flask):
    """Initialize database engine from Flask config with environment-specific settings."""
    global engine
    db_url = app.config.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not configured")
    
    # Environment-specific configuration
    app_env = app.config.get("APP_ENV", "development")
    
    if app_env in ["staging", "production"]:
        # Production-optimized settings for remote database
        engine = create_engine(
            db_url,
            echo=app.config.get("DEBUG", False),
            pool_size=10,                     # Base connection pool size
            max_overflow=20,                  # Additional connections under load
            pool_timeout=30,                  # Wait time for connection from pool (seconds)
            pool_recycle=3600,                # Recycle connections after 1 hour
            pool_pre_ping=True,               # Verify connections before use
            connect_args={
                "connect_timeout": 10,        # Initial connection timeout (seconds)
                "options": "-c statement_timeout=30000"  # Query timeout (30s)
            }
        )
        logger.info(f"Database initialized with production settings: {db_url.split('@')[1] if '@' in db_url else 'remote'}")
    else:
        # Development uses simpler configuration
        engine = create_engine(
            db_url,
            echo=app.config.get("DEBUG", False)
        )
        logger.info(f"Database initialized with development settings: {db_url}")
    
    create_db_tables()


def create_db_tables():
    """Create all tables."""
    if engine is None:
        raise RuntimeError("Database engine not initialized")
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Get a database session."""
    if engine is None:
        raise RuntimeError("Database engine not initialized")
    with Session(engine, expire_on_commit=False) as session:
        yield session
