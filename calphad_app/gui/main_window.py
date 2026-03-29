"""Main application window with tabbed interface, workflow stepper, unit toggles,
keyboard shortcuts, drag-and-drop support, and welcome dialog."""

from __future__ import annotations

import os
import random

from PyQt6.QtCore import Qt, pyqtSignal, QSettings, QMimeData, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QMainWindow, QStatusBar, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QToolBar, QDialog, QCheckBox, QSizePolicy,
    QMessageBox, QFrame,
)

from gui.database_panel import DatabasePanel
from gui.phase_diagram_panel import PhaseDiagramPanel
from gui.equilibrium_panel import EquilibriumPanel
from gui.stepping_panel import SteppingPanel
from gui.ternary_panel import TernaryPanel
from gui.scheil_panel import ScheilPanel
from gui.thermo_properties_panel import ThermoPropertiesPanel
from gui.single_phase_panel import SinglePhasePanel
from gui.driving_force_panel import DrivingForcePanel
from gui.t0_panel import T0Panel
from gui.volume_panel import VolumePanel
from gui.history_panel import HistoryPanel
from gui.phase_info_panel import PhaseInfoPanel
from gui.database_explorer_panel import DatabaseExplorerPanel
from gui.glossary_panel import GlossaryPanel
from gui.tutorial_overlay import TutorialOverlay
from gui.info_content import DID_YOU_KNOW
from gui.styles import DARK_STYLESHEET


# ---------------------------------------------------------------------------
# Workflow Progress Stepper Widget
# ---------------------------------------------------------------------------

