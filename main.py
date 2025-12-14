# main.py
import os
import sys
from pathlib import Path

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
    qss_path = resource_path("ui/style.qss")
    try:
        qss = qss_path.read_text(encoding="utf-8")
        app.setStyleSheet(qss)
    except Exception as exc:
        # Don't crash the app if the stylesheet can't be loaded.
        print(f"[QSS] Could not load stylesheet from {qss_path}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    # Ensure database file and schema exist (important for packaged app)
    init_db()

    app = QApplication(sys.argv)
    load_stylesheet(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

