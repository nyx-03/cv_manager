# main.py
import sys
from pathlib import Path

import logging
from utils.logging_setup import setup_logging

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from db import init_db


def resource_path(relative: str) -> Path:
    """Return an absolute Path to a resource.

    Works in development and in PyInstaller (onedir/onefile) bundles.
    """
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / relative
    # Dev mode: relative to this file
    return Path(__file__).resolve().parent / relative


def load_stylesheet(app: QApplication) -> None:
    log = logging.getLogger("cv_manager")
    qss_path = resource_path("ui/style.qss")
    try:
        qss = qss_path.read_text(encoding="utf-8")
        app.setStyleSheet(qss)
    except Exception as exc:
        # Don't crash the app if the stylesheet can't be loaded.
        log.exception("[QSS] Could not load stylesheet from %s", qss_path)


def _install_excepthook() -> None:
    """Log all uncaught exceptions to the configured logger."""
    log = logging.getLogger("cv_manager")

    def _hook(exc_type, exc, tb):
        # KeyboardInterrupt: keep default behavior (stop quickly)
        if exc_type is KeyboardInterrupt:
            sys.__excepthook__(exc_type, exc, tb)
            return
        log.critical("Uncaught exception", exc_info=(exc_type, exc, tb))

    sys.excepthook = _hook


if __name__ == "__main__":
    log_mgr = setup_logging()
    log_mgr.start()
    _install_excepthook()
    log = logging.getLogger("cv_manager")
    log.info("Application starting")

    try:
        init_db()
    except Exception:
        log.exception("Database initialization failed")
        raise

    try:
        app = QApplication(sys.argv)
        load_stylesheet(app)
        window = MainWindow()
        window.show()
        exit_code = app.exec()
        log.info("Application exited with code %s", exit_code)
        sys.exit(exit_code)
    except Exception:
        log.exception("Fatal error in Qt main loop")
        raise
