"""Scheil-Gulliver solidification simulation panel.

Simulates non-equilibrium solidification using the Scheil model,
which assumes complete mixing in the liquid, no diffusion in the solid,
and local equilibrium at the solid-liquid interface.  Provides
solidification curves, phase sequence tables, stacked-area phase plots,
and microsegregation profiles.
"""

from __future__ import annotations

import datetime
import traceback

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)
from gui.lazy_canvas import LazyCanvas
from pycalphad import Database

from core.units import k_to_c, c_to_k, format_temp, mole_to_weight, weight_to_mole
from gui.info_content import TAB_INFO, TOOLTIPS

# ---------------------------------------------------------------------------
# Optional scheil import -- graceful fallback
# ---------------------------------------------------------------------------

_SCHEIL_AVAILABLE = True
_SCHEIL_IMPORT_ERROR = ""

try:
    from scheil import simulate_scheil_solidification
except ImportError as _exc:
    _SCHEIL_AVAILABLE = False
    _SCHEIL_IMPORT_ERROR = (
        "The 'scheil' package is not installed.\n\n"
        "Install it with:\n    pip install scheil\n\n"
        f"Original error: {_exc}"
    )

# ---------------------------------------------------------------------------
# Phase color palette
# ---------------------------------------------------------------------------

PHASE_COLORS = [
    "#4FC3F7", "#81C784", "#FFB74D", "#E57373", "#BA68C8",
    "#4DB6AC", "#FFD54F", "#7986CB", "#A1887F", "#90A4AE",
    "#F06292", "#AED581", "#64B5F6", "#FF8A65", "#CE93D8",
]

# ---------------------------------------------------------------------------
# Friendly error messages
# ---------------------------------------------------------------------------

_FRIENDLY_ERRORS: list[tuple[str, str]] = [
    ("convergence|did not converge",
     "The Scheil simulation could not converge.  This often happens when "
     "the start temperature is too far from the liquidus or the step size "
     "is too large.  Try raising the start temperature or reducing the "
     "step size."),
    ("singular matrix",
     "The calculation hit a numerical singularity.  Try adjusting the "
     "composition slightly or changing the start temperature."),
    ("Database|TDB",
     "There may be a problem with the thermodynamic database for this "
     "element combination.  Make sure all selected elements are covered "
     "by the loaded database."),
    ("composition|fraction",
     "One or more composition values appear to be out of range.  Ensure "
     "that all mole fractions are between 0 and 1 and do not exceed 1 "
     "in total."),
]


def _friendly_error(raw: str) -> str:
    """Return a user-friendly error message based on the raw traceback."""
    import re
    for pattern, friendly in _FRIENDLY_ERRORS:
        if re.search(pattern, raw, re.IGNORECASE):
            return friendly
    return (
        "The Scheil simulation did not succeed.  This can happen when the "
        "thermodynamic database does not fully cover the requested "
        "conditions.\n\n"
        "Suggestions:\n"
        "  - Ensure all elements are present in the database.\n"
        "  - Start from a temperature well above the expected liquidus.\n"
        "  - Try a smaller step size (e.g. 1 K).\n"
        "  - Reduce extreme composition values."
    )


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

class ScheilWorker(QThread):
    """Background worker for Scheil solidification simulation."""

    finished = pyqtSignal(object)  # dict with results or error

    def __init__(
        self,
        db: Database,
        comps: list[str],
        phases: list[str],
        conditions: dict,
        start_temperature: float,
        step_temperature: float,
    ):
        super().__init__()
        self.db = db
        self.comps = comps
        self.phases = phases
        self.conditions = conditions
        self.start_temperature = start_temperature
        self.step_temperature = step_temperature

    def run(self):
        try:
            sol_res = simulate_scheil_solidification(
                self.db,
                self.comps,
                self.phases,
                self.conditions,
                start_temperature=self.start_temperature,
                step_temperature=self.step_temperature,
            )

            # Extract data from the result object
            temperatures = list(sol_res.temperatures)
            fraction_solid = list(sol_res.fraction_solid)

            # Phase amounts: dict of phase name -> list of fractions
            phase_amounts: dict[str, list[float]] = {}
            if hasattr(sol_res, "phase_amounts") and sol_res.phase_amounts:
                for phase_name, amounts in sol_res.phase_amounts.items():
                    phase_amounts[phase_name] = list(amounts)

            # Cumulative phase amounts (for stacked area)
            cum_phase_amounts: dict[str, list[float]] = {}
            if hasattr(sol_res, "cum_phase_amounts") and sol_res.cum_phase_amounts:
                for phase_name, amounts in sol_res.cum_phase_amounts.items():
                    cum_phase_amounts[phase_name] = list(amounts)

            # Liquid composition for microsegregation
            liquid_comp: dict[str, list[float]] = {}
            if hasattr(sol_res, "liquid_compositions") and sol_res.liquid_compositions:
                for el, comps in sol_res.liquid_compositions.items():
                    liquid_comp[el] = list(comps)
            elif hasattr(sol_res, "eq_liquid_compositions"):
                for el, comps in sol_res.eq_liquid_compositions.items():
                    liquid_comp[el] = list(comps)

            self.finished.emit({
                "success": True,
                "temperatures": temperatures,
                "fraction_solid": fraction_solid,
                "phase_amounts": phase_amounts,
                "cum_phase_amounts": cum_phase_amounts,
                "liquid_comp": liquid_comp,
            })

        except Exception:
            self.finished.emit({
                "success": False,
                "error": traceback.format_exc(),
            })


