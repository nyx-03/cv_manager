from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session

import sys
import importlib
from pathlib import Path
import os


def is_frozen_app() -> bool:
    """True when running from a PyInstaller bundle (.app/.exe)."""
    return bool(getattr(sys, "frozen", False)) or bool(getattr(sys, "_MEIPASS", None))


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


# ---- Helper functions for DB path and reset ----
def get_db_path() -> Path:
    """Return the absolute path to the SQLite database file."""
    return DB_PATH


def reset_database() -> None:
    """Delete the SQLite database and related WAL/SHM files if they exist."""
    try:
        engine.dispose()
    except Exception:
        pass

    for suffix in ("", "-wal", "-shm"):
        p = Path(str(DB_PATH) + suffix)
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass

    # Reset initialization flag so DB can be recreated on next start / next session.
    global _DB_INITIALIZED
    _DB_INITIALIZED = False


def reset_database_and_init() -> None:
    """Reset DB files then recreate schema immediately."""
    reset_database()
    init_db()


def resource_path(relative: str) -> Path:
    """Return an absolute path to a bundled resource (PyInstaller) or a dev path."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / relative
    return Path(__file__).resolve().parent / relative


# Optional migration/seed: copy a seed DB once (useful in dev).
# In packaged apps, this is disabled by default to avoid shipping a dev DB.
# Enable explicitly with environment variable: CVM_SEED_DB=1
seed_candidates = [
    resource_path("data/cv_manager.sqlite"),
    Path.cwd() / "data" / "cv_manager.sqlite",
]

_seed_enabled = (not is_frozen_app()) or (os.environ.get("CVM_SEED_DB", "").strip().lower() in {"1", "true", "yes", "on"})
if _seed_enabled and (not DB_PATH.exists()):
    for seed in seed_candidates:
        try:
            if seed.exists():
                DB_PATH.write_bytes(seed.read_bytes())
                break
        except Exception:
            # If copy fails, we'll fall back to creating an empty DB and creating tables.
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


_DB_INITIALIZED = False


def init_db() -> None:
    """Ensure DB file exists and schema is created.

    In packaged apps, the DB may be freshly created in Application Support.
    We must create the tables at least once.

    This function is idempotent.
    """
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return

    # Best-effort: import models so SQLAlchemy knows about mapped tables.
    # If the project uses a different module name, this won't crash the app.
    for mod_name in ("models", "ui.models", "db.models"):
        try:
            importlib.import_module(mod_name)
            break
        except Exception:
            continue

    try:
        Base.metadata.create_all(bind=engine)
        _DB_INITIALIZED = True
    except Exception as exc:
        print(f"[DB] init_db failed: {exc}", file=sys.stderr)
        # Do not raise here: we prefer the UI to show an error rather than immediate exit.


def get_session() -> Session:
    """Convenience helper returning a new SessionLocal after ensuring DB is initialized."""
    init_db()
    return SessionLocal()