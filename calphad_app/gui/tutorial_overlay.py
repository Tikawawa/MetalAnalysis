"""First-launch tutorial dialog for CalcPHAD."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QWidget, QSizePolicy,
)

# -- Tutorial step content ------------------------------------------------

TUTORIAL_STEPS: list[dict[str, str]] = [
    {"title": "Welcome to CalcPHAD!",
     "body": ("This app helps you explore how metals behave at different "
              "temperatures and compositions. You don't need to be a "
              "metallurgist \u2014 we'll explain everything along the way!")},
    {"title": "Step 1: Load a Database",
     "body": ("A thermodynamic database contains all the scientific data about "
              "how elements interact. Click \u2018Try Sample (COST507)\u2019 to "
              "load a database with 27 common elements.")},
    {"title": "Step 2: Pick Your Alloy",
     "body": ("Choose two elements to study. For example, select AL (aluminum) "
              "and CU (copper) to explore aluminum\u2013copper alloys \u2014 "
              "used in aircraft and engines.")},
    {"title": "Step 3: Calculate!",
     "body": ("Go to the Phase Diagram tab and click Calculate. The app will "
              "compute which crystal structures exist at every temperature and "
              "composition combination.")},
    {"title": "Step 4: Explore and Learn",
     "body": ("Hover over the diagram to see what each region means. "
              "Use the other tabs to dig deeper:\n\n"
              "\u2022 Equilibrium \u2014 What phases exist at one specific temperature\n"
              "\u2022 Stepping \u2014 Watch phases change as temperature increases\n"
              "\u2022 Scheil \u2014 Simulate real-world metal casting\n\n"
              "Look for the info panels on each tab for explanations!")},
]

_SETTINGS_KEY = "tutorial/completed"
_BTN_STYLE = (
    "QPushButton { background-color: #16213e; color: #4FC3F7; "
    "border: 1px solid #4FC3F7; border-radius: 4px; padding: 6px 16px; "
    "font-size: 13px; font-weight: bold; }"
    "QPushButton:hover { background-color: #1a3a5c; }"
    "QPushButton:disabled { color: #555577; border-color: #333355; "
    "background-color: #1a1a2e; }"
)


class _StepIndicator(QWidget):
    """Row of dots indicating current step position."""

    _COLORS = {True: "#4FC3F7", False: "#555577", "done": "#81C784"}

    def __init__(self, total: int, parent=None):
        super().__init__(parent)
        self._dots: list[QLabel] = []
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for _ in range(total):
            dot = QLabel("\u25CF")
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setFixedSize(18, 18)
            self._dots.append(dot)
            lay.addWidget(dot)

    def set_step(self, index: int):
        for i, dot in enumerate(self._dots):
            if i == index:
                color = "#4FC3F7"
            elif i < index:
                color = "#81C784"
            else:
                color = "#555577"
            dot.setStyleSheet(f"color: {color}; font-size: 16px;")


class TutorialOverlay(QDialog):
    """Modal dialog walking users through CalcPHAD in 5 guided steps.

    Uses QSettings to remember completion so the tutorial only shows
    on first launch (unless the user resets it).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CalcPHAD Tutorial")
        self.setModal(True)
        self.setFixedSize(520, 380)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        self.setStyleSheet(
            "QDialog { background-color: #1a1a2e; border: 1px solid #333355; }"
        )
        self._current_step = 0
        self._total_steps = len(TUTORIAL_STEPS)
        self._setup_ui()
        self._show_step(0)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(12)

        # Top bar
        top = QHBoxLayout()
        lbl = QLabel("CalcPHAD Tutorial")
        lbl.setStyleSheet("color: #4FC3F7; font-size: 13px; font-weight: bold;")
        top.addWidget(lbl)
        top.addStretch()
        self.step_counter = QLabel()
        self.step_counter.setStyleSheet("color: #888; font-size: 12px;")
        top.addWidget(self.step_counter)
        root.addLayout(top)

        # Title and body
        self.title_label = QLabel()
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet(
            "color: #4FC3F7; font-size: 20px; font-weight: bold; "
            "padding-top: 4px; padding-bottom: 2px;"
        )
        root.addWidget(self.title_label)

        self.body_label = QLabel()
        self.body_label.setWordWrap(True)
        self.body_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.body_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.body_label.setStyleSheet(
            "color: #e0e0e0; font-size: 14px; line-height: 1.6; padding: 4px;"
        )
        root.addWidget(self.body_label, stretch=1)

        # Navigation: Back | dots | Next
        nav = QHBoxLayout()
        nav.setSpacing(12)
        self.back_btn = QPushButton("Back")
        self.back_btn.setFixedWidth(80)
        self.back_btn.setStyleSheet(_BTN_STYLE)
        self.back_btn.clicked.connect(self._go_back)
        nav.addWidget(self.back_btn)
        nav.addStretch()
        self.indicator = _StepIndicator(self._total_steps)
        nav.addWidget(self.indicator)
        nav.addStretch()
        self.next_btn = QPushButton("Next")
        self.next_btn.setFixedWidth(80)
        self.next_btn.setStyleSheet(_BTN_STYLE)
        self.next_btn.clicked.connect(self._go_next)
        nav.addWidget(self.next_btn)
        root.addLayout(nav)

        # Don't show again
        self.dont_show_cb = QCheckBox("Don't show this again")
        self.dont_show_cb.setStyleSheet(
            "QCheckBox { color: #888; font-size: 12px; padding-top: 4px; }"
            "QCheckBox::indicator { width: 14px; height: 14px; }"
            "QCheckBox::indicator:unchecked { border: 1px solid #555577; "
            "background-color: #16213e; border-radius: 2px; }"
            "QCheckBox::indicator:checked { border: 1px solid #4FC3F7; "
            "background-color: #4FC3F7; border-radius: 2px; }"
        )
        root.addWidget(self.dont_show_cb)

    # -- Navigation -------------------------------------------------------

    def _show_step(self, index: int):
        self._current_step = index
        step = TUTORIAL_STEPS[index]
        self.step_counter.setText(f"Step {index + 1} of {self._total_steps}")
        self.title_label.setText(step["title"])
        self.body_label.setText(step["body"])
        self.indicator.set_step(index)
        self.back_btn.setEnabled(index > 0)
        self.next_btn.setText("Finish" if index == self._total_steps - 1 else "Next")

    def _go_next(self):
        if self._current_step < self._total_steps - 1:
            self._show_step(self._current_step + 1)
        else:
            if self.dont_show_cb.isChecked():
                self._set_completed(True)
            self.accept()

    def _go_back(self):
        if self._current_step > 0:
            self._show_step(self._current_step - 1)

    # -- QSettings persistence --------------------------------------------

    @staticmethod
    def _get_settings() -> QSettings:
        return QSettings("CalcPHAD", "CalcPHAD")

    @classmethod
    def _set_completed(cls, value: bool):
        cls._get_settings().setValue(_SETTINGS_KEY, value)

    @classmethod
    def was_completed(cls) -> bool:
        """True if the user previously dismissed the tutorial."""
        return bool(cls._get_settings().value(_SETTINGS_KEY, False, type=bool))

    @classmethod
    def reset(cls):
        """Clear the completion flag so the tutorial shows again."""
        cls._get_settings().remove(_SETTINGS_KEY)

    # -- Public API -------------------------------------------------------

    @classmethod
    def show_if_first_launch(cls, parent=None) -> bool:
        """Show the tutorial only on first launch. Returns True if shown."""
        if cls.was_completed():
            return False
        cls(parent).exec()
        return True

    @classmethod
    def show_always(cls, parent=None):
        """Show the tutorial unconditionally (e.g. from a Help menu)."""
        cls(parent).exec()
