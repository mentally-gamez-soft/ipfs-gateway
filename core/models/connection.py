from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel
from flask import Flask
from typing import Generator
import logging

logger = logging.getLogger(__name__)

engine = None


def init_db(app: Flask):
    """Initialize database engine from Flask config."""
    global engine
    db_url = app.config.get("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not configured")
    
    engine = create_engine(db_url, echo=app.config.get("DEBUG", False))
    create_db_tables()
    logger.info(f"Database initialized: {db_url}")


def create_db_tables():
    """Create all tables."""
    if engine is None:
        raise RuntimeError("Database engine not initialized")
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    """Get a database session."""
    if engine is None:
        raise RuntimeError("Database engine not initialized")
    with Session(engine) as session:
        yield session
