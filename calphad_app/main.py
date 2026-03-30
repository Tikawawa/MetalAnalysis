#!/usr/bin/env python3
"""CalcPHAD - CALPHAD Thermodynamic Calculator Application."""

import sys
import os

# Ensure the app directory is on the path for imports
app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

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
    icon_path = os.path.join(app_dir, "calphad.png")
    if os.path.isfile(icon_path):
        from PyQt6.QtGui import QIcon
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