# ---------------------------------------------------------------------------
# Composition row widget
# ---------------------------------------------------------------------------

class _CompositionRow(QWidget):
    """A single element + composition input row."""

    def __init__(self, elements: list[str], comp_unit: str = "mole_fraction",
                 parent=None):
        super().__init__(parent)
        self._comp_unit = comp_unit
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.element_combo = QComboBox()
        self.element_combo.addItems(elements)
        self.element_combo.setToolTip(
            "Select an alloying element. The balance element is determined "
            "automatically from the remaining fraction."
        )
        layout.addWidget(self.element_combo)

        self.unit_label = QLabel(self._label_text())
        layout.addWidget(self.unit_label)

        self.composition_spin = QDoubleSpinBox()
        self._apply_unit_range()
        self.composition_spin.setToolTip(
            "Composition of this element. The balance element accounts for "
            "the remainder."
        )
        layout.addWidget(self.composition_spin)

    def _label_text(self) -> str:
        return "wt% =" if self._comp_unit == "weight_percent" else "X ="

    def _apply_unit_range(self):
        if self._comp_unit == "weight_percent":
            self.composition_spin.setRange(0.0, 100.0)
            self.composition_spin.setDecimals(2)
            self.composition_spin.setSingleStep(0.5)
            self.composition_spin.setValue(5.0)
        else:
            self.composition_spin.setRange(0.0, 1.0)
            self.composition_spin.setDecimals(4)
            self.composition_spin.setSingleStep(0.01)
            self.composition_spin.setValue(0.05)

    def set_comp_unit(self, unit: str):
        """Switch between 'mole_fraction' and 'weight_percent'."""
        if unit == self._comp_unit:
            return
        self._comp_unit = unit
        self.unit_label.setText(self._label_text())
        self._apply_unit_range()


# ---------------------------------------------------------------------------
# Dark-themed matplotlib helpers
# ---------------------------------------------------------------------------

def _style_axes(ax, xlabel: str, ylabel: str, title: str = ""):
    """Apply the application's dark theme to a matplotlib Axes."""
    ax.set_facecolor("#1e1e2e")
    ax.set_xlabel(xlabel, color="white", fontsize=10)
    ax.set_ylabel(ylabel, color="white", fontsize=10)
    if title:
        ax.set_title(title, color="white", fontsize=12, pad=10)
    ax.tick_params(colors="white", labelsize=9)
    for spine in ax.spines.values():
        spine.set_color("#555555")
    ax.grid(True, color="#555555", alpha=0.3, linestyle="--")


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

