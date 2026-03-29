"""Calculation history log dock widget."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QPushButton,
)


class HistoryPanel(QDockWidget):
    """Dock widget that records every calculation with timestamp, type,
    elements, conditions, and a brief result summary."""

    rerun_requested = pyqtSignal(str, list, dict)  # calc_type, elements, conditions

    def __init__(self, parent=None):
        super().__init__("Calculation History", parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self._entries: list[dict] = []
        self._setup_ui()

    def _setup_ui(self):
        container = QWidget()
        container.setStyleSheet(
            "background-color: #1a1a2e; color: #e0e0e0;"
        )
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QLabel("History")
        header.setStyleSheet(
            "color: #4FC3F7; font-size: 14px; font-weight: bold; padding: 2px;"
        )
        layout.addWidget(header)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "QListWidget { background-color: #16213e; color: #e0e0e0; "
            "border: 1px solid #333355; border-radius: 4px; font-size: 12px; }"
            "QListWidget::item { padding: 4px 6px; }"
            "QListWidget::item:selected { background-color: #0f3460; color: #4FC3F7; }"
        )
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget, stretch=1)

        self.detail_label = QLabel("Select an entry to see details.")
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet(
            "background-color: #16213e; color: #b0b0cc; border: 1px solid #333355; "
            "border-radius: 4px; padding: 8px; font-size: 12px;"
        )
        self.detail_label.setMinimumHeight(80)
        layout.addWidget(self.detail_label)

        self.rerun_btn = QPushButton("Re-run")
        self.rerun_btn.setStyleSheet(
            "QPushButton { background-color: #1a3a5c; color: #4FC3F7; "
            "border: 1px solid #4FC3F7; border-radius: 4px; padding: 4px 12px; "
            "font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background-color: #2a4a6c; }"
            "QPushButton:disabled { background-color: #1a1a2e; color: #555555; "
            "border-color: #555555; }"
        )
        self.rerun_btn.setEnabled(False)
        self.rerun_btn.setToolTip("Re-run the selected calculation with the same parameters.")
        self.rerun_btn.clicked.connect(self._on_rerun_clicked)
        layout.addWidget(self.rerun_btn)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        clear_btn = QPushButton("Clear History")
        clear_btn.setStyleSheet(
            "QPushButton { background-color: #4a1a1a; color: #E57373; "
            "border: 1px solid #E57373; border-radius: 4px; padding: 4px 12px; "
            "font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background-color: #6a2a2a; }"
        )
        clear_btn.clicked.connect(self._clear_history)
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)

        self.setWidget(container)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_entry(self, calc_type: str, elements: list[str], conditions: dict, summary: str):
        """Record a calculation in the history log.

        Parameters
        ----------
        calc_type : str
            One of "Phase Diagram", "Equilibrium", "Stepping".
        elements : list[str]
            Elements involved, e.g. ["AL", "CU"].
        conditions : dict
            Key conditions such as {"T_min": 300, "T_max": 1400}.
        summary : str
            Brief result summary text.
        """
        timestamp = datetime.now()
        entry = {
            "timestamp": timestamp,
            "type": calc_type,
            "elements": elements,
            "conditions": conditions,
            "summary": summary,
        }
        self._entries.append(entry)

        # Format for list display
        time_str = timestamp.strftime("%H:%M:%S")
        elem_str = "-".join(elements)
        display_text = f"[{time_str}] {calc_type}: {elem_str}"

        item = QListWidgetItem(display_text)
        item.setToolTip(summary)
        self.list_widget.addItem(item)
        self.list_widget.scrollToBottom()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_selection_changed(self, row: int):
        if row < 0 or row >= len(self._entries):
            self.detail_label.setText("Select an entry to see details.")
            self.rerun_btn.setEnabled(False)
            return

        self.rerun_btn.setEnabled(True)

        entry = self._entries[row]
        ts = entry["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
        elem_str = ", ".join(entry["elements"])

        cond_parts = []
        for k, v in entry["conditions"].items():
            if isinstance(v, float):
                cond_parts.append(f"{k} = {v:.2f}")
            else:
                cond_parts.append(f"{k} = {v}")
        cond_str = "; ".join(cond_parts) if cond_parts else "N/A"

        detail = (
            f"Timestamp: {ts}\n"
            f"Type: {entry['type']}\n"
            f"Elements: {elem_str}\n"
            f"Conditions: {cond_str}\n"
            f"Result: {entry['summary']}"
        )
        self.detail_label.setText(detail)

    def _on_rerun_clicked(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self._entries):
            return
        entry = self._entries[row]
        self.rerun_requested.emit(
            entry["type"], list(entry["elements"]), dict(entry["conditions"])
        )

    def _clear_history(self):
        self._entries.clear()
        self.list_widget.clear()
        self.detail_label.setText("History cleared.")
        self.rerun_btn.setEnabled(False)
