from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///data/cv_manager.sqlite"

# SQLite + Qt: allow usage from the GUI thread and worker threads if needed.
# (Qt can create signals/slots that end up touching the DB from different threads.)
engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):  # pragma: no cover
    # Enable foreign keys for SQLite
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()