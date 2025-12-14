from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base


import os
from pathlib import Path

def _get_app_data_dir() -> Path:
    """
    Return a writable application data directory.
    macOS: ~/Library/Application Support/CV Manager
    Fallback: ~/.cv_manager
    """
    home = Path.home()
    mac_dir = home / "Library" / "Application Support" / "CV Manager"
    try:
        mac_dir.mkdir(parents=True, exist_ok=True)
        return mac_dir
    except Exception:
        fallback = home / ".cv_manager"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

APP_DATA_DIR = _get_app_data_dir()
DB_PATH = APP_DATA_DIR / "cv_manager.sqlite"

# Optional migration: if an old DB exists in ./data/, copy it once
legacy_path = Path("data") / "cv_manager.sqlite"
if legacy_path.exists() and not DB_PATH.exists():
    try:
        DB_PATH.write_bytes(legacy_path.read_bytes())
    except Exception:
        pass

DATABASE_URL = f"sqlite:///{DB_PATH}"

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