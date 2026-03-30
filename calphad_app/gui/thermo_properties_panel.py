"""Thermodynamic properties panel for computing G, H, S, Cp, and chemical
potentials as a function of temperature using pycalphad equilibrium."""

from __future__ import annotations

import datetime
import re
import traceback
from typing import Any

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QTabWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)
from gui.lazy_canvas import LazyCanvas
from pycalphad import Database, equilibrium, variables as v

from core.units import k_to_c, c_to_k, format_temp, mole_to_weight, weight_to_mole
from gui.info_content import TAB_INFO


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHASE_COLORS: list[str] = [
    "#4FC3F7", "#81C784", "#FFB74D", "#E57373", "#BA68C8",
    "#4DB6AC", "#FFD54F", "#7986CB", "#A1887F", "#90A4AE",
    "#F06292", "#AED581", "#64B5F6", "#FF8A65", "#CE93D8",
]

PROPERTY_COLORS: dict[str, str] = {
    "GM": "#4FC3F7",
    "HM": "#81C784",
    "SM": "#FFB74D",
    "CPM": "#E57373",
}

PROPERTY_LABELS: dict[str, str] = {
    "GM": "Gibbs Energy (J/mol)",
    "HM": "Enthalpy (J/mol)",
    "SM": "Entropy (J/mol/K)",
    "CPM": "Heat Capacity (J/mol/K)",
}

PROPERTY_SHORT: dict[str, str] = {
    "GM": "G",
    "HM": "H",
    "SM": "S",
    "CPM": "Cp",
}


# ---------------------------------------------------------------------------
# Friendly error messages
# ---------------------------------------------------------------------------

_FRIENDLY_ERRORS: list[tuple[str, str]] = [
    ("Composition.*out of range",
     "One of your composition values is outside the valid range for this "
     "thermodynamic database. Try reducing the amount of the alloying element."),
    ("No solution found",
     "The solver could not find a stable equilibrium at one or more "
     "temperatures. Try adjusting the temperature range or composition."),
    ("singular matrix",
     "The calculation hit a numerical singularity. This sometimes happens "
     "near a phase boundary. Try a slightly different temperature range."),
    ("Database",
     "There may be a problem with the thermodynamic database for this element "
     "combination. Make sure all selected elements are covered by the loaded "
     "database."),
]


def _friendly_error(raw: str) -> str:
    """Return a user-friendly error message based on the raw traceback."""
    for pattern, friendly in _FRIENDLY_ERRORS:
        if re.search(pattern, raw, re.IGNORECASE):
            return friendly
    return (
        "The thermodynamic property calculation did not succeed. This can "
        "happen when the database does not cover the requested conditions.\n\n"
        "Suggestions:\n"
        "  - Check that every element is present in the database.\n"
        "  - Try a narrower temperature range or larger step size.\n"
        "  - Reduce extreme composition values."
    )


# ---------------------------------------------------------------------------
# Composition row widget
# ---------------------------------------------------------------------------

