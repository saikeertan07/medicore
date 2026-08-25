import logging
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

logger = logging.getLogger("medicore.database")

def create_db_engine():
    # Production strictly prohibits SQLite
    if settings.ENVIRONMENT == "production":
        if settings.DATABASE_ENGINE != "postgresql":
            raise RuntimeError(
                "FATAL: Production mode requires DATABASE_ENGINE='postgresql'. "
                f"Configured engine '{settings.DATABASE_ENGINE}' is prohibited in production."
            )

    # When PostgreSQL is explicitly chosen or running in production
    if settings.DATABASE_ENGINE == "postgresql":
        safe_url = settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL
        logger.info(f"Connecting to authoritative PostgreSQL database at {safe_url}")
        try:
            pg_engine = create_engine(
                settings.DATABASE_URL,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                connect_args={"connect_timeout": 5}
            )
            # Fail loudly immediately if connection cannot be established
            with pg_engine.connect() as conn:
                logger.info("Successfully connected to authoritative PostgreSQL database.")
            return pg_engine
        except Exception as exc:
            logger.error(f"FATAL: PostgreSQL connection failed for {safe_url}: {exc}")
            raise RuntimeError(
                f"Database connection failure: PostgreSQL connection to {safe_url} failed: {exc}. "
                f"MediCore AI will NOT start with an unreachable PostgreSQL engine. "
                f"Silent fallback to SQLite is strictly disabled."
            ) from exc

    elif settings.DATABASE_ENGINE == "sqlite":
        # SQLite is strictly permitted ONLY in non-production environments
        if settings.ENVIRONMENT == "production":
            raise RuntimeError("FATAL: SQLite is strictly prohibited in production mode.")
        logger.info(f"Using explicitly configured development/testing SQLite database: {settings.SQLITE_URL}")
        return create_engine(
            settings.SQLITE_URL,
            connect_args={"check_same_thread": False}
        )
    else:
        raise RuntimeError(
            f"Invalid DATABASE_ENGINE='{settings.DATABASE_ENGINE}'. Supported engines are 'postgresql' and 'sqlite'."
        )

engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
