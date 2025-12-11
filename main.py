# main.py
import sys
from PySide6.QtWidgets import QApplication
from pathlib import Path
from ui.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    with open("ui/style.qss") as f:
        app.setStyleSheet(f.read())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

