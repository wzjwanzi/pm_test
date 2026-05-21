from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from desktop_qt.main_window import MainWindow


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