class WorkflowStepper(QWidget):
    """Horizontal progress stepper showing workflow steps with clickable labels."""

    step_clicked = pyqtSignal(int)  # emitted with 0-based step index

    STEP_LABELS = [
        "1. Load Database",
        "2. Configure & Calculate",
        "3. Analyze & Export",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_step = 0
        self._completed: set[int] = set()
        self._buttons: list[QPushButton] = []
        self._arrows: list[QLabel] = []
        self._setup_ui()
        self._refresh()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(0)

        for i, label in enumerate(self.STEP_LABELS):
            btn = QPushButton(label)
            btn.setFlat(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setFixedHeight(36)
            btn.clicked.connect(lambda checked, idx=i: self.step_clicked.emit(idx))
            self._buttons.append(btn)
            layout.addWidget(btn)

            if i < len(self.STEP_LABELS) - 1:
                arrow = QLabel("\u2192")  # right arrow
                arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
                arrow.setFixedWidth(30)
                arrow.setStyleSheet("color: #555577; font-size: 18px;")
                self._arrows.append(arrow)
                layout.addWidget(arrow)

    def set_current_step(self, step: int):
        self._current_step = step
        self._refresh()

    def mark_completed(self, step: int):
        self._completed.add(step)
        self._refresh()

    def _refresh(self):
        for i, btn in enumerate(self._buttons):
            if i in self._completed:
                # Completed: green checkmark prefix
                btn.setText("\u2705 " + self.STEP_LABELS[i])
                btn.setStyleSheet(
                    "QPushButton { color: #81C784; background-color: #1b3a2a; "
                    "border: 1px solid #2e7d32; border-radius: 6px; font-weight: bold; "
                    "padding: 4px 10px; }"
                    "QPushButton:hover { background-color: #254a34; }"
                )
            elif i == self._current_step:
                # Current: highlighted
                btn.setText("\u25b6 " + self.STEP_LABELS[i])
                btn.setStyleSheet(
                    "QPushButton { color: #4FC3F7; background-color: #0f3460; "
                    "border: 2px solid #4FC3F7; border-radius: 6px; font-weight: bold; "
                    "padding: 4px 10px; }"
                    "QPushButton:hover { background-color: #164a80; }"
                )
            else:
                # Upcoming / inactive
                btn.setText(self.STEP_LABELS[i])
                btn.setStyleSheet(
                    "QPushButton { color: #666688; background-color: #16213e; "
                    "border: 1px solid #333355; border-radius: 6px; font-weight: normal; "
                    "padding: 4px 10px; }"
                    "QPushButton:hover { background-color: #1c2b50; }"
                )


# ---------------------------------------------------------------------------
# Welcome Dialog
# ---------------------------------------------------------------------------

class WelcomeDialog(QDialog):
    """First-launch dialog offering sample database or file open."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to CalcPHAD")
        self.setFixedSize(460, 280)
        self.setStyleSheet(
            "QDialog { background-color: #1a1a2e; color: #e0e0e0; }"
            "QLabel { color: #e0e0e0; }"
            "QPushButton { background-color: #0f3460; color: #4FC3F7; border: 1px solid #4FC3F7; "
            "border-radius: 6px; padding: 10px 24px; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background-color: #164a80; }"
            "QCheckBox { color: #888; font-size: 12px; }"
        )

        self.result_action: str = ""  # "sample", "open", or ""

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(30, 24, 30, 20)

        title = QLabel("Welcome to CalcPHAD")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #4FC3F7;")
        layout.addWidget(title)

        subtitle = QLabel("CALPHAD Thermodynamic Calculator")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 13px; color: #aaa;")
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)

        self.sample_btn = QPushButton("Try Sample (COST507)")
        self.sample_btn.clicked.connect(self._on_sample)
        btn_layout.addWidget(self.sample_btn)

        self.open_btn = QPushButton("Open TDB File")
        self.open_btn.setStyleSheet(
            "QPushButton { background-color: #16213e; color: #aaaacc; "
            "border: 1px solid #333355; border-radius: 6px; padding: 10px 24px; "
            "font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background-color: #1c2b50; }"
        )
        self.open_btn.clicked.connect(self._on_open)
        btn_layout.addWidget(self.open_btn)

        layout.addLayout(btn_layout)

        layout.addSpacing(8)

        self.dont_show_cb = QCheckBox("Don't show this again")
        self.dont_show_cb.setChecked(False)
        layout.addWidget(self.dont_show_cb, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

    def _on_sample(self):
        self.result_action = "sample"
        self.accept()

    def _on_open(self):
        self.result_action = "open"
        self.accept()


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """Main application window for CalcPHAD."""

    temp_unit_changed = pyqtSignal(str)   # "K" or "C"
    comp_unit_changed = pyqtSignal(str)   # "wt%" or "mol"
    learning_mode_changed = pyqtSignal(bool)  # True = learning, False = expert

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CalcPHAD - CALPHAD Thermodynamic Calculator")
        self.setMinimumSize(1100, 750)
        self.resize(1280, 850)
        self.setStyleSheet(DARK_STYLESHEET)

        # Enable drag and drop
        self.setAcceptDrops(True)

        self._setup_toolbar()
        self._setup_ui()
        self._setup_dock_widgets()
        self._setup_shortcuts()
        self._connect_signals()

        # Learning mode state (default ON)
        self._learning_mode = True

        # Show welcome dialog on first launch
        self._maybe_show_welcome()

        # Apply initial learning mode state (hide advanced tabs, rename)
        self._on_learning_mode_toggle(True)

        # "Did You Know?" rotating facts in status bar
        self._fact_timer = QTimer(self)
        self._fact_timer.timeout.connect(self._rotate_did_you_know)
        self._fact_timer.start(30000)  # Every 30 seconds

    # ------------------------------------------------------------------
    # Toolbar with unit toggles
    # ------------------------------------------------------------------

    def _setup_toolbar(self):
        toolbar = QToolBar("Units")
        toolbar.setMovable(False)
        toolbar.setStyleSheet(
            "QToolBar { background-color: #16213e; border-bottom: 1px solid #333355; "
            "spacing: 8px; padding: 4px 8px; }"
        )
        self.addToolBar(toolbar)

        # Temperature unit toggle
        self.temp_toggle_btn = QPushButton("Temp: K")
        self.temp_toggle_btn.setCheckable(True)
        self.temp_toggle_btn.setChecked(False)  # default Kelvin
        self.temp_toggle_btn.setFixedSize(100, 28)
        self.temp_toggle_btn.setStyleSheet(
            "QPushButton { background-color: #0f3460; color: #4FC3F7; border: 1px solid #4FC3F7; "
            "border-radius: 4px; font-weight: bold; font-size: 12px; }"
            "QPushButton:checked { background-color: #2e7d32; color: #C8E6C9; border-color: #66BB6A; }"
            "QPushButton:hover { background-color: #164a80; }"
        )
        self.temp_toggle_btn.clicked.connect(self._on_temp_toggle)
        toolbar.addWidget(self.temp_toggle_btn)

        # Composition unit toggle
        self.comp_toggle_btn = QPushButton("Comp: wt%")
        self.comp_toggle_btn.setCheckable(True)
        self.comp_toggle_btn.setChecked(False)  # default wt%
        self.comp_toggle_btn.setFixedSize(110, 28)
        self.comp_toggle_btn.setStyleSheet(
            "QPushButton { background-color: #0f3460; color: #4FC3F7; border: 1px solid #4FC3F7; "
            "border-radius: 4px; font-weight: bold; font-size: 12px; }"
            "QPushButton:checked { background-color: #2e7d32; color: #C8E6C9; border-color: #66BB6A; }"
            "QPushButton:hover { background-color: #164a80; }"
        )
        self.comp_toggle_btn.clicked.connect(self._on_comp_toggle)
        toolbar.addWidget(self.comp_toggle_btn)

        toolbar.addSeparator()

        # History toggle button
        self.history_toggle_btn = QPushButton("History")
        self.history_toggle_btn.setCheckable(True)
        self.history_toggle_btn.setChecked(False)
        self.history_toggle_btn.setFixedSize(90, 28)
        self.history_toggle_btn.setStyleSheet(
            "QPushButton { background-color: #0f3460; color: #4FC3F7; border: 1px solid #4FC3F7; "
            "border-radius: 4px; font-weight: bold; font-size: 12px; }"
            "QPushButton:checked { background-color: #2e7d32; color: #C8E6C9; border-color: #66BB6A; }"
            "QPushButton:hover { background-color: #164a80; }"
        )
        self.history_toggle_btn.clicked.connect(self._on_history_toggle)
        toolbar.addWidget(self.history_toggle_btn)

        # Phase Info toggle button
        self.phase_info_toggle_btn = QPushButton("Phase Info")
        self.phase_info_toggle_btn.setCheckable(True)
        self.phase_info_toggle_btn.setChecked(False)
        self.phase_info_toggle_btn.setFixedSize(100, 28)
        self.phase_info_toggle_btn.setStyleSheet(
            "QPushButton { background-color: #0f3460; color: #4FC3F7; border: 1px solid #4FC3F7; "
            "border-radius: 4px; font-weight: bold; font-size: 12px; }"
            "QPushButton:checked { background-color: #2e7d32; color: #C8E6C9; border-color: #66BB6A; }"
            "QPushButton:hover { background-color: #164a80; }"
        )
        self.phase_info_toggle_btn.clicked.connect(self._on_phase_info_toggle)
        toolbar.addWidget(self.phase_info_toggle_btn)

        # DB Explorer toggle button
        self.db_explorer_toggle_btn = QPushButton("DB Explorer")
        self.db_explorer_toggle_btn.setCheckable(True)
        self.db_explorer_toggle_btn.setChecked(False)
        self.db_explorer_toggle_btn.setFixedSize(110, 28)
        self.db_explorer_toggle_btn.setStyleSheet(
            "QPushButton { background-color: #0f3460; color: #4FC3F7; border: 1px solid #4FC3F7; "
            "border-radius: 4px; font-weight: bold; font-size: 12px; }"
            "QPushButton:checked { background-color: #2e7d32; color: #C8E6C9; border-color: #66BB6A; }"
            "QPushButton:hover { background-color: #164a80; }"
        )
        self.db_explorer_toggle_btn.clicked.connect(self._on_db_explorer_toggle)
        toolbar.addWidget(self.db_explorer_toggle_btn)

        # Glossary toggle button
        self.glossary_toggle_btn = QPushButton("Glossary")
        self.glossary_toggle_btn.setCheckable(True)
        self.glossary_toggle_btn.setChecked(False)
        self.glossary_toggle_btn.setFixedSize(90, 28)
        self.glossary_toggle_btn.setStyleSheet(
            "QPushButton { background-color: #0f3460; color: #4FC3F7; border: 1px solid #4FC3F7; "
            "border-radius: 4px; font-weight: bold; font-size: 12px; }"
            "QPushButton:checked { background-color: #2e7d32; color: #C8E6C9; border-color: #66BB6A; }"
            "QPushButton:hover { background-color: #164a80; }"
        )
        self.glossary_toggle_btn.clicked.connect(self._on_glossary_toggle)
        toolbar.addWidget(self.glossary_toggle_btn)

        toolbar.addSeparator()

        # Learning Mode / Expert Mode toggle
        self.learning_mode_btn = QPushButton("Learning Mode")
        self.learning_mode_btn.setCheckable(True)
        self.learning_mode_btn.setChecked(True)  # Default to learning mode ON
        self.learning_mode_btn.setStyleSheet(
            "QPushButton { background-color: #7B1FA2; color: #CE93D8; border: 1px solid #CE93D8; "
            "border-radius: 4px; font-weight: bold; font-size: 12px; }"
            "QPushButton:checked { background-color: #4A148C; color: #E1BEE7; border-color: #BA68C8; }"
            "QPushButton:hover { background-color: #6A1B9A; }"
        )
        self.learning_mode_btn.clicked.connect(self._on_learning_mode_toggle)
        toolbar.addWidget(self.learning_mode_btn)

    def _on_temp_toggle(self, checked: bool):
        unit = "C" if checked else "K"
        self.temp_toggle_btn.setText(f"Temp: {unit}")
        self.temp_unit_changed.emit(unit)

    def _on_comp_toggle(self, checked: bool):
        unit = "mol" if checked else "wt%"
        self.comp_toggle_btn.setText(f"Comp: {unit}")
        self.comp_unit_changed.emit(unit)

    def _on_history_toggle(self, checked: bool):
        self.history_panel.setVisible(checked)

    def _on_phase_info_toggle(self, checked: bool):
        self.phase_info_panel.setVisible(checked)

    def _on_db_explorer_toggle(self, checked: bool):
        self.db_explorer_panel.setVisible(checked)

    def _on_glossary_toggle(self, checked: bool):
        self.glossary_panel.setVisible(checked)

    def _on_learning_mode_toggle(self, checked: bool):
        """Toggle between Learning Mode and Expert Mode."""
        self._learning_mode = checked
        self.learning_mode_btn.setText("Learning Mode" if checked else "Expert Mode")

        # Show/hide advanced tabs
        advanced_tab_names = {"Thermo Props", "Phase Calc", "Driving Force", "T-Zero", "Volume"}
        for i in range(self.tabs.count()):
            tab_name = self.tabs.tabText(i)
            if tab_name in advanced_tab_names:
                self.tabs.setTabVisible(i, not checked)

        # Rename tabs in learning mode
        if checked:
            for i in range(self.tabs.count()):
                name = self.tabs.tabText(i)
                renames = {"Stepping": "Melting Sim", "Scheil": "Casting Sim", "Equilibrium": "Alloy Analyzer"}
                if name in renames:
                    self.tabs.setTabText(i, renames[name])
        else:
            # Restore original names
            originals = {5: "Scheil", 3: "Stepping", 2: "Equilibrium"}
            for idx, name in originals.items():
                if idx < self.tabs.count():
                    self.tabs.setTabText(idx, name)

        # Broadcast to all panels
        self.learning_mode_changed.emit(checked)

    # ------------------------------------------------------------------
    # Dock widgets
    # ------------------------------------------------------------------

    def _setup_dock_widgets(self):
        # History panel (left)
        self.history_panel = HistoryPanel(self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.history_panel)
        self.history_panel.setVisible(False)
        self.history_panel.visibilityChanged.connect(
            lambda vis: self.history_toggle_btn.setChecked(vis)
        )

        # Phase info panel (right)
        self.phase_info_panel = PhaseInfoPanel(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.phase_info_panel)
        self.phase_info_panel.setVisible(False)
        self.phase_info_panel.visibilityChanged.connect(
            lambda vis: self.phase_info_toggle_btn.setChecked(vis)
        )

        # Database explorer panel (right)
        self.db_explorer_panel = DatabaseExplorerPanel(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.db_explorer_panel)
        self.db_explorer_panel.setVisible(False)
        self.db_explorer_panel.visibilityChanged.connect(
            lambda vis: self.db_explorer_toggle_btn.setChecked(vis)
        )

        # Glossary panel (right)
        self.glossary_panel = GlossaryPanel(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.glossary_panel)
        self.glossary_panel.setVisible(False)
        self.glossary_panel.visibilityChanged.connect(
            lambda vis: self.glossary_toggle_btn.setChecked(vis)
        )

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Workflow stepper
        self.stepper = WorkflowStepper()
        self.stepper.step_clicked.connect(self._on_stepper_clicked)
        layout.addWidget(self.stepper)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #333355;")
        layout.addWidget(sep)

        # Tab widget — use Ignored vertical size so tabs don't resize the window
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.tabs.setUsesScrollButtons(True)

        # Panels — all use Ignored vertical size policy so the tab widget
        # keeps a stable size regardless of which tab is active.
        self.database_panel = DatabasePanel()
        self.phase_diagram_panel = PhaseDiagramPanel()
        self.equilibrium_panel = EquilibriumPanel()
        self.stepping_panel = SteppingPanel()
        self.ternary_panel = TernaryPanel()
        self.scheil_panel = ScheilPanel()
        self.thermo_panel = ThermoPropertiesPanel()
        self.single_phase_panel = SinglePhasePanel()
        self.driving_force_panel = DrivingForcePanel()
        self.t0_panel = T0Panel()
        self.volume_panel = VolumePanel()

        for panel in (self.database_panel, self.phase_diagram_panel,
                      self.equilibrium_panel, self.stepping_panel,
                      self.ternary_panel, self.scheil_panel,
                      self.thermo_panel, self.single_phase_panel,
                      self.driving_force_panel, self.t0_panel,
                      self.volume_panel):
            panel.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored
            )

        self.tabs.addTab(self.database_panel, "Database")
        self.tabs.addTab(self.phase_diagram_panel, "Phase Diagram")
        self.tabs.addTab(self.equilibrium_panel, "Equilibrium")
        self.tabs.addTab(self.stepping_panel, "Stepping")
        self.tabs.addTab(self.ternary_panel, "Ternary")
        self.tabs.addTab(self.scheil_panel, "Scheil")
        self.tabs.addTab(self.thermo_panel, "Thermo Props")
        self.tabs.addTab(self.single_phase_panel, "Phase Calc")
        self.tabs.addTab(self.driving_force_panel, "Driving Force")
        self.tabs.addTab(self.t0_panel, "T-Zero")
        self.tabs.addTab(self.volume_panel, "Volume")

        # Disable calculation tabs until database is loaded
        for i in range(1, self.tabs.count()):
            self.tabs.setTabEnabled(i, False)

        layout.addWidget(self.tabs)

        # Status bar
        self.statusBar().showMessage("Load a TDB database to begin")

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def _setup_shortcuts(self):
        # Ctrl+O  - open database
        open_action = QAction("Open Database", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._shortcut_open_database)
        self.addAction(open_action)

        # Ctrl+1..9  - switch tabs
        for i in range(min(9, self.tabs.count()) if hasattr(self, 'tabs') else 11):
            action = QAction(f"Tab {i+1}", self)
            action.setShortcut(QKeySequence(f"Ctrl+{i+1}"))
            action.triggered.connect(lambda checked, idx=i: self._switch_tab(idx))
            self.addAction(action)

        # F1 - help
        help_action = QAction("Help", self)
        help_action.setShortcut(QKeySequence("F1"))
        help_action.triggered.connect(self._show_help)
        self.addAction(help_action)

        # Ctrl+R - run current calculation
        run_action = QAction("Run Calculation", self)
        run_action.setShortcut(QKeySequence("Ctrl+R"))
        run_action.triggered.connect(self._run_current_calculation)
        self.addAction(run_action)

    def _shortcut_open_database(self):
        self.tabs.setCurrentIndex(0)
        self.database_panel._browse_file()

    def _switch_tab(self, index: int):
        if self.tabs.isTabEnabled(index):
            self.tabs.setCurrentIndex(index)

    def _show_help(self):
        QMessageBox.information(
            self,
            "CalcPHAD - Keyboard Shortcuts & Features",
            "Keyboard Shortcuts:\n"
            "Ctrl+O\tOpen database (.tdb or .dat)\n"
            "Ctrl+1\tDatabase tab\n"
            "Ctrl+2\tPhase Diagram tab\n"
            "Ctrl+3\tEquilibrium / Alloy Analyzer tab\n"
            "Ctrl+4\tStepping / Melting Sim tab\n"
            "Ctrl+5\tTernary tab\n"
            "Ctrl+6\tScheil / Casting Sim tab\n"
            "Ctrl+7\tThermo Properties tab\n"
            "Ctrl+8\tPhase Calculator tab\n"
            "Ctrl+9\tDriving Force tab\n"
            "Ctrl+R\tRun current calculation\n"
            "F1\tShow this help\n\n"
            "Features:\n"
            "- Learning Mode: Simplifies the interface for beginners.\n"
            "  Hides advanced tabs, renames tabs to friendlier names.\n"
            "  Toggle with the purple button in the toolbar.\n"
            "- Expert Mode: Shows all tabs with original names.\n"
            "- Glossary: Searchable dictionary of metallurgical terms.\n"
            "- Did You Know?: Rotating facts in the status bar.\n"
            "- Drag and drop .tdb or .dat files onto the window.\n"
            "- Info panels on each calculation tab explain the concepts.",
        )

    def _rotate_did_you_know(self):
        """Show a random 'Did You Know?' fact in the status bar."""
        if self._learning_mode:
            fact = random.choice(DID_YOU_KNOW)
            self.statusBar().showMessage(f"Did you know? {fact}", 15000)

    def _run_current_calculation(self):
        current = self.tabs.currentIndex()
        panel = self.tabs.widget(current)
        # Try to invoke a calculate method on the active panel
        if hasattr(panel, "_calculate"):
            panel._calculate()
        else:
            self.statusBar().showMessage("Switch to a calculation tab first")

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def _connect_signals(self):
        self.database_panel.database_loaded.connect(self._on_database_loaded)
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Connect unit toggle signals to all panels
        panels = [
            self.database_panel,
            self.phase_diagram_panel,
            self.equilibrium_panel,
            self.stepping_panel,
            self.ternary_panel,
            self.scheil_panel,
            self.thermo_panel,
            self.single_phase_panel,
            self.driving_force_panel,
            self.t0_panel,
            self.volume_panel,
        ]
        for panel in panels:
            if hasattr(panel, "set_temp_unit"):
                self.temp_unit_changed.connect(panel.set_temp_unit)
            if hasattr(panel, "set_comp_unit"):
                self.comp_unit_changed.connect(panel.set_comp_unit)

        # Connect calculation completion to history logging
        self.phase_diagram_panel.calculation_done.connect(self._log_phase_diagram)
        self.equilibrium_panel.calculation_done.connect(self._log_equilibrium)
        self.stepping_panel.calculation_done.connect(self._log_stepping)
        self.ternary_panel.calculation_done.connect(self._log_ternary)
        self.scheil_panel.calculation_done.connect(
            lambda e, c, s: self.history_panel.add_entry("Scheil", e, c, s))
        self.thermo_panel.calculation_done.connect(
            lambda e, c, s: self.history_panel.add_entry("Thermo Props", e, c, s))
        self.single_phase_panel.calculation_done.connect(
            lambda e, c, s: self.history_panel.add_entry("Phase Calc", e, c, s))
        self.driving_force_panel.calculation_done.connect(
            lambda e, c, s: self.history_panel.add_entry("Driving Force", e, c, s))
        self.t0_panel.calculation_done.connect(
            lambda e, c, s: self.history_panel.add_entry("T-Zero", e, c, s))
        self.volume_panel.calculation_done.connect(
            lambda e, c, s: self.history_panel.add_entry("Volume", e, c, s))

        # Connect preset applied signal
        self.database_panel.preset_applied.connect(self._on_preset_applied)

        # Connect history panel re-run signal
        self.history_panel.rerun_requested.connect(self._on_history_rerun)

    def _on_tab_changed(self, index: int):
        # Map tab index to stepper step (3 steps: Load, Configure & Calculate, Analyze & Export)
        if index == 0:
            step = 0
        else:
            step = 1  # All calculation tabs are step 1 (Configure & Calculate)
        self.stepper.set_current_step(step)

    def _on_stepper_clicked(self, step: int):
        # Map stepper step to tab index
        # Step 0 -> Database, Step 1 -> Phase Diagram, Step 2 -> keep current tab
        if step == 0:
            target = 0
        elif step == 1:
            target = 1
        elif step == 2:
            # Stay on the current tab (user's last calculation tab)
            target = self.tabs.currentIndex()
        else:
            target = 0
        if self.tabs.isTabEnabled(target):
            self.tabs.setCurrentIndex(target)

    def _on_database_loaded(self, db, elements, phases):
        # Enable all tabs
        for i in range(1, self.tabs.count()):
            self.tabs.setTabEnabled(i, True)

        # Mark step 1 (Load Database) as completed
        self.stepper.mark_completed(0)
        self.stepper.set_current_step(1)

        # Update all panels
        self.phase_diagram_panel.update_database(db, elements, phases)
        self.equilibrium_panel.update_database(db, elements, phases)
        self.stepping_panel.update_database(db, elements, phases)
        self.ternary_panel.update_database(db, elements, phases)
        self.scheil_panel.update_database(db, elements, phases)
        self.thermo_panel.update_database(db, elements, phases)
        self.single_phase_panel.update_database(db, elements, phases)
        self.driving_force_panel.update_database(db, elements, phases)
        self.t0_panel.update_database(db, elements, phases)
        self.volume_panel.update_database(db, elements, phases)

        # Update dock widgets
        self.db_explorer_panel.update_database(db, elements, phases)

        self.statusBar().showMessage(
            f"Database loaded: {len(elements)} elements, {len(phases)} phases"
        )

        # In learning mode, auto-switch to Phase Diagram tab
        if self._learning_mode:
            self.tabs.setCurrentIndex(1)

    # ------------------------------------------------------------------
    # Preset auto-fill
    # ------------------------------------------------------------------

    def _on_preset_applied(self, preset):
        """Auto-fill calculation panels with the selected alloy preset."""
        # For binary presets (2 elements), set up phase diagram and stepping
        if len(preset.elements) >= 2:
            el1 = preset.elements[0]
            el2 = preset.elements[1]

            # Phase diagram panel
            pdp = self.phase_diagram_panel
            if el1 in [pdp.el1_combo.itemText(i) for i in range(pdp.el1_combo.count())]:
                pdp.el1_combo.setCurrentText(el1)
            if el2 in [pdp.el2_combo.itemText(i) for i in range(pdp.el2_combo.count())]:
                pdp.el2_combo.setCurrentText(el2)
            pdp.t_min_spin.setValue(preset.t_min_k)
            pdp.t_max_spin.setValue(preset.t_max_k)

            # Stepping panel
            sp = self.stepping_panel
            if el1 in [sp.el1_combo.itemText(i) for i in range(sp.el1_combo.count())]:
                sp.el1_combo.setCurrentText(el1)
            if el2 in [sp.el2_combo.itemText(i) for i in range(sp.el2_combo.count())]:
                sp.el2_combo.setCurrentText(el2)
            sp.t_min_spin.setValue(preset.t_min_k)
            sp.t_max_spin.setValue(preset.t_max_k)

            # Set composition in stepping (use first non-base element's wt% converted roughly to mol frac)
            if el2 in preset.composition_wt:
                wt_pct = preset.composition_wt[el2]
                # Rough conversion: for dilute alloys, wt% ~ mol frac * (AW_base/AW_solute) * 100
                from core.units import weight_to_mole
                all_comp = dict(preset.composition_wt)
                balance_wt = 100.0 - sum(all_comp.values())
                all_comp[el1] = balance_wt
                mol_fracs = weight_to_mole(all_comp)
                if el2 in mol_fracs:
                    sp.comp_spin.setValue(mol_fracs[el2])

        # For equilibrium panel, set up composition rows
        ep = self.equilibrium_panel
        # Clear existing rows
        while ep.comp_rows:
            ep._remove_composition_row()
        # Add rows for each non-base element in the preset
        for el, wt in preset.composition_wt.items():
            ep._add_composition_row()
            row = ep.comp_rows[-1]
            if el in [row.element_combo.itemText(i) for i in range(row.element_combo.count())]:
                row.element_combo.setCurrentText(el)
            # Convert wt% to mole fraction for the spin box
            from core.units import weight_to_mole
            all_comp = dict(preset.composition_wt)
            balance_el = preset.elements[0]
            balance_wt = 100.0 - sum(all_comp.values())
            all_comp[balance_el] = balance_wt
            mol_fracs = weight_to_mole(all_comp)
            if el in mol_fracs:
                row.composition_spin.setValue(mol_fracs[el])

        ep.temp_spin.setValue((preset.t_min_k + preset.t_max_k) / 2)

        # Navigate to phase diagram tab
        self.tabs.setCurrentIndex(1)
        self.stepper.mark_completed(1)
        self.stepper.set_current_step(2)

        self.statusBar().showMessage(
            f"Preset applied: {preset.name} ({preset.designation}) - "
            f"ready to calculate on any tab"
        )

    # ------------------------------------------------------------------
    # History re-run
    # ------------------------------------------------------------------

    def _on_history_rerun(self, calc_type: str, elements: list, conditions: dict):
        """Re-load conditions from a history entry into the appropriate panel."""
        if calc_type == "Phase Diagram":
            self.tabs.setCurrentIndex(1)
            pdp = self.phase_diagram_panel
            if len(elements) >= 1:
                pdp.el1_combo.setCurrentText(elements[0])
            if len(elements) >= 2:
                pdp.el2_combo.setCurrentText(elements[1])
            t_min = conditions.get("T_min")
            if t_min is not None:
                pdp.t_min_spin.setValue(t_min)
            t_max = conditions.get("T_max")
            if t_max is not None:
                pdp.t_max_spin.setValue(t_max)

        elif calc_type == "Equilibrium":
            self.tabs.setCurrentIndex(2)
            ep = self.equilibrium_panel
            temp = conditions.get("T")
            if temp is not None:
                ep.temp_spin.setValue(temp)

        elif calc_type == "Stepping":
            self.tabs.setCurrentIndex(3)
            sp = self.stepping_panel
            if len(elements) >= 1:
                sp.el1_combo.setCurrentText(elements[0])
            if len(elements) >= 2:
                sp.el2_combo.setCurrentText(elements[1])
            t_min = conditions.get("T_min")
            if t_min is not None:
                sp.t_min_spin.setValue(t_min)
            t_max = conditions.get("T_max")
            if t_max is not None:
                sp.t_max_spin.setValue(t_max)

        self.statusBar().showMessage(
            "Re-loaded conditions from history. Click Calculate to re-run."
        )

    # ------------------------------------------------------------------
    # History logging slots
    # ------------------------------------------------------------------

    def _log_phase_diagram(self, elements: list, conditions: dict, summary: str):
        self.history_panel.add_entry("Phase Diagram", elements, conditions, summary)

    def _log_equilibrium(self, elements: list, conditions: dict, summary: str):
        self.history_panel.add_entry("Equilibrium", elements, conditions, summary)

    def _log_stepping(self, elements: list, conditions: dict, summary: str):
        self.history_panel.add_entry("Stepping", elements, conditions, summary)

    def _log_ternary(self, elements: list, conditions: dict, summary: str):
        self.history_panel.add_entry("Ternary", elements, conditions, summary)

    # ------------------------------------------------------------------
    # Drag and Drop
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith((".tdb", ".dat")):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith((".tdb", ".dat")):
                self.tabs.setCurrentIndex(0)
                self.database_panel.load_file(path)
                self.statusBar().showMessage(f"Loading dropped file: {os.path.basename(path)}")
                event.acceptProposedAction()
                return
        event.ignore()

    # ------------------------------------------------------------------
    # Welcome Dialog
    # ------------------------------------------------------------------

    def _maybe_show_welcome(self):
        # Skip welcome dialog in offscreen/headless mode
        import os
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            return

        settings = QSettings("CalcPHAD", "CalcPHAD")
        if settings.value("shown_welcome", False, type=bool):
            return

        dialog = WelcomeDialog(self)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            if dialog.dont_show_cb.isChecked():
                settings.setValue("shown_welcome", True)
            if dialog.result_action == "sample":
                self._load_sample_database()
            elif dialog.result_action == "open":
                self._shortcut_open_database()

        # Show tutorial on first launch
        TutorialOverlay.show_if_first_launch(self)

    def _load_sample_database(self):
        """Load the bundled COST507.tdb sample database."""
        # Look for COST507.tdb next to main.py (calphad_app directory)
        app_dir = os.path.dirname(os.path.abspath(__file__))
        sample_path = os.path.join(os.path.dirname(app_dir), "COST507.tdb")
        if not os.path.isfile(sample_path):
            # Also check inside gui's parent
            sample_path = os.path.join(app_dir, "..", "COST507.tdb")

        if os.path.isfile(sample_path):
            self.database_panel.load_file(sample_path)
            self.statusBar().showMessage("Loading sample database (COST507)...")
        else:
            QMessageBox.warning(
                self,
                "Sample Not Found",
                "COST507.tdb was not found next to the application.\n"
                "Please open a TDB file manually.",
            )
