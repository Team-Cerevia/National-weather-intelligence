"""SQLAlchemy 2.x database session and connection engine for PostgreSQL + PostGIS."""

import os
from collections.abc import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""

    pass


def get_database_url() -> str:
    """Resolve database URL from environment variables or use the development default.

    Development default:
    postgresql+psycopg://weather_user:weather_password@localhost:5432/weather_db
    """
    url = os.getenv("DATABASE_URL")
    if url:
        # Standardize postgresql:// to postgresql+psycopg:// for SQLAlchemy psycopg v3 driver
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    user = os.getenv("POSTGRES_USER", "weather_user")
    password = os.getenv("POSTGRES_PASSWORD", "weather_password")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "weather_db")

    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db_name}"


DATABASE_URL = get_database_url()

# SQLAlchemy 2.x Engine
engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session Factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding an isolated SQLAlchemy database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine: Engine | None = None) -> None:
    """Initialize database schema and ensure the PostGIS extension is enabled.

    Creates tables registered on Base.metadata using modern SQLAlchemy 2.x DDL execution.
    """
    eng = target_engine or engine
    with eng.begin() as conn:
        if eng.dialect.name == "postgresql":
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        Base.metadata.create_all(conn)
