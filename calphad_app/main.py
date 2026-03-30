#!/usr/bin/env python3
"""CalcPHAD - CALPHAD Thermodynamic Calculator Application."""

import sys
import os

# Determine base path: PyInstaller frozen bundle or normal source tree
if getattr(sys, "frozen", False):
    # Running as a PyInstaller bundle — resources extracted to _MEIPASS
    _BASE_DIR = sys._MEIPASS
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def resource_path(relative_path: str) -> str:
    """Get absolute path to a bundled resource (works in dev and PyInstaller)."""
    return os.path.join(_BASE_DIR, relative_path)


# Ensure the app directory is on the path for imports
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from gui.main_window import MainWindow


def main():
    # Force software OpenGL to prevent segfault from matplotlib canvas
    # rendering conflicts during rapid tab switching (PyQt6 + GPU issue)
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("LIBGL_ALWAYS_SOFTWARE", "1")

    app = QApplication(sys.argv)
    app.setApplicationName("CalcPHAD")
    app.setOrganizationName("MetalAnalysis")

    # Set app icon if available
    icon_path = resource_path("calphad.png")
    if os.path.isfile(icon_path):
        from PyQt6.QtGui import QIcon
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
