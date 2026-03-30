"""Dark professional theme stylesheet for the CALPHAD application."""

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Segoe UI", "Ubuntu", sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #333355;
    background-color: #1a1a2e;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #16213e;
    color: #aaaacc;
    padding: 6px 10px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
}

QTabBar::tab:selected {
    background-color: #0f3460;
    color: #4FC3F7;
    border-bottom: 2px solid #4FC3F7;
}

QTabBar::tab:hover:!selected {
    background-color: #1a2a4a;
    color: #ccccee;
}

QPushButton {
    background-color: #0f3460;
    color: #e0e0e0;
    border: 1px solid #1a4a7a;
    padding: 8px 18px;
    border-radius: 5px;
    font-weight: bold;
    min-height: 28px;
}

QPushButton:hover {
    background-color: #1a4a7a;
    border-color: #4FC3F7;
}

QPushButton:pressed {
    background-color: #0a2540;
}

QPushButton:disabled {
    background-color: #222244;
    color: #555577;
    border-color: #333355;
}

QPushButton#primary {
    background-color: #1565C0;
    border-color: #1976D2;
}

QPushButton#primary:hover {
    background-color: #1976D2;
}

QPushButton#success {
    background-color: #2E7D32;
    border-color: #388E3C;
}

QPushButton#success:hover {
    background-color: #388E3C;
}

QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #333355;
    padding: 6px 10px;
    border-radius: 4px;
    selection-background-color: #0f3460;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #4FC3F7;
}

QComboBox {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #333355;
    padding: 6px 10px;
    border-radius: 4px;
    min-height: 24px;
}

QComboBox:hover {
    border-color: #4FC3F7;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #16213e;
    color: #e0e0e0;
    selection-background-color: #0f3460;
    border: 1px solid #333355;
}

QListWidget {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #333355;
    border-radius: 4px;
    padding: 4px;
}

QListWidget::item:selected {
    background-color: #0f3460;
    color: #4FC3F7;
}

QTableWidget {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #333355;
    border-radius: 4px;
    gridline-color: #333355;
}

QTableWidget::item {
    padding: 4px 8px;
}

QTableWidget::item:selected {
    background-color: #0f3460;
}

QHeaderView::section {
    background-color: #0f3460;
    color: #4FC3F7;
    padding: 6px 8px;
    border: 1px solid #333355;
    font-weight: bold;
}

QGroupBox {
    border: 1px solid #333355;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
    color: #4FC3F7;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QLabel {
    color: #ccccdd;
}

QLabel#heading {
    color: #4FC3F7;
    font-size: 16px;
    font-weight: bold;
}

QLabel#status {
    color: #81C784;
    font-size: 12px;
}

QLabel#error {
    color: #E57373;
    font-size: 12px;
}

QProgressBar {
    background-color: #16213e;
    border: 1px solid #333355;
    border-radius: 4px;
    text-align: center;
    color: #e0e0e0;
    min-height: 20px;
}

QProgressBar::chunk {
    background-color: #1565C0;
    border-radius: 3px;
}

QScrollBar:vertical {
    background-color: #1a1a2e;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #333355;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #444477;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QStatusBar {
    background-color: #0f3460;
    color: #ccccdd;
    border-top: 1px solid #333355;
}

QMenuBar {
    background-color: #16213e;
    color: #ccccdd;
}

QMenuBar::item:selected {
    background-color: #0f3460;
}

QMenu {
    background-color: #16213e;
    color: #ccccdd;
    border: 1px solid #333355;
}

QMenu::item:selected {
    background-color: #0f3460;
}

QSplitter::handle {
    background-color: #333355;
    width: 2px;
}

/* ===== Stepper Widget ===== */

QLabel#stepLabel {
    color: #777799;
    font-size: 12px;
    font-weight: bold;
    padding: 4px 12px;
    border-bottom: 2px solid transparent;
}

QLabel#stepLabelActive {
    color: #4FC3F7;
    font-size: 12px;
    font-weight: bold;
    padding: 4px 12px;
    border-bottom: 2px solid #4FC3F7;
}

QLabel#stepLabelCompleted {
    color: #81C784;
    font-size: 12px;
    font-weight: bold;
    padding: 4px 12px;
    border-bottom: 2px solid #81C784;
}

QFrame#stepperFrame {
    background-color: #16213e;
    border: 1px solid #333355;
    border-radius: 6px;
    padding: 6px 10px;
}

/* ===== Info Label (preset suggestions) ===== */

QLabel#infoLabel {
    background-color: #0d2744;
    color: #90CAF9;
    border: 1px solid #1565C0;
    border-radius: 5px;
    padding: 8px 12px;
    font-size: 12px;
}

/* ===== Summary Label (plain-English summaries) ===== */

QLabel#summaryLabel {
    background-color: #1c1c34;
    color: #b0b0cc;
    border: 1px solid #2a2a4a;
    border-radius: 5px;
    padding: 8px 12px;
    font-size: 12px;
    font-style: italic;
}

/* ===== Warning Label ===== */

QLabel#warningLabel {
    color: #FFB74D;
    font-size: 12px;
    font-weight: bold;
    padding: 4px 8px;
}

/* ===== Balance Indicator ===== */

QLabel#balanceValid {
    color: #81C784;
    font-size: 12px;
    font-weight: bold;
}

QLabel#balanceOver {
    color: #E57373;
    font-size: 12px;
    font-weight: bold;
}

/* ===== Welcome Dialog ===== */

QDialog#welcomeDialog {
    background-color: #1a1a2e;
    border: 2px solid #333355;
    border-radius: 10px;
}

QDialog#welcomeDialog QLabel#welcomeTitle {
    color: #4FC3F7;
    font-size: 22px;
    font-weight: bold;
    padding-bottom: 8px;
}

QDialog#welcomeDialog QLabel#welcomeSubtitle {
    color: #aaaacc;
    font-size: 14px;
    padding-bottom: 12px;
}

QDialog#welcomeDialog QPushButton {
    min-width: 140px;
    padding: 10px 24px;
    font-size: 14px;
}

/* ===== Toolbar ===== */

QToolBar {
    background-color: #16213e;
    border-bottom: 1px solid #333355;
    spacing: 4px;
    padding: 2px 6px;
}

QToolBar::separator {
    width: 1px;
    background-color: #333355;
    margin: 4px 6px;
}

QToolButton {
    background-color: transparent;
    color: #ccccdd;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 5px 10px;
    font-weight: bold;
}

QToolButton:hover {
    background-color: #1a2a4a;
    border-color: #4FC3F7;
    color: #4FC3F7;
}

QToolButton:pressed {
    background-color: #0f3460;
}

QToolButton:checked {
    background-color: #0f3460;
    color: #4FC3F7;
    border-color: #4FC3F7;
}

/* ===== Tooltip ===== */

QToolTip {
    background-color: #222244;
    color: #e0e0e0;
    border: 1px solid #4FC3F7;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 13px;
    max-width: 360px;
}
"""