class CompositionRow(QWidget):
    """A single element-composition input row."""

    def __init__(self, elements: list[str], comp_unit: str = "mole_fraction",
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._comp_unit = comp_unit
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.element_combo = QComboBox()
        self.element_combo.addItems(elements)
        self.element_combo.setToolTip(
            "Select the alloying element whose composition you want to set. "
            "The balance element is determined automatically."
        )
        layout.addWidget(self.element_combo)

        self.unit_label = QLabel(self._label_text())
        layout.addWidget(self.unit_label)

        self.composition_spin = QDoubleSpinBox()
        self._apply_unit_range()
        self.composition_spin.setToolTip(
            "Composition of this element. The balance element makes up the "
            "remainder so that all fractions sum to 1 (or all wt% sum to 100)."
        )
        layout.addWidget(self.composition_spin)

    def _label_text(self) -> str:
        return "wt% =" if self._comp_unit == "weight_percent" else "X ="

    def _apply_unit_range(self) -> None:
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

    def set_comp_unit(self, unit: str) -> None:
        """Switch between 'mole_fraction' and 'weight_percent'."""
        if unit == self._comp_unit:
            return
        self._comp_unit = unit
        self.unit_label.setText(self._label_text())
        self._apply_unit_range()


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

class ThermoPropertiesWorker(QThread):
    """Background worker that sweeps temperature and extracts thermo props."""

    finished = pyqtSignal(object)   # dict with results or error
    progress = pyqtSignal(int)      # percent complete

    def __init__(
        self,
        db: Database,
        elements: list[str],
        compositions: dict[str, float],
        t_min: float,
        t_max: float,
        t_step: float,
        pressure: float,
        requested_props: list[str],
        calc_mu: bool,
    ):
        super().__init__()
        self.db = db
        self.elements = elements
        self.compositions = compositions
        self.t_min = t_min
        self.t_max = t_max
        self.t_step = t_step
        self.pressure = pressure
        self.requested_props = requested_props
        self.calc_mu = calc_mu

    def run(self) -> None:
        try:
            result = self._compute()
            self.finished.emit(result)
        except Exception:
            self.finished.emit({"error": traceback.format_exc()})

    def _compute(self) -> dict[str, Any]:
        db = self.db
        comps = sorted([e.upper() for e in self.elements]) + ["VA"]
        phases = list(db.phases.keys())

        temps = np.arange(self.t_min, self.t_max + self.t_step / 2, self.t_step)
        n_temps = len(temps)

        # We always compute GM; HM and SM are derived when needed.
        need_gm = True
        need_hm = ("HM" in self.requested_props or "CPM" in self.requested_props)
        need_sm = ("SM" in self.requested_props or need_hm)

        gm_values: list[float] = []
        sm_values: list[float] = []
        hm_values: list[float] = []
        mu_results: dict[str, list[float]] = {
            el: [] for el in sorted([e.upper() for e in self.elements])
        }

        sorted_elements = sorted([e.upper() for e in self.elements])

        for idx, temp in enumerate(temps):
            conds: dict = {v.T: float(temp), v.P: self.pressure, v.N: 1}
            for el, x in self.compositions.items():
                conds[v.X(el.upper())] = x

            try:
                eq = equilibrium(db, comps, phases, conds)

                # Extract Gibbs energy
                gm_val = float(eq.GM.values.squeeze())
                gm_values.append(gm_val)

                # Extract entropy: try SM attribute, fall back to NaN
                sm_val = float("nan")
                if need_sm:
                    if hasattr(eq, "SM") and eq.SM.values.size > 0:
                        sm_val = float(eq.SM.values.squeeze())
                sm_values.append(sm_val)

                # Enthalpy: try HM attribute, fall back to H = G + T*S
                hm_val = float("nan")
                if need_hm:
                    if hasattr(eq, "HM") and eq.HM.values.size > 0:
                        hm_val = float(eq.HM.values.squeeze())
                    elif not np.isnan(sm_val):
                        hm_val = gm_val + float(temp) * sm_val
                hm_values.append(hm_val)

                # Chemical potentials
                if self.calc_mu and eq.MU.values.size > 0:
                    mu_vals = eq.MU.values.squeeze()
                    for i, el in enumerate(sorted_elements):
                        try:
                            mu_results[el].append(float(mu_vals[i]))
                        except (IndexError, TypeError):
                            mu_results[el].append(float("nan"))
                elif self.calc_mu:
                    for el in sorted_elements:
                        mu_results[el].append(float("nan"))

            except Exception:
                gm_values.append(float("nan"))
                sm_values.append(float("nan"))
                hm_values.append(float("nan"))
                if self.calc_mu:
                    for el in sorted_elements:
                        mu_results[el].append(float("nan"))

            # Report progress
            pct = int((idx + 1) / n_temps * 100)
            self.progress.emit(pct)

        # Build results dict for each requested property
        results: dict[str, list[float]] = {}
        if "GM" in self.requested_props:
            results["GM"] = gm_values
        if "SM" in self.requested_props:
            results["SM"] = sm_values
        if "HM" in self.requested_props:
            results["HM"] = hm_values

        # Compute Cp from numerical derivative of H
        if "CPM" in self.requested_props:
            h_arr = np.array(hm_values)
            if len(h_arr) > 1 and not np.all(np.isnan(h_arr)):
                cp = np.gradient(h_arr, temps[:len(h_arr)])
                results["CPM"] = list(cp)
            else:
                results["CPM"] = [float("nan")] * n_temps

        return {
            "temps": list(temps),
            "results": results,
            "mu_results": mu_results if self.calc_mu else {},
            "error": None,
        }


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

class ThermoPropertiesPanel(QWidget):
    """Panel for computing thermodynamic properties vs temperature."""

    calculation_done = pyqtSignal(list, dict, str)

    def __init__(self) -> None:
        super().__init__()
        self.db: Database | None = None
        self.elements: list[str] = []
        self.phases: list[str] = []
        self.comp_rows: list[CompositionRow] = []
        self._worker: ThermoPropertiesWorker | None = None
        self._last_data: dict[str, Any] | None = None
        self._temp_unit: str = "K"
        self._comp_unit: str = "mole_fraction"
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(6)

        title = QLabel("Thermodynamic Properties")
        title.setObjectName("heading")
        layout.addWidget(title)

        # --- Educational info panel ---
        info_data = TAB_INFO.get("thermo_props", {})
        self.info_group = QGroupBox("What Is This? (click to expand)")
        self.info_group.setCheckable(True)
        self.info_group.setChecked(False)
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
        self._info_visible = False
        self._info_text.setVisible(False)
        info_layout.addWidget(self._info_text)
        self.info_group.setLayout(info_layout)
        self.info_group.toggled.connect(self._toggle_info)
        layout.addWidget(self.info_group)

        # --- Alloy Composition group ---
        self.comp_group = QGroupBox("Alloy Composition (mole fractions)")
        self.comp_layout = QVBoxLayout()

        comp_btn_layout = QHBoxLayout()
        self.add_comp_btn = QPushButton("+ Add Element")
        self.add_comp_btn.setToolTip(
            "Add another alloying element row. The first unused element "
            "will be selected automatically."
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
        self.balance_label.setStyleSheet(
            "padding: 4px; font-weight: bold;"
        )
        self.comp_layout.addWidget(self.balance_label)

        self.comp_group.setLayout(self.comp_layout)
        layout.addWidget(self.comp_group)

        # --- Temperature Range group ---
        temp_group = QGroupBox("Temperature Range")
        temp_layout = QHBoxLayout()

        self.t_min_label = QLabel("T min (K):")
        temp_layout.addWidget(self.t_min_label)
        self.t_min_spin = QDoubleSpinBox()
        self.t_min_spin.setRange(100, 5000)
        self.t_min_spin.setValue(300)
        self.t_min_spin.setSingleStep(50)
        self.t_min_spin.setToolTip(
            "Lowest temperature in the sweep (Kelvin). "
            "300 K (room temperature) is typical."
        )
        temp_layout.addWidget(self.t_min_spin)

        self.t_max_label = QLabel("T max (K):")
        temp_layout.addWidget(self.t_max_label)
        self.t_max_spin = QDoubleSpinBox()
        self.t_max_spin.setRange(100, 5000)
        self.t_max_spin.setValue(1200)
        self.t_max_spin.setSingleStep(50)
        self.t_max_spin.setToolTip(
            "Highest temperature in the sweep. Should be above "
            "the liquidus of the alloy."
        )
        temp_layout.addWidget(self.t_max_spin)

        self.t_step_label = QLabel("Step (K):")
        temp_layout.addWidget(self.t_step_label)
        self.t_step_spin = QDoubleSpinBox()
        self.t_step_spin.setRange(1, 200)
        self.t_step_spin.setValue(5)
        self.t_step_spin.setSingleStep(1)
        self.t_step_spin.setToolTip(
            "Temperature increment between calculations. "
            "Smaller = more precise but slower. 5 K is a good balance."
        )
        temp_layout.addWidget(self.t_step_spin)

        temp_layout.addWidget(QLabel("Pressure (Pa):"))
        self.pressure_spin = QDoubleSpinBox()
        self.pressure_spin.setRange(1, 1e9)
        self.pressure_spin.setValue(101325)
        self.pressure_spin.setDecimals(0)
        self.pressure_spin.setSingleStep(1000)
        self.pressure_spin.setToolTip(
            "Total pressure in Pascals. 101325 Pa = 1 atmosphere."
        )
        temp_layout.addWidget(self.pressure_spin)

        temp_group.setLayout(temp_layout)
        layout.addWidget(temp_group)

        # --- Properties to Calculate group ---
        props_group = QGroupBox("Properties to Calculate")
        props_grid = QGridLayout()

        self.cb_gibbs = QCheckBox("Gibbs Energy (G)")
        self.cb_gibbs.setChecked(True)
        self.cb_gibbs.setToolTip("Molar Gibbs energy GM (J/mol)")
        props_grid.addWidget(self.cb_gibbs, 0, 0)

        self.cb_enthalpy = QCheckBox("Enthalpy (H)")
        self.cb_enthalpy.setChecked(True)
        self.cb_enthalpy.setToolTip("Molar enthalpy HM (J/mol)")
        props_grid.addWidget(self.cb_enthalpy, 0, 1)

        self.cb_entropy = QCheckBox("Entropy (S)")
        self.cb_entropy.setChecked(True)
        self.cb_entropy.setToolTip("Molar entropy SM (J/mol/K)")
        props_grid.addWidget(self.cb_entropy, 1, 0)

        self.cb_cp = QCheckBox("Heat Capacity (Cp)")
        self.cb_cp.setChecked(True)
        self.cb_cp.setToolTip(
            "Molar heat capacity CPM (J/mol/K), computed from "
            "numerical derivative of enthalpy."
        )
        props_grid.addWidget(self.cb_cp, 1, 1)

        self.cb_mu = QCheckBox("Chemical Potentials")
        self.cb_mu.setChecked(True)
        self.cb_mu.setToolTip(
            "Chemical potential of each element as a function of temperature."
        )
        props_grid.addWidget(self.cb_mu, 2, 0)

        props_group.setLayout(props_grid)
        layout.addWidget(props_group)

        # --- Buttons ---
        btn_layout = QHBoxLayout()

        self.calc_btn = QPushButton("Calculate Properties")
        self.calc_btn.setObjectName("primary")
        self.calc_btn.setEnabled(False)
        self.calc_btn.setToolTip(
            "Sweep the temperature range and compute the selected "
            "thermodynamic properties at each step."
        )
        self.calc_btn.clicked.connect(self._calculate)
        btn_layout.addWidget(self.calc_btn)

        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.setObjectName("success")
        self.export_csv_btn.setEnabled(False)
        self.export_csv_btn.setToolTip(
            "Save all computed property data to a CSV file."
        )
        self.export_csv_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(self.export_csv_btn)

        self.export_png_btn = QPushButton("Export PNG")
        self.export_png_btn.setObjectName("success")
        self.export_png_btn.setEnabled(False)
        self.export_png_btn.setToolTip(
            "Save the current plot tab as a PNG image."
        )
        self.export_png_btn.clicked.connect(self._export_png)
        btn_layout.addWidget(self.export_png_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # --- Progress bar ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # --- Status + Summary ---
        self.status_label = QLabel("")
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(
            "background-color: rgba(255,255,255,0.05); "
            "border-radius: 6px; padding: 8px; margin-top: 4px;"
        )
        self.summary_label.setVisible(False)
        layout.addWidget(self.summary_label)

        # --- Results tab widget ---
        self.tab_widget = QTabWidget()

        # Tab 1: Property Curves
        self.props_canvas = LazyCanvas(figsize=(8, 5), dpi=100)
        self.props_canvas.setMinimumHeight(350)
        self.tab_widget.addTab(self.props_canvas, "Property Curves")

        # Tab 2: Chemical Potentials
        self.mu_canvas = LazyCanvas(figsize=(8, 5), dpi=100)
        self.mu_canvas.setMinimumHeight(350)
        self.tab_widget.addTab(self.mu_canvas, "Chemical Potentials")

        # Tab 3: Data Table
        self.data_table = QTableWidget()
        self.data_table.setMinimumHeight(250)
        self.data_table.setToolTip(
            "All computed thermodynamic property values at each temperature step."
        )
        self.tab_widget.addTab(self.data_table, "Data Table")

        layout.addWidget(self.tab_widget, stretch=1)

        scroll.setWidget(container)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    # Unit setters
    # ------------------------------------------------------------------

    def set_temp_unit(self, unit: str) -> None:
        """Switch the temperature inputs between 'K' and 'C'."""
        if unit not in ("K", "C") or unit == self._temp_unit:
            return

        old_unit = self._temp_unit
        self._temp_unit = unit

        self.t_min_spin.blockSignals(True)
        self.t_max_spin.blockSignals(True)
        try:
            if old_unit == "K" and unit == "C":
                old_min = self.t_min_spin.value()
                old_max = self.t_max_spin.value()
                self.t_min_spin.setRange(-273, 4727)
                self.t_max_spin.setRange(-273, 4727)
                self.t_min_spin.setValue(k_to_c(old_min))
                self.t_max_spin.setValue(k_to_c(old_max))
                self.t_min_label.setText("T min (\u00b0C):")
                self.t_max_label.setText("T max (\u00b0C):")
            elif old_unit == "C" and unit == "K":
                old_min = self.t_min_spin.value()
                old_max = self.t_max_spin.value()
                self.t_min_spin.setRange(100, 5000)
                self.t_max_spin.setRange(100, 5000)
                self.t_min_spin.setValue(c_to_k(old_min))
                self.t_max_spin.setValue(c_to_k(old_max))
                self.t_min_label.setText("T min (K):")
                self.t_max_label.setText("T max (K):")
        finally:
            self.t_min_spin.blockSignals(False)
            self.t_max_spin.blockSignals(False)

    def set_comp_unit(self, unit: str) -> None:
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
            current_vals: dict[str, float] = {}
            for row in self.comp_rows:
                el = row.element_combo.currentText()
                current_vals[el] = row.composition_spin.value()

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

    # ------------------------------------------------------------------
    # Database update
    # ------------------------------------------------------------------

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

    def update_database(
        self, db: Database, elements: list[str], phases: list[str]
    ) -> None:
        """Called when a new database is loaded."""
        self.db = db
        self.elements = elements
        self.phases = phases

        for row in self.comp_rows:
            row.deleteLater()
        self.comp_rows.clear()

        self.add_comp_btn.setEnabled(True)
        self.calc_btn.setEnabled(len(elements) >= 2)

        if len(elements) >= 2:
            self._add_composition_row()

        self._update_balance()

    # ------------------------------------------------------------------
    # Composition rows
    # ------------------------------------------------------------------

    def _add_composition_row(self) -> None:
        if not self.elements:
            return
        row = CompositionRow(self.elements, comp_unit=self._comp_unit)
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

    def _remove_composition_row(self) -> None:
        if self.comp_rows:
            row = self.comp_rows.pop()
            row.deleteLater()
        self.remove_comp_btn.setEnabled(len(self.comp_rows) > 0)
        self._update_balance()

    # ------------------------------------------------------------------
    # Balance indicator
    # ------------------------------------------------------------------

    def _update_balance(self) -> None:
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

    def _check_duplicate_elements(self) -> None:
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_t_min_k(self) -> float:
        val = self.t_min_spin.value()
        return c_to_k(val) if self._temp_unit == "C" else val

    def _get_t_max_k(self) -> float:
        val = self.t_max_spin.value()
        return c_to_k(val) if self._temp_unit == "C" else val

    def _requested_properties(self) -> list[str]:
        props: list[str] = []
        if self.cb_gibbs.isChecked():
            props.append("GM")
        if self.cb_enthalpy.isChecked():
            props.append("HM")
        if self.cb_entropy.isChecked():
            props.append("SM")
        if self.cb_cp.isChecked():
            props.append("CPM")
        return props

    def _build_conditions_text(self) -> str:
        comp_parts = []
        for row in self.comp_rows:
            el = row.element_combo.currentText()
            val = row.composition_spin.value()
            if self._comp_unit == "weight_percent":
                comp_parts.append(f"{el}={val:.2f} wt%")
            else:
                comp_parts.append(f"{el}={val:.4f}")
        t_min = self._get_t_min_k()
        t_max = self._get_t_max_k()
        return (
            f"Composition: {', '.join(comp_parts)}  |  "
            f"T: {t_min:.0f}-{t_max:.0f} K "
            f"(step {self.t_step_spin.value():.0f} K)  |  "
            f"P: {self.pressure_spin.value():.0f} Pa"
        )

    # ------------------------------------------------------------------
    # Calculation
    # ------------------------------------------------------------------

    def _calculate(self) -> None:
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
                "A calculation is already in progress. Please wait for it "
                "to finish."
            )
            return

        # Collect compositions
        compositions: dict[str, float] = {}
        all_elements: set[str] = set()
        duplicates: set[str] = set()
        for row in self.comp_rows:
            el = row.element_combo.currentText()
            x = row.composition_spin.value()
            if el in compositions:
                duplicates.add(el)
            compositions[el] = x
            all_elements.add(el)

        if duplicates:
            QMessageBox.warning(
                self, "Duplicate Elements",
                f"The following element(s) appear more than once: "
                f"{', '.join(sorted(duplicates))}. "
                f"Please ensure each element is used only once."
            )
            return

        # Validate composition totals
        if self._comp_unit == "weight_percent":
            total_wt = sum(compositions.values())
            if total_wt > 100.01:
                QMessageBox.warning(
                    self, "Composition Too High",
                    f"The total weight percent ({total_wt:.2f}%) exceeds "
                    f"100%. Please reduce one or more element values."
                )
                return
            balance_el = None
            for el in self.elements:
                if el not in all_elements:
                    balance_el = el
                    break
            if balance_el:
                full_wt = dict(compositions)
                full_wt[balance_el] = 100.0 - total_wt
                mole_frac = weight_to_mole(full_wt)
                compositions = {el: mole_frac[el] for el in compositions}
        else:
            total = sum(compositions.values())
            if total > 1.0001:
                QMessageBox.warning(
                    self, "Composition Too High",
                    f"The total mole fraction ({total:.4f}) exceeds 1.0. "
                    f"Please reduce one or more element values."
                )
                return

        # Determine full element list including balance
        elements = list(all_elements)
        for el in self.elements:
            if el not in elements:
                elements.append(el)
                break

        # Validate temperature range
        t_min = self._get_t_min_k()
        t_max = self._get_t_max_k()
        t_step = self.t_step_spin.value()

        if t_min >= t_max:
            QMessageBox.warning(
                self, "Temperature Range Issue",
                f"The minimum temperature must be lower than the maximum. "
                f"Currently T min = {t_min:.0f} K and T max = {t_max:.0f} K."
            )
            return

        n_steps = int((t_max - t_min) / t_step) + 1
        if n_steps > 2000:
            QMessageBox.warning(
                self, "Too Many Steps",
                f"The current settings produce {n_steps} temperature steps. "
                f"Please increase the step size or narrow the range to keep "
                f"the number of steps below 2000."
            )
            return

        requested_props = self._requested_properties()
        calc_mu = self.cb_mu.isChecked()

        if not requested_props and not calc_mu:
            QMessageBox.warning(
                self, "No Properties Selected",
                "Please select at least one thermodynamic property to compute."
            )
            return

        # Start calculation
        self.calc_btn.setEnabled(False)
        self.export_csv_btn.setEnabled(False)
        self.export_png_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_label.setText(
            f"Computing {len(requested_props)} properties over "
            f"{n_steps} temperature steps..."
        )
        self.status_label.setStyleSheet("color: #FFB74D;")
        self.summary_label.setVisible(False)

        self._worker = ThermoPropertiesWorker(
            db=self.db,
            elements=elements,
            compositions=compositions,
            t_min=t_min,
            t_max=t_max,
            t_step=t_step,
            pressure=self.pressure_spin.value(),
            requested_props=requested_props,
            calc_mu=calc_mu,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_calculated)
        self._worker.start()

    def _on_progress(self, pct: int) -> None:
        self.progress_bar.setValue(pct)

    # ------------------------------------------------------------------
    # Results handling
    # ------------------------------------------------------------------

    def _on_calculated(self, data: dict[str, Any]) -> None:
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(True)

        error = data.get("error")
        if error:
            friendly = _friendly_error(error)
            self.status_label.setText("Calculation failed")
            self.status_label.setStyleSheet("color: #E57373;")
            QMessageBox.warning(
                self, "Calculation Did Not Succeed",
                f"{friendly}\n\n(Technical details below.)\n\n{error[-300:]}"
            )
            return

        self._last_data = data
        temps = data["temps"]
        results = data["results"]
        mu_results = data["mu_results"]

        # Plot property curves
        self._plot_property_curves(temps, results)

        # Plot chemical potentials
        if mu_results:
            self._plot_chemical_potentials(temps, mu_results)

        # Fill data table
        self._fill_data_table(temps, results, mu_results)

        # Enable exports
        self.export_csv_btn.setEnabled(True)
        self.export_png_btn.setEnabled(True)

        # Status
        n_props = len(results) + (1 if mu_results else 0)
        self.status_label.setText(
            f"Computed {n_props} properties over "
            f"{format_temp(temps[0])} to {format_temp(temps[-1])}"
        )
        self.status_label.setStyleSheet("color: #81C784;")

        # Summary
        self._show_summary(temps, results)

        # Emit signal for history
        elem_list = [
            row.element_combo.currentText() for row in self.comp_rows
        ]
        cond = {
            "T_min": temps[0],
            "T_max": temps[-1],
            "properties": list(results.keys()),
        }
        self.calculation_done.emit(elem_list, cond, self.summary_label.text())

    def _show_summary(
        self, temps: list[float], results: dict[str, list[float]]
    ) -> None:
        parts: list[str] = []
        n_props = len(results)
        parts.append(
            f"Computed {n_props} "
            f"{'property' if n_props == 1 else 'properties'} over "
            f"{temps[0]:.0f}-{temps[-1]:.0f} K."
        )

        if "GM" in results:
            gm = np.array(results["GM"])
            valid = gm[~np.isnan(gm)]
            if len(valid) > 0:
                parts.append(
                    f"G ranges from {valid.min():.0f} to "
                    f"{valid.max():.0f} J/mol."
                )

        if "HM" in results:
            hm = np.array(results["HM"])
            valid = hm[~np.isnan(hm)]
            if len(valid) > 0:
                parts.append(
                    f"H ranges from {valid.min():.0f} to "
                    f"{valid.max():.0f} J/mol."
                )

        if "SM" in results:
            sm = np.array(results["SM"])
            valid = sm[~np.isnan(sm)]
            if len(valid) > 0:
                parts.append(
                    f"S ranges from {valid.min():.2f} to "
                    f"{valid.max():.2f} J/mol/K."
                )

        self.summary_label.setText("  ".join(parts))
        self.summary_label.setVisible(True)

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def _configure_axis(self, ax: Any) -> None:
        """Apply the dark theme to a matplotlib axis."""
        ax.set_facecolor("#1e1e2e")
        ax.tick_params(colors="white", which="both")
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.title.set_color("white")
        for spine in ax.spines.values():
            spine.set_color("#555555")
        ax.grid(True, color="#555555", alpha=0.3, linestyle="--")

    def _add_celsius_axis(self, ax: Any) -> None:
        """Add a secondary Celsius x-axis on top."""
        ax_c = ax.secondary_xaxis(
            "top", functions=(k_to_c, c_to_k)
        )
        ax_c.set_xlabel("Temperature (\u00b0C)", color="white", fontsize=9)
        ax_c.tick_params(colors="white")

    def _plot_property_curves(
        self, temps: list[float], results: dict[str, list[float]]
    ) -> None:
        self.props_canvas.figure.clear()
        if not results:
            self.props_canvas.draw()
            return

        t_arr = np.array(temps)

        # Separate properties into two groups by unit:
        # Left axis: G (J/mol) and H (J/mol)
        # Right axis: S (J/mol/K) and Cp (J/mol/K)
        left_props = [p for p in ("GM", "HM") if p in results]
        right_props = [p for p in ("SM", "CPM") if p in results]

        ax_left = self.props_canvas.figure.add_subplot(111)
        self._configure_axis(ax_left)
        ax_left.set_xlabel("Temperature (K)", fontsize=10)

        lines = []
        labels = []

        # Plot left-axis properties
        if left_props:
            ax_left.set_ylabel("Energy (J/mol)", color="white", fontsize=10)
            for prop in left_props:
                vals = np.array(results[prop])
                color = PROPERTY_COLORS[prop]
                line, = ax_left.plot(
                    t_arr[:len(vals)], vals,
                    color=color, linewidth=1.8,
                    label=PROPERTY_SHORT[prop],
                )
                lines.append(line)
                labels.append(PROPERTY_SHORT[prop])

        # Plot right-axis properties on a twin axis
        ax_right = None
        if right_props:
            ax_right = ax_left.twinx()
            ax_right.set_ylabel(
                "Entropy / Heat Capacity (J/mol/K)",
                color="white", fontsize=10,
            )
            ax_right.tick_params(colors="white")
            ax_right.yaxis.label.set_color("white")
            for spine in ax_right.spines.values():
                spine.set_color("#555555")

            for prop in right_props:
                vals = np.array(results[prop])
                color = PROPERTY_COLORS[prop]
                line, = ax_right.plot(
                    t_arr[:len(vals)], vals,
                    color=color, linewidth=1.8, linestyle="--",
                    label=PROPERTY_SHORT[prop],
                )
                lines.append(line)
                labels.append(PROPERTY_SHORT[prop])

        # If there are no left props but there are right props, update left label
        if not left_props and right_props:
            ax_left.set_ylabel(
                "Entropy / Heat Capacity (J/mol/K)",
                color="white", fontsize=10,
            )

        # Combined legend
        if lines:
            ax_left.legend(
                lines, labels,
                loc="best",
                facecolor="#2a2a3e",
                edgecolor="#555555",
                labelcolor="white",
                fontsize=9,
            )

        ax_left.set_title(
            "Thermodynamic Properties vs Temperature",
            color="white", fontsize=12, pad=20,
        )

        # Add Celsius axis on top
        self._add_celsius_axis(ax_left)

        self.props_canvas.figure.tight_layout()
        self.props_canvas.draw()
        self.props_canvas.enable_line_hover()

    def _plot_chemical_potentials(
        self, temps: list[float], mu_results: dict[str, list[float]]
    ) -> None:
        self.mu_canvas.figure.clear()
        if not mu_results:
            self.mu_canvas.draw()
            return

        ax = self.mu_canvas.figure.add_subplot(111)
        self._configure_axis(ax)

        t_arr = np.array(temps)

        for idx, (el, mu_vals) in enumerate(sorted(mu_results.items())):
            color = PHASE_COLORS[idx % len(PHASE_COLORS)]
            vals = np.array(mu_vals)
            ax.plot(
                t_arr[:len(vals)], vals,
                color=color, linewidth=1.8,
                label=f"\u03bc({el})",
            )

        ax.set_xlabel("Temperature (K)", fontsize=10)
        ax.set_ylabel("Chemical Potential (J/mol)", color="white", fontsize=10)
        ax.set_title(
            "Chemical Potentials vs Temperature",
            color="white", fontsize=12, pad=20,
        )

        handles, labels = ax.get_legend_handles_labels()
        if len(handles) <= 8:
            ax.legend(fontsize=8, loc="best", facecolor="#2d2d3e", edgecolor="#555555", labelcolor="white")
        else:
            ax.legend(fontsize=7, loc="center left", bbox_to_anchor=(1.02, 0.5),
                      facecolor="#2d2d3e", edgecolor="#555555", labelcolor="white", borderaxespad=0)

        self._add_celsius_axis(ax)
        self.mu_canvas.figure.tight_layout()
        self.mu_canvas.draw()
        self.mu_canvas.enable_line_hover()

    # ------------------------------------------------------------------
    # Data table
    # ------------------------------------------------------------------

    def _fill_data_table(
        self,
        temps: list[float],
        results: dict[str, list[float]],
        mu_results: dict[str, list[float]],
    ) -> None:
        prop_keys = list(results.keys())
        mu_keys = sorted(mu_results.keys()) if mu_results else []

        columns = ["T (K)", "T (\u00b0C)"]
        columns.extend(PROPERTY_LABELS.get(k, k) for k in prop_keys)
        columns.extend(f"\u03bc({el}) (J/mol)" for el in mu_keys)

        n_rows = len(temps)
        self.data_table.setRowCount(n_rows)
        self.data_table.setColumnCount(len(columns))
        self.data_table.setHorizontalHeaderLabels(columns)

        for i, temp in enumerate(temps):
            self.data_table.setItem(i, 0, QTableWidgetItem(f"{temp:.1f}"))
            self.data_table.setItem(
                i, 1, QTableWidgetItem(f"{k_to_c(temp):.1f}")
            )

            col = 2
            for key in prop_keys:
                val = results[key][i] if i < len(results[key]) else float("nan")
                if np.isnan(val):
                    self.data_table.setItem(i, col, QTableWidgetItem("NaN"))
                else:
                    self.data_table.setItem(
                        i, col, QTableWidgetItem(f"{val:.4f}")
                    )
                col += 1

            for el in mu_keys:
                val = (
                    mu_results[el][i]
                    if i < len(mu_results[el])
                    else float("nan")
                )
                if np.isnan(val):
                    self.data_table.setItem(i, col, QTableWidgetItem("NaN"))
                else:
                    self.data_table.setItem(
                        i, col, QTableWidgetItem(f"{val:.4f}")
                    )
                col += 1

        # Smart column sizing
        n_cols = self.data_table.columnCount()
        if n_cols <= 8:
            self.data_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )
        else:
            self.data_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Interactive
            )
            self.data_table.horizontalHeader().setDefaultSectionSize(90)

    # ------------------------------------------------------------------
    # Export CSV
    # ------------------------------------------------------------------

    def _export_csv(self) -> None:
        if not self._last_data:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Thermodynamic Data", "thermo_properties.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return

        data = self._last_data
        temps = data["temps"]
        results = data["results"]
        mu_results = data.get("mu_results", {})

        prop_keys = list(results.keys())
        mu_keys = sorted(mu_results.keys()) if mu_results else []

        try:
            with open(path, "w", newline="") as f:
                f.write("# CALPHAD Thermodynamic Properties\n")
                f.write(
                    f"# Generated: "
                    f"{datetime.datetime.now().isoformat(timespec='seconds')}\n"
                )
                f.write(f"# {self._build_conditions_text()}\n")
                f.write("#\n")

                # Header
                header = ["T_K", "T_C"]
                header.extend(prop_keys)
                header.extend(f"MU_{el}" for el in mu_keys)
                f.write(",".join(header) + "\n")

                # Data rows
                for i, temp in enumerate(temps):
                    row_vals = [f"{temp:.2f}", f"{k_to_c(temp):.2f}"]
                    for key in prop_keys:
                        val = (
                            results[key][i]
                            if i < len(results[key])
                            else float("nan")
                        )
                        row_vals.append(f"{val:.6f}")
                    for el in mu_keys:
                        val = (
                            mu_results[el][i]
                            if i < len(mu_results[el])
                            else float("nan")
                        )
                        row_vals.append(f"{val:.6f}")
                    f.write(",".join(row_vals) + "\n")

            self.status_label.setText(f"Exported to {path}")
        except Exception as exc:
            QMessageBox.critical(
                self, "Export Failed",
                f"Could not write CSV file:\n\n{exc}"
            )

    # ------------------------------------------------------------------
    # Export PNG
    # ------------------------------------------------------------------

    def _export_png(self) -> None:
        if not self._last_data:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Property Plot", "thermo_properties.png",
            "PNG Files (*.png);;All Files (*)"
        )
        if not path:
            return

        # Determine which figure to export based on current tab
        current_idx = self.tab_widget.currentIndex()
        if current_idx == 1:
            figure = self.mu_canvas.figure
            canvas = self.mu_canvas
        else:
            figure = self.props_canvas.figure
            canvas = self.props_canvas

        conditions = self._build_conditions_text()
        annotation = figure.text(
            0.01, 0.01, conditions,
            fontsize=7, color="#888888",
            transform=figure.transFigure,
            ha="left", va="bottom",
        )

        try:
            figure.savefig(
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
            canvas.draw()
