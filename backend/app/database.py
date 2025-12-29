from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Create Base first (needed for Alembic)
Base = declarative_base()

# Lazy engine creation to avoid connection errors during import
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create SQLAlchemy engine"""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10
        )
    return _engine


def get_session_local():
    """Get or create SessionLocal"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


# For backward compatibility
engine = property(lambda self: get_engine())
SessionLocal = property(lambda self: get_session_local())


def get_db():
    """Database dependency for FastAPI routes"""
    session_local = get_session_local()
    db = session_local()
    try:
        yield db
    finally:
        db.close()
