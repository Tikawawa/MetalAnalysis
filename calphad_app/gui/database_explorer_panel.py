"""Database parameter search/explorer as a QDockWidget.

Provides a filterable, searchable view of all thermodynamic parameters
stored in the loaded TDB database.  Users can filter by phase, element,
and parameter type, then browse matching parameters in a table.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDockWidget, QHBoxLayout, QHeaderView,
    QLabel, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)
from pycalphad import Database


# ---------------------------------------------------------------------------
# Helper: format parameter expression for display
# ---------------------------------------------------------------------------

def _format_expression(param: dict) -> str:
    """Return a human-readable representation of a parameter value."""
    expr = param.get("parameter", "")
    if expr is None:
        return ""
    text = str(expr)
    # Truncate very long expressions for table display
    if len(text) > 120:
        return text[:117] + "..."
    return text


def _format_constituents(param: dict) -> str:
    """Return a readable string for the constituent array."""
    raw = param.get("constituent_array", "")
    if raw is None:
        return ""
    if isinstance(raw, (list, tuple)):
        parts = []
        for sublattice in raw:
            if isinstance(sublattice, (list, tuple, frozenset, set)):
                parts.append(",".join(sorted(str(s) for s in sublattice)))
            else:
                parts.append(str(sublattice))
        return " : ".join(parts)
    return str(raw)


# ---------------------------------------------------------------------------
# Dock widget
# ---------------------------------------------------------------------------

class DatabaseExplorerPanel(QDockWidget):
    """Dockable panel for exploring and filtering database parameters."""

    def __init__(self, parent=None):
        super().__init__("Database Explorer", parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )

        self.db: Database | None = None
        self._all_params: list[dict] = []
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title = QLabel("Database Explorer")
        title.setObjectName("heading")
        layout.addWidget(title)

        # --- Filter bar ---
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Phase:"))
        self.phase_combo = QComboBox()
        self.phase_combo.setToolTip(
            "Filter parameters by phase name. "
            "Select (All) to show every phase."
        )
        self.phase_combo.setMinimumWidth(120)
        filter_layout.addWidget(self.phase_combo)

        filter_layout.addWidget(QLabel("Element:"))
        self.element_combo = QComboBox()
        self.element_combo.setToolTip(
            "Filter parameters that reference this element "
            "in their constituent array."
        )
        self.element_combo.setMinimumWidth(80)
        filter_layout.addWidget(self.element_combo)

        filter_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        self.type_combo.setToolTip(
            "Filter by parameter type: G (Gibbs energy), L (interaction), "
            "TC (Curie temperature), BMAGN (Bohr magneton), V0 (volume), etc."
        )
        self.type_combo.setMinimumWidth(100)
        filter_layout.addWidget(self.type_combo)

        self.search_btn = QPushButton("Search")
        self.search_btn.setObjectName("primary")
        self.search_btn.setToolTip("Apply the selected filters.")
        self.search_btn.clicked.connect(self._do_search)
        filter_layout.addWidget(self.search_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setToolTip("Reset all filters and show all parameters.")
        self.clear_btn.clicked.connect(self._clear_filters)
        filter_layout.addWidget(self.clear_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # --- Results table ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Phase", "Type", "Constituents", "Order", "Value"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            "QTableWidget { alternate-background-color: #1f1f3a; }"
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setToolTip(
            "Thermodynamic parameters from the loaded database. "
            "Each row is one parameter entry from the TDB file."
        )
        layout.addWidget(self.table, stretch=1)

        # --- Count label ---
        self.count_label = QLabel("No database loaded")
        self.count_label.setStyleSheet(
            "color: #aaaacc; font-size: 12px; padding: 4px;"
        )
        layout.addWidget(self.count_label)

        scroll.setWidget(container)
        self.setWidget(scroll)

    # ------------------------------------------------------------------
    # Database update
    # ------------------------------------------------------------------

    def update_database(
        self, db: Database, elements: list[str], phases: list[str]
    ):
        """Populate filter combos from the loaded database."""
        self.db = db

        # Fetch all parameters
        try:
            self._all_params = db._parameters.all()
        except Exception:
            self._all_params = []

        # Populate phase filter
        self.phase_combo.blockSignals(True)
        self.phase_combo.clear()
        self.phase_combo.addItem("(All)")
        phase_names = sorted({
            p.get("phase_name", "") for p in self._all_params
            if p.get("phase_name")
        })
        self.phase_combo.addItems(phase_names)
        self.phase_combo.blockSignals(False)

        # Populate element filter
        self.element_combo.blockSignals(True)
        self.element_combo.clear()
        self.element_combo.addItem("(All)")
        self.element_combo.addItems(sorted(elements))
        self.element_combo.blockSignals(False)

        # Populate type filter
        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        self.type_combo.addItem("(All)")
        param_types = sorted({
            p.get("parameter_type", "") for p in self._all_params
            if p.get("parameter_type")
        })
        self.type_combo.addItems(param_types)
        self.type_combo.blockSignals(False)

        # Show all parameters initially
        self._populate_table(self._all_params)

    # ------------------------------------------------------------------
    # Search / filter
    # ------------------------------------------------------------------

    def _do_search(self):
        """Apply the current filters and update the table."""
        phase_filter = self.phase_combo.currentText()
        element_filter = self.element_combo.currentText()
        type_filter = self.type_combo.currentText()

        # Normalize "(All)" to empty string for no-filter
        if phase_filter == "(All)":
            phase_filter = ""
        if element_filter == "(All)":
            element_filter = ""
        if type_filter == "(All)":
            type_filter = ""

        filtered = [
            p for p in self._all_params
            if (
                not phase_filter
                or p.get("phase_name") == phase_filter
            )
            and (
                not type_filter
                or p.get("parameter_type") == type_filter
            )
            and (
                not element_filter
                or element_filter in str(p.get("constituent_array", ""))
            )
        ]

        self._populate_table(filtered)

    def _clear_filters(self):
        """Reset all filter combos and show all parameters."""
        self.phase_combo.setCurrentIndex(0)
        self.element_combo.setCurrentIndex(0)
        self.type_combo.setCurrentIndex(0)
        self._populate_table(self._all_params)

    # ------------------------------------------------------------------
    # Table population
    # ------------------------------------------------------------------

    def _populate_table(self, params: list[dict]):
        """Fill the results table with the given parameter list."""
        self.table.setRowCount(len(params))

        for row_idx, param in enumerate(params):
            phase_item = QTableWidgetItem(
                str(param.get("phase_name", ""))
            )
            type_item = QTableWidgetItem(
                str(param.get("parameter_type", ""))
            )
            const_item = QTableWidgetItem(
                _format_constituents(param)
            )
            order_item = QTableWidgetItem(
                str(param.get("parameter_order", ""))
            )
            value_item = QTableWidgetItem(
                _format_expression(param)
            )

            # Set tooltips with full expression for truncated values
            full_expr = str(param.get("parameter", ""))
            value_item.setToolTip(full_expr)

            self.table.setItem(row_idx, 0, phase_item)
            self.table.setItem(row_idx, 1, type_item)
            self.table.setItem(row_idx, 2, const_item)
            self.table.setItem(row_idx, 3, order_item)
            self.table.setItem(row_idx, 4, value_item)

        total = len(self._all_params)
        shown = len(params)
        self.count_label.setText(
            f"Showing {shown} of {total} parameters"
        )