class ScheilPanel(QWidget):
    """Panel for Scheil-Gulliver solidification simulation."""

    calculation_done = pyqtSignal(list, dict, str)

    def __init__(self):
        super().__init__()
        self.db: Database | None = None
        self.elements: list[str] = []
        self.phases_list: list[str] = []
        self.comp_rows: list[_CompositionRow] = []
        self._worker: ScheilWorker | None = None
        self._last_result: dict | None = None
        self._temp_unit: str = "K"
        self._comp_unit: str = "mole_fraction"
        self._setup_ui()

    # ------------------------------------------------------------------ UI
    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        title = QLabel("Scheil Solidification")
        title.setObjectName("heading")
        layout.addWidget(title)

        # --- Educational info panel ---
        info_data = TAB_INFO.get("scheil", {})
        self.info_group = QGroupBox("What Is This?")
        info_layout = QVBoxLayout()
        simple = info_data.get("simple", "")
        analogy = info_data.get("analogy", "")
        tips = info_data.get("tips", [])
        tips_html = "".join(f"<li>{t}</li>" for t in tips)
        self._info_text = QLabel()
        self._info_text.setWordWrap(True)
        self._info_text.setTextFormat(Qt.TextFormat.RichText)
        self._info_text.setStyleSheet(
            "color: #ccccdd; font-size: 13px; padding: 10px 14px;"
        )
        self._info_text.setText(
            f'<p style="color: #e0e0e0;">{simple}</p>'
            f'<p style="color: #81C784;"><b>Think of it like:</b> {analogy}</p>'
            f'<p style="color: #FFB74D;"><b>Tips:</b></p><ul>{tips_html}</ul>'
        )
        self._info_text.setVisible(True)
        info_layout.addWidget(self._info_text)
        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)

        # --- Scheil availability warning ---
        if not _SCHEIL_AVAILABLE:
            warn = QLabel(
                "The scheil package is not installed.  Install it with:\n"
                "    pip install scheil"
            )
            warn.setStyleSheet(
                "color: #E57373; font-weight: bold; padding: 8px; "
                "background: rgba(229,115,115,0.1); border-radius: 6px;"
            )
            warn.setWordWrap(True)
            layout.addWidget(warn)

        # --- Alloy Composition group ---
        self.comp_group = QGroupBox("Alloy Composition (mole fractions)")
        self.comp_layout = QVBoxLayout()

        comp_btn_layout = QHBoxLayout()
        self.add_comp_btn = QPushButton("+ Add Element")
        self.add_comp_btn.setToolTip(
            "Add an alloying element row. The first unused element is "
            "selected automatically."
        )
        self.add_comp_btn.clicked.connect(self._add_composition_row)
        self.add_comp_btn.setEnabled(False)
        comp_btn_layout.addWidget(self.add_comp_btn)

        self.remove_comp_btn = QPushButton("- Remove Last")
        self.remove_comp_btn.setToolTip("Remove the last composition row.")
        self.remove_comp_btn.clicked.connect(self._remove_composition_row)
        self.remove_comp_btn.setEnabled(False)
        comp_btn_layout.addWidget(self.remove_comp_btn)

        comp_btn_layout.addStretch()
        self.comp_layout.addLayout(comp_btn_layout)

        self.comp_rows_container = QVBoxLayout()
        self.comp_layout.addLayout(self.comp_rows_container)

        self.balance_label = QLabel("")
        self.balance_label.setToolTip(
            "Live composition balance. Shows each element and the total. "
            "Turns red if the total exceeds the allowed maximum."
        )
        self.balance_label.setStyleSheet("padding: 4px; font-weight: bold;")
        self.comp_layout.addWidget(self.balance_label)

        self.comp_group.setLayout(self.comp_layout)
        layout.addWidget(self.comp_group)

        # --- Scheil Parameters group ---
        param_group = QGroupBox("Scheil Parameters")
        param_layout = QHBoxLayout()

        self.start_temp_label = QLabel("Start Temperature (K):")
        param_layout.addWidget(self.start_temp_label)
        self.start_temp_spin = QDoubleSpinBox()
        self.start_temp_spin.setRange(500, 5000)
        self.start_temp_spin.setValue(1600)
        self.start_temp_spin.setSingleStep(50)
        self.start_temp_spin.setDecimals(1)
        self.start_temp_spin.setToolTip(TOOLTIPS["scheil_start_temp"])
        param_layout.addWidget(self.start_temp_spin)

        param_layout.addWidget(QLabel("Step Size (K):"))
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.1, 10.0)
        self.step_spin.setValue(1.0)
        self.step_spin.setSingleStep(0.5)
        self.step_spin.setDecimals(1)
        self.step_spin.setToolTip(TOOLTIPS["scheil_step_size"])
        param_layout.addWidget(self.step_spin)

        param_layout.addStretch()
        param_group.setLayout(param_layout)
        layout.addWidget(param_group)

        # --- Buttons ---
        btn_layout = QHBoxLayout()

        self.calc_btn = QPushButton("Calculate Scheil")
        self.calc_btn.setObjectName("primary")
        self.calc_btn.setEnabled(False)
        self.calc_btn.setToolTip(
            "Run the Scheil-Gulliver solidification simulation with the "
            "specified alloy composition and parameters."
        )
        self.calc_btn.clicked.connect(self._calculate)
        btn_layout.addWidget(self.calc_btn)

        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.setObjectName("success")
        self.export_csv_btn.setEnabled(False)
        self.export_csv_btn.setToolTip(
            "Save the Scheil simulation data as a CSV file with metadata."
        )
        self.export_csv_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(self.export_csv_btn)

        self.export_png_btn = QPushButton("Export PNG")
        self.export_png_btn.setObjectName("success")
        self.export_png_btn.setEnabled(False)
        self.export_png_btn.setToolTip(
            "Save the currently visible plot as a PNG image."
        )
        self.export_png_btn.clicked.connect(self._export_png)
        btn_layout.addWidget(self.export_png_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # --- Progress ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)

        # --- Summary ---
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(
            "background-color: rgba(255,255,255,0.05); "
            "border-radius: 6px; padding: 8px; margin-top: 4px;"
        )
        self.summary_label.setVisible(False)
        layout.addWidget(self.summary_label)

        # --- Result tabs ---
        self.result_tabs = QTabWidget()

        # Tab 1: Solidification Curve
        self.solidification_canvas = LazyCanvas(figsize=(8, 5), dpi=100)
        self.solidification_canvas.setMinimumHeight(350)
        self.result_tabs.addTab(self.solidification_canvas, "Solidification Curve")

        # Tab 2: Phase Sequence (table + stacked area chart)
        phase_seq_widget = QWidget()
        phase_seq_layout = QVBoxLayout(phase_seq_widget)

        self.phase_table = QTableWidget()
        self.phase_table.setMinimumHeight(120)
        self.phase_table.setMaximumHeight(200)
        self.phase_table.setToolTip(
            "Phases that form during solidification, in order of appearance."
        )
        phase_seq_layout.addWidget(self.phase_table)

        self.phase_seq_canvas = LazyCanvas(figsize=(8, 4), dpi=100)
        self.phase_seq_canvas.setMinimumHeight(250)
        phase_seq_layout.addWidget(self.phase_seq_canvas, stretch=1)

        self.result_tabs.addTab(phase_seq_widget, "Phase Sequence")

        # Tab 3: Microsegregation
        self.microseg_canvas = LazyCanvas(figsize=(8, 5), dpi=100)
        self.microseg_canvas.setMinimumHeight(350)
        self.result_tabs.addTab(self.microseg_canvas, "Microsegregation")

        layout.addWidget(self.result_tabs, stretch=1)

        scroll.setWidget(container)
        outer.addWidget(scroll)

    # -------------------------------------------------------- unit setters

    def set_temp_unit(self, unit: str):
        """Switch the start temperature input between 'K' and 'C'."""
        if unit not in ("K", "C"):
            return
        if unit == self._temp_unit:
            return

        old_val = self.start_temp_spin.value()
        self._temp_unit = unit

        self.start_temp_spin.blockSignals(True)
        if unit == "C":
            self.start_temp_label.setText("Start Temperature (\u00b0C):")
            self.start_temp_spin.setRange(227, 4727)
            self.start_temp_spin.setValue(k_to_c(old_val))
            self.start_temp_spin.setToolTip(TOOLTIPS["scheil_start_temp_c"])
        else:
            self.start_temp_label.setText("Start Temperature (K):")
            self.start_temp_spin.setRange(500, 5000)
            self.start_temp_spin.setValue(c_to_k(old_val))
            self.start_temp_spin.setToolTip(TOOLTIPS["scheil_start_temp"])
        self.start_temp_spin.blockSignals(False)

    def set_comp_unit(self, unit: str):
        """Switch composition between 'mole_fraction' and 'weight_percent'."""
        if unit not in ("mole_fraction", "weight_percent"):
            return
        if unit == self._comp_unit:
            return

        old_unit = self._comp_unit
        self._comp_unit = unit

        if unit == "weight_percent":
            self.comp_group.setTitle("Alloy Composition (weight percent)")
        else:
            self.comp_group.setTitle("Alloy Composition (mole fractions)")

        if self.comp_rows:
            # Collect current values
            current_vals: dict[str, float] = {}
            for row in self.comp_rows:
                el = row.element_combo.currentText()
                current_vals[el] = row.composition_spin.value()

            # Determine balance element
            used = set(current_vals.keys())
            balance_el = None
            for el in self.elements:
                if el not in used:
                    balance_el = el
                    break

            if balance_el is not None:
                if old_unit == "mole_fraction":
                    balance_val = 1.0 - sum(current_vals.values())
                else:
                    balance_val = 100.0 - sum(current_vals.values())
                full_comp = dict(current_vals)
                full_comp[balance_el] = max(0.0, balance_val)

                if old_unit == "mole_fraction" and unit == "weight_percent":
                    converted = mole_to_weight(full_comp)
                else:
                    converted = weight_to_mole(full_comp)

                for row in self.comp_rows:
                    el = row.element_combo.currentText()
                    row.composition_spin.blockSignals(True)
                    row.set_comp_unit(unit)
                    if el in converted:
                        row.composition_spin.setValue(converted[el])
                    row.composition_spin.blockSignals(False)
            else:
                for row in self.comp_rows:
                    row.set_comp_unit(unit)
        else:
            for row in self.comp_rows:
                row.set_comp_unit(unit)

        self._update_balance()

    # -------------------------------------------------------- database load

    def _toggle_info(self, checked=None):
        """Toggle the educational info panel visibility."""
        if checked is not None:
            self._info_visible = checked
        else:
            self._info_visible = not self._info_visible
        # Defer visibility change to avoid Qt layout re-entrancy segfault
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._apply_info_visibility)

    def _apply_info_visibility(self):
        """Apply the info panel visibility (deferred from toggle to avoid segfault)."""
        self._info_text.setVisible(self._info_visible)
        if self._info_visible:
            self.info_group.setTitle("What Is This? (click to collapse)")
        else:
            self.info_group.setTitle("What Is This? (click to expand)")

    def update_database(self, db: Database, elements: list[str],
                        phases: list[str]):
        self.db = db
        self.elements = elements
        self.phases_list = phases

        for row in self.comp_rows:
            row.deleteLater()
        self.comp_rows.clear()

        self.add_comp_btn.setEnabled(True)
        self.calc_btn.setEnabled(len(elements) >= 2 and _SCHEIL_AVAILABLE)

        if len(elements) >= 2:
            self._add_composition_row()

        self._update_balance()

    # ----------------------------------------------------- composition rows

    def _add_composition_row(self):
        if not self.elements:
            return
        row = _CompositionRow(self.elements, comp_unit=self._comp_unit)
        used = {r.element_combo.currentText() for r in self.comp_rows}
        for el in self.elements:
            if el not in used:
                row.element_combo.setCurrentText(el)
                break
        row.composition_spin.valueChanged.connect(self._update_balance)
        row.element_combo.currentTextChanged.connect(self._update_balance)
        row.element_combo.currentTextChanged.connect(
            self._check_duplicate_elements
        )
        self.comp_rows.append(row)
        self.comp_rows_container.addWidget(row)
        self.remove_comp_btn.setEnabled(True)
        self._update_balance()

    def _remove_composition_row(self):
        if self.comp_rows:
            row = self.comp_rows.pop()
            row.deleteLater()
        self.remove_comp_btn.setEnabled(len(self.comp_rows) > 0)
        self._update_balance()

    # --------------------------------------------------- balance indicator

    def _update_balance(self):
        if not self.comp_rows:
            self.balance_label.setText("")
            return

        is_wt = self._comp_unit == "weight_percent"
        limit = 100.0 if is_wt else 1.0
        unit_str = "%" if is_wt else ""
        fmt = ".2f" if is_wt else ".4f"

        parts: list[str] = []
        total = 0.0
        used_elements: set[str] = set()

        for row in self.comp_rows:
            el = row.element_combo.currentText()
            val = row.composition_spin.value()
            total += val
            used_elements.add(el)
            parts.append(f"{el}: {val:{fmt}}{unit_str}")

        balance_el = None
        for el in self.elements:
            if el not in used_elements:
                balance_el = el
                break

        if balance_el is not None:
            parts.insert(0, f"{balance_el}: balance")

        total_display = f"{total:{fmt}}{unit_str}"
        text = " | ".join(parts) + f" | Total: {total_display}"

        over_limit = total > limit + (0.01 if is_wt else 0.0001)
        if over_limit:
            self.balance_label.setStyleSheet(
                "padding: 4px; font-weight: bold; color: #E57373;"
            )
        else:
            self.balance_label.setStyleSheet(
                "padding: 4px; font-weight: bold; color: #81C784;"
            )
        self.balance_label.setText(text)

    # ------------------------------------------------ duplicate detection

    def _check_duplicate_elements(self):
        element_counts: dict[str, int] = {}
        for row in self.comp_rows:
            el = row.element_combo.currentText()
            element_counts[el] = element_counts.get(el, 0) + 1

        for row in self.comp_rows:
            el = row.element_combo.currentText()
            if element_counts.get(el, 0) > 1:
                row.element_combo.setStyleSheet("border: 2px solid #E57373;")
            else:
                row.element_combo.setStyleSheet("")

    # ---------------------------------------------------------- calculate

    def _get_start_temperature_k(self) -> float:
        """Return the start temperature in Kelvin."""
        val = self.start_temp_spin.value()
        if self._temp_unit == "C":
            return c_to_k(val)
        return val

    def _calculate(self):
        if not _SCHEIL_AVAILABLE:
            QMessageBox.warning(
                self, "Missing Package", _SCHEIL_IMPORT_ERROR
            )
            return

        if not self.db or not self.comp_rows:
            QMessageBox.warning(
                self, "Missing Input",
                "Please load a database and add at least one element "
                "composition before calculating."
            )
            return

        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(
                self, "Please Wait",
                "A Scheil simulation is already in progress. "
                "Please wait for it to finish."
            )
            return

        # Collect compositions
        compositions: dict[str, float] = {}
        all_elements: set[str] = set()
        duplicates: set[str] = set()

        for row in self.comp_rows:
            el = row.element_combo.currentText()
            val = row.composition_spin.value()
            if el in compositions:
                duplicates.add(el)
            compositions[el] = val
            all_elements.add(el)

        if duplicates:
            QMessageBox.warning(
                self, "Duplicate Elements",
                f"The following element(s) appear more than once: "
                f"{', '.join(sorted(duplicates))}. "
                f"Please ensure each element is used only once."
            )
            return

        # Need at least 2 elements (1 specified + 1 balance)
        balance_el = None
        for el in self.elements:
            if el not in all_elements:
                balance_el = el
                break

        if balance_el is None and len(all_elements) < 2:
            QMessageBox.warning(
                self, "Not Enough Elements",
                "Scheil simulation requires at least 2 elements. "
                "Please load a database with at least 2 elements and "
                "add at least one composition row."
            )
            return

        # Convert weight percent to mole fraction if needed
        if self._comp_unit == "weight_percent":
            total_wt = sum(compositions.values())
            if total_wt > 100.01:
                QMessageBox.warning(
                    self, "Composition Too High",
                    f"The total weight percent ({total_wt:.2f}%) exceeds "
                    f"100%. Please reduce one or more element values."
                )
                return
            if balance_el:
                full_wt = dict(compositions)
                full_wt[balance_el] = 100.0 - total_wt
                mole_frac = weight_to_mole(full_wt)
                compositions = {
                    el: mole_frac[el] for el in compositions
                }
        else:
            total = sum(compositions.values())
            if total > 1.0001:
                QMessageBox.warning(
                    self, "Composition Too High",
                    f"The total mole fraction ({total:.4f}) exceeds 1.0. "
                    f"Please reduce one or more element values."
                )
                return

        # Build element list including balance
        elements_list = list(all_elements)
        if balance_el and balance_el not in elements_list:
            elements_list.append(balance_el)

        start_temp = self._get_start_temperature_k()
        step_size = self.step_spin.value()

        if start_temp <= 0:
            QMessageBox.warning(
                self, "Invalid Temperature",
                "Start temperature must be greater than 0 K."
            )
            return

        # Build pycalphad conditions
        from pycalphad import variables as v

        comps = sorted([el.upper() for el in elements_list]) + ["VA"]
        phases = self.phases_list if self.phases_list else list(self.db.phases.keys())

        conds = {v.P: 101325, v.N: 1}
        for el, x in compositions.items():
            conds[v.X(el.upper())] = x

        # Start calculation
        self.calc_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText(
            "Running Scheil simulation... This may take a while."
        )
        self.status_label.setStyleSheet("color: #FFB74D;")
        self.summary_label.setVisible(False)

        self._worker = ScheilWorker(
            self.db, comps, phases, conds,
            start_temperature=start_temp,
            step_temperature=step_size,
        )
        self._worker.finished.connect(self._on_calculated)
        self._worker.start()

    # ------------------------------------------------------- results

    def _on_calculated(self, result: dict):
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(True)

        if not result.get("success", False):
            raw_error = result.get("error", "Unknown error")
            friendly = _friendly_error(raw_error)
            self.status_label.setText("Simulation failed")
            self.status_label.setStyleSheet("color: #E57373;")
            QMessageBox.warning(
                self, "Scheil Simulation Did Not Succeed",
                f"{friendly}\n\n(Technical details below)\n\n"
                f"{raw_error[-400:]}"
            )
            return

        self._last_result = result

        temperatures = result["temperatures"]
        fraction_solid = result["fraction_solid"]
        phase_amounts = result.get("phase_amounts", {})
        cum_phase_amounts = result.get("cum_phase_amounts", {})
        liquid_comp = result.get("liquid_comp", {})

        # --- Plot solidification curve ---
        self._plot_solidification_curve(temperatures, fraction_solid)

        # --- Fill phase sequence table and stacked area ---
        self._fill_phase_sequence(temperatures, phase_amounts, cum_phase_amounts)

        # --- Plot microsegregation ---
        self._plot_microsegregation(fraction_solid, liquid_comp)

        # --- Summary ---
        self._show_summary(temperatures, fraction_solid, phase_amounts)

        self.export_csv_btn.setEnabled(True)
        self.export_png_btn.setEnabled(True)

        n_phases = len(phase_amounts)
        self.status_label.setText(
            f"Scheil simulation complete: {n_phases} phase(s) formed "
            f"over {len(temperatures)} steps"
        )
        self.status_label.setStyleSheet("color: #81C784;")

        # Emit signal for history
        elem_list = [r.element_combo.currentText() for r in self.comp_rows]
        cond = {
            "start_T": temperatures[0] if temperatures else 0,
            "end_T": temperatures[-1] if temperatures else 0,
            "steps": len(temperatures),
        }
        summary_text = self.summary_label.text()
        self.calculation_done.emit(elem_list, cond, summary_text)

    # --------------------------------------------------- plotting

    def _plot_solidification_curve(self, temperatures: list[float],
                                   fraction_solid: list[float]):
        """Plot fraction solid vs temperature."""
        self.solidification_canvas.figure.clear()
        ax = self.solidification_canvas.figure.add_subplot(111)
        _style_axes(ax, "Fraction Solid", "Temperature (K)",
                     "Scheil Solidification Curve")

        ax.plot(fraction_solid, temperatures, color="#4FC3F7", linewidth=2)
        ax.set_xlim(0, 1)

        if temperatures:
            y_min = min(temperatures) - 20
            y_max = max(temperatures) + 20
            ax.set_ylim(y_min, y_max)

        # Secondary Celsius axis on the right
        ax2 = ax.twinx()
        ax2.set_ylabel("Temperature (\u00b0C)", color="white", fontsize=10)
        ax2.tick_params(colors="white", labelsize=9)
        for spine in ax2.spines.values():
            spine.set_color("#555555")
        if temperatures:
            ax2.set_ylim(k_to_c(y_min), k_to_c(y_max))

        self.solidification_canvas.figure.tight_layout()
        self.solidification_canvas.draw()

    def _fill_phase_sequence(self, temperatures: list[float],
                             phase_amounts: dict[str, list[float]],
                             cum_phase_amounts: dict[str, list[float]]):
        """Fill the phase sequence table and draw the stacked area chart."""
        # --- Table ---
        # Determine phase appearance order and max fractions
        phase_info: list[dict] = []
        for phase_name, amounts in phase_amounts.items():
            if not amounts or max(amounts) < 1e-6:
                continue
            # Find first temperature where phase appears
            first_idx = None
            for i, amt in enumerate(amounts):
                if amt > 1e-6:
                    first_idx = i
                    break
            appears_at = temperatures[first_idx] if first_idx is not None else 0.0
            max_frac = max(amounts)
            phase_info.append({
                "phase": phase_name,
                "appears_at": appears_at,
                "max_fraction": max_frac,
            })

        phase_info.sort(key=lambda p: p["appears_at"], reverse=True)

        columns = ["Phase", "Appears At (K)", "Max Fraction", "Description"]
        self.phase_table.setRowCount(len(phase_info))
        self.phase_table.setColumnCount(len(columns))
        self.phase_table.setHorizontalHeaderLabels(columns)

        for i, info in enumerate(phase_info):
            self.phase_table.setItem(
                i, 0, QTableWidgetItem(info["phase"])
            )
            self.phase_table.setItem(
                i, 1, QTableWidgetItem(f"{info['appears_at']:.1f}")
            )
            self.phase_table.setItem(
                i, 2, QTableWidgetItem(f"{info['max_fraction']:.4f}")
            )
            desc = self._phase_description(info["phase"])
            self.phase_table.setItem(i, 3, QTableWidgetItem(desc))

        # Smart column sizing
        n_cols = self.phase_table.columnCount()
        if n_cols <= 8:
            self.phase_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )
        else:
            self.phase_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Interactive
            )
            self.phase_table.horizontalHeader().setDefaultSectionSize(90)

        # --- Stacked area chart ---
        self.phase_seq_canvas.figure.clear()
        ax = self.phase_seq_canvas.figure.add_subplot(111)
        _style_axes(ax, "Temperature (K)", "Phase Fraction",
                     "Phase Fractions During Solidification")

        # Use cumulative amounts if available, otherwise incremental
        plot_data = cum_phase_amounts if cum_phase_amounts else phase_amounts
        valid_phases = [
            p for p in plot_data
            if plot_data[p] and max(plot_data[p]) > 1e-6
        ]

        if valid_phases and temperatures:
            # Ensure all arrays match the temperature length
            min_len = min(len(temperatures),
                          *(len(plot_data[p]) for p in valid_phases))
            t_arr = temperatures[:min_len]
            colors = [PHASE_COLORS[i % len(PHASE_COLORS)]
                      for i in range(len(valid_phases))]
            y_arrays = [plot_data[p][:min_len] for p in valid_phases]

            ax.stackplot(t_arr, *y_arrays, labels=valid_phases,
                         colors=colors, alpha=0.85)
            handles, labels = ax.get_legend_handles_labels()
            if len(handles) <= 8:
                ax.legend(fontsize=8, loc="best", facecolor="#2d2d3e", edgecolor="#555555", labelcolor="white")
            else:
                ax.legend(fontsize=7, loc="center left", bbox_to_anchor=(1.02, 0.5),
                          facecolor="#2d2d3e", edgecolor="#555555", labelcolor="white", borderaxespad=0)
            ax.set_xlim(max(t_arr), min(t_arr))  # High to low temperature

        self.phase_seq_canvas.figure.tight_layout()
        self.phase_seq_canvas.draw()

    def _plot_microsegregation(self, fraction_solid: list[float],
                               liquid_comp: dict[str, list[float]]):
        """Plot liquid composition vs fraction solid."""
        self.microseg_canvas.figure.clear()
        ax = self.microseg_canvas.figure.add_subplot(111)
        _style_axes(ax, "Fraction Solid", "Composition in Liquid",
                     "Microsegregation (Liquid Composition)")

        if liquid_comp and fraction_solid:
            for i, (el, comps) in enumerate(sorted(liquid_comp.items())):
                if el.upper() == "VA":
                    continue
                min_len = min(len(fraction_solid), len(comps))
                color = PHASE_COLORS[i % len(PHASE_COLORS)]
                ax.plot(
                    fraction_solid[:min_len], comps[:min_len],
                    color=color, linewidth=1.8, label=el,
                )
            ax.set_xlim(0, 1)
            handles, labels = ax.get_legend_handles_labels()
            if len(handles) <= 8:
                ax.legend(fontsize=8, loc="best", facecolor="#2d2d3e", edgecolor="#555555", labelcolor="white")
            else:
                ax.legend(fontsize=7, loc="center left", bbox_to_anchor=(1.02, 0.5),
                          facecolor="#2d2d3e", edgecolor="#555555", labelcolor="white", borderaxespad=0)

        self.microseg_canvas.figure.tight_layout()
        self.microseg_canvas.draw()

    @staticmethod
    def _phase_description(phase_name: str) -> str:
        """Return a short human-readable description for common phases."""
        # Try to use the project's translator if available
        try:
            from core.presets import translate_phase_name
            desc = translate_phase_name(phase_name)
            if desc and desc != phase_name:
                return desc
        except ImportError:
            pass

        name = phase_name.upper()
        descriptions = {
            "LIQUID": "Liquid phase",
            "FCC_A1": "Face-centered cubic (austenite in steels, Al matrix)",
            "BCC_A2": "Body-centered cubic (ferrite in steels)",
            "HCP_A3": "Hexagonal close-packed",
            "CEMENTITE": "Iron carbide (Fe3C)",
            "M23C6": "Chromium carbide M23C6",
            "M7C3": "Chromium carbide M7C3",
            "SIGMA": "Sigma intermetallic phase",
            "LAVES": "Laves intermetallic phase",
            "MU_PHASE": "Mu intermetallic phase",
        }
        return descriptions.get(name, "")

    # ------------------------------------------------------- summary

    def _show_summary(self, temperatures: list[float],
                      fraction_solid: list[float],
                      phase_amounts: dict[str, list[float]]):
        """Build and display a plain-English summary."""
        if not temperatures:
            return

        start_t = temperatures[0]
        end_t = temperatures[-1]

        # Count phases that actually formed
        active_phases = [
            p for p, a in phase_amounts.items()
            if a and max(a) > 1e-6
        ]
        n_phases = len(active_phases)

        # Estimate eutectic fraction
        # The eutectic fraction is the remaining liquid at the eutectic point
        # (the last significant fraction solid jump or the final fraction)
        eutectic_frac = 0.0
        if fraction_solid:
            final_solid = fraction_solid[-1]
            eutectic_frac = 1.0 - final_solid

        summary = (
            f"Scheil solidification: Solidification begins at "
            f"{start_t:.0f} K ({k_to_c(start_t):.0f} \u00b0C) and ends at "
            f"{end_t:.0f} K ({k_to_c(end_t):.0f} \u00b0C). "
            f"{n_phases} phase{'s' if n_phases != 1 else ''} "
            f"form{'s' if n_phases == 1 else ''} during solidification. "
            f"Eutectic fraction: {eutectic_frac:.1%}."
        )
        self.summary_label.setText(summary)
        self.summary_label.setVisible(True)

    # -------------------------------------------------------- export CSV

    def _export_csv(self):
        if not self._last_result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Scheil Data", "scheil.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return

        result = self._last_result
        temperatures = result["temperatures"]
        fraction_solid = result["fraction_solid"]
        phase_amounts = result.get("phase_amounts", {})

        try:
            with open(path, "w", newline="") as f:
                # Metadata header
                f.write(f"# Scheil-Gulliver Solidification Simulation\n")
                f.write(
                    f"# Exported: "
                    f"{datetime.datetime.now().isoformat(timespec='seconds')}\n"
                )
                f.write(
                    f"# Start Temperature: "
                    f"{format_temp(self._get_start_temperature_k())}\n"
                )
                f.write(f"# Step Size: {self.step_spin.value():.1f} K\n")

                comp_parts = []
                for row in self.comp_rows:
                    el = row.element_combo.currentText()
                    val = row.composition_spin.value()
                    if self._comp_unit == "weight_percent":
                        comp_parts.append(f"{el}={val:.2f} wt%")
                    else:
                        comp_parts.append(f"{el}={val:.4f}")
                if comp_parts:
                    f.write(f"# Composition: {', '.join(comp_parts)}\n")

                f.write(f"# Steps: {len(temperatures)}\n")
                f.write("#\n")

                # Build column headers
                phase_names = sorted(phase_amounts.keys())
                headers = ["Temperature_K", "Fraction_Solid"]
                headers.extend(
                    f"Phase_{p}" for p in phase_names
                )
                f.write(",".join(headers) + "\n")

                # Data rows
                n = len(temperatures)
                for i in range(n):
                    row_vals = [
                        f"{temperatures[i]:.2f}",
                        f"{fraction_solid[i]:.6f}",
                    ]
                    for p in phase_names:
                        amounts = phase_amounts[p]
                        val = amounts[i] if i < len(amounts) else 0.0
                        row_vals.append(f"{val:.6f}")
                    f.write(",".join(row_vals) + "\n")

            self.status_label.setText(f"Exported to {path}")
        except Exception as exc:
            QMessageBox.critical(
                self, "Export Failed",
                f"Could not write CSV file:\n\n{exc}"
            )

    # -------------------------------------------------------- export PNG

    def _export_png(self):
        # Determine which figure is currently visible
        current_idx = self.result_tabs.currentIndex()
        fig_map = {
            0: self.solidification_canvas.figure,
            1: self.phase_seq_canvas.figure,
            2: self.microseg_canvas.figure,
        }
        fig = fig_map.get(current_idx)
        if fig is None:
            return

        tab_names = {
            0: "scheil_solidification",
            1: "scheil_phases",
            2: "scheil_microsegregation",
        }
        default_name = f"{tab_names.get(current_idx, 'scheil')}.png"

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Scheil Plot", default_name,
            "PNG Files (*.png);;All Files (*)"
        )
        if not path:
            return

        # Add a subtitle with conditions for export
        comp_parts = []
        for row in self.comp_rows:
            el = row.element_combo.currentText()
            val = row.composition_spin.value()
            if self._comp_unit == "weight_percent":
                comp_parts.append(f"{el}={val:.2f} wt%")
            else:
                comp_parts.append(f"{el}={val:.4f}")
        subtitle = f"Start T: {format_temp(self._get_start_temperature_k())}"
        if comp_parts:
            subtitle += "  |  " + ", ".join(comp_parts)

        annotation = fig.text(
            0.01, 0.01, subtitle,
            fontsize=7, color="#888888",
            transform=fig.transFigure,
            ha="left", va="bottom",
        )

        try:
            fig.savefig(
                path, dpi=150, facecolor="#1e1e2e",
                bbox_inches="tight",
            )
            self.status_label.setText(f"Exported to {path}")
        except Exception as exc:
            QMessageBox.critical(
                self, "Export Failed",
                f"Could not save PNG file:\n\n{exc}"
            )
        finally:
            annotation.remove()
            # Redraw the appropriate canvas
            canvas_map = {
                0: self.solidification_canvas,
                1: self.phase_seq_canvas,
                2: self.microseg_canvas,
            }
            canvas = canvas_map.get(current_idx)
            if canvas:
                canvas.draw()
