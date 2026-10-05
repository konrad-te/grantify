"""Set up the local SQLite database and the sessions used to read and write it."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


PROJECT_DIR = Path(__file__).resolve().parent.parent
# Keep the database in the project folder regardless of where the app is launched.
# FastAPI can use different worker threads; allow SQLite connections across them.
engine = create_engine(
    f"sqlite:///{PROJECT_DIR / 'gratify.db'}",
    connect_args={"check_same_thread": False},
)
# This factory creates a short-lived database session for each with block.
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    """Shared SQLAlchemy parent that collects table definitions for database creation."""
    pass
