"""Database connection pool and session manager.

Dynamically adapts to changes in settings.data_dir to support sandboxed unit tests.
"""

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger

from src.config import settings
from src.database.models import Base

# Dynamic connection cache
_engine = None
_SessionLocal = None
_last_url = None
_db_initialized = False


def get_engine():
    """Get the SQLAlchemy database engine dynamically, adapting to path changes."""
    global _engine, _last_url, _db_initialized
    url = settings.database_url
    
    # Adapt default SQLite URL if settings.data_dir is monkeypatched
    if url == "sqlite:///data/synapse.db":
        db_file = settings.data_dir / "synapse.db"
        url = f"sqlite:///{db_file.resolve()}"

    if _engine is None or url != _last_url:
        _last_url = url
        _db_initialized = False  # Reset initialization flag for new database connection
        
        connect_args = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            # Ensure local directory for SQLite database file exists
            from pathlib import Path
            db_path = url.replace("sqlite:///", "")
            if db_path != ":memory:":
                db_file = Path(db_path)
                db_file.parent.mkdir(parents=True, exist_ok=True)
            _engine = create_engine(url, connect_args=connect_args)
        elif url.startswith("postgresql"):
            _engine = create_engine(
                url,
                pool_size=15,
                max_overflow=25,
                pool_recycle=300,
                pool_pre_ping=True
            )
        else:
            _engine = create_engine(url)
            
        logger.info(f"Database Engine created for: {url.split('@')[-1] if '@' in url else url}")
        
    return _engine


def get_sessionmaker():
    """Get the sessionmaker factory dynamically."""
    global _SessionLocal
    engine = get_engine()
    if _SessionLocal is None or _SessionLocal.kw.get("bind") != engine:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


def init_db():
    """Verify connections and auto-initialize tables (ideal for SQLite/local)."""
    global _db_initialized
    try:
        engine = get_engine()
        logger.info("Initializing database schema...")
        Base.metadata.create_all(bind=engine)
        _db_initialized = True
        logger.info("Database schema initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise e


@contextmanager
def get_db_session():
    """Transactional session context manager (for standard scripts)."""
    global _db_initialized
    if not _db_initialized:
        init_db()
    session_factory = get_sessionmaker()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error occurred: {e}")
        raise e
    finally:
        session.close()


def get_db():
    """Dependency helper for FastAPI route dependency injection (Depends(get_db))."""
    global _db_initialized
    if not _db_initialized:
        init_db()
    session_factory = get_sessionmaker()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
