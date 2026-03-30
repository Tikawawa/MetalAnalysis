"""Driving Force & Metastable Phase Analysis panel.

Computes the thermodynamic driving force for each non-stable phase,
showing how close metastable phases are to becoming stable.
Supports single-point analysis and temperature sweep modes.
"""

from __future__ import annotations

import datetime
import io

import numpy as np
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QSplitter, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from pycalphad import Database, equilibrium, calculate, variables as v

from core.presets import translate_phase_short, translate_phase_name, ATOMIC_WEIGHTS
from core.units import k_to_c, c_to_k, format_temp, mole_to_weight, weight_to_mole
from gui.info_content import TAB_INFO


# ---------------------------------------------------------------------------
# Phase color palette
# ---------------------------------------------------------------------------

PHASE_COLORS = [
    "#4FC3F7", "#81C784", "#FFB74D", "#E57373", "#BA68C8",
    "#4DB6AC", "#FFD54F", "#7986CB", "#A1887F", "#90A4AE",
]


# ---------------------------------------------------------------------------
# Driving force color thresholds
# ---------------------------------------------------------------------------

_DF_GREEN = "#81C784"    # > 2000 J/mol -- far from stable
_DF_ORANGE = "#FFB74D"   # 500-2000 J/mol -- approaching
_DF_RED = "#E57373"      # < 500 J/mol -- near stability


def _df_color(df_value: float) -> str:
    """Return a color hex string based on driving force magnitude."""
    if np.isnan(df_value):
        return "#90A4AE"
    if df_value < 500.0:
        return _DF_RED
    if df_value < 2000.0:
        return _DF_ORANGE
    return _DF_GREEN


# ---------------------------------------------------------------------------
# Driving force computation
# ---------------------------------------------------------------------------

def compute_driving_forces(
    db: Database,
    elements: list[str],
    compositions: dict[str, float],
    temperature: float,
    pressure: float,
) -> tuple[list[str], dict[str, float]]:
    """Compute the driving force for every non-stable phase.

    Returns:
        (stable_phases, driving_forces) where driving_forces maps
        phase name -> driving force in J/mol (positive = metastable).
    """
    comps = sorted([e.upper() for e in elements]) + ["VA"]
    all_phases = list(db.phases.keys())

    # Build conditions dict
    conds = {v.T: temperature, v.P: pressure, v.N: 1}
    for el, x in compositions.items():
        conds[v.X(el.upper())] = x

    eq = equilibrium(db, comps, all_phases, conds)

    # Identify stable phases
    stable_phases: list[str] = []
    phase_names = eq.Phase.values.squeeze()
    np_values = eq.NP.values.squeeze()
    if phase_names.ndim == 0:
        phase_names = np.array([phase_names])
        np_values = np.array([np_values])
    for pname, frac in zip(phase_names, np_values):
        pname_str = str(pname).strip()
        if pname_str and pname_str != "" and not np.isnan(frac) and frac > 1e-10:
            stable_phases.append(pname_str)

    # Equilibrium Gibbs energy (hyperplane reference)
    hyperplane_g = float(eq.GM.values.squeeze())

    # Compute driving force for each non-stable phase
    driving_forces: dict[str, float] = {}
    for phase in all_phases:
        if phase in stable_phases:
            continue
        try:
            calc_res = calculate(
                db, comps, [phase], T=temperature, P=pressure, N=1, output="GM",
            )
            gm_values = calc_res.GM.values.squeeze()
            if gm_values.ndim > 0:
                min_gm = float(np.nanmin(gm_values))
            else:
                min_gm = float(gm_values)

            df = min_gm - hyperplane_g
            driving_forces[phase] = max(0.0, df)
        except Exception:
            driving_forces[phase] = float("nan")

    return stable_phases, driving_forces


# ---------------------------------------------------------------------------
# Friendly error translation
# ---------------------------------------------------------------------------

_FRIENDLY_ERRORS: list[tuple[str, str]] = [
    ("Composition.*out of range",
     "One of your composition values is outside the valid range for this "
     "thermodynamic database. Try reducing the amount of the alloying element."),
    ("No solution found",
     "The solver could not find a stable equilibrium at these conditions. "
     "Try a different temperature or adjust the composition."),
    ("singular matrix",
     "The calculation hit a numerical singularity. This sometimes happens "
     "very close to a phase boundary. Try shifting the temperature by a few "
     "degrees or tweaking the composition slightly."),
    ("Database",
     "There may be a problem with the thermodynamic database for this element "
     "combination. Make sure all selected elements are covered by the loaded "
     "database."),
]


def _friendly_error(raw: str) -> str:
    """Return a user-friendly error message based on the raw traceback."""
    import re
    for pattern, friendly in _FRIENDLY_ERRORS:
        if re.search(pattern, raw, re.IGNORECASE):
            return friendly
    return (
        "The driving force calculation did not succeed. This can happen when "
        "the thermodynamic database does not cover the requested conditions.\n\n"
        "Suggestions:\n"
        "  - Check that every element is present in the database.\n"
        "  - Try a temperature closer to room temperature or the known "
        "melting range.\n"
        "  - Reduce extreme composition values."
    )


# ---------------------------------------------------------------------------
# Worker thread -- point mode
# ---------------------------------------------------------------------------

class DrivingForcePointWorker(QThread):
    """Worker thread for a single-point driving force calculation."""

    finished = pyqtSignal(object)  # (stable_phases, driving_forces, temperature) or error str

    def __init__(self, db, elements, compositions, temperature, pressure):
        super().__init__()
        self.db = db
        self.elements = elements
        self.compositions = compositions
        self.temperature = temperature
        self.pressure = pressure

    def run(self):
        try:
            stable, dfs = compute_driving_forces(
                self.db, self.elements, self.compositions,
                self.temperature, self.pressure,
            )
            self.finished.emit((stable, dfs, self.temperature, None))
        except Exception as exc:
            import traceback
            self.finished.emit(([], {}, self.temperature, traceback.format_exc()))


# ---------------------------------------------------------------------------
# Worker thread -- sweep mode
# ---------------------------------------------------------------------------

class DrivingForceSweepWorker(QThread):
    """Worker thread for a temperature-sweep driving force calculation."""

    progress = pyqtSignal(int)       # percent complete
    finished = pyqtSignal(object)    # results dict or error

    def __init__(self, db, elements, compositions, t_min, t_max, t_step, pressure):
        super().__init__()
        self.db = db
        self.elements = elements
        self.compositions = compositions
        self.t_min = t_min
        self.t_max = t_max
        self.t_step = t_step
        self.pressure = pressure

    def run(self):
        try:
            temperatures = np.arange(self.t_min, self.t_max + 0.1, self.t_step)
            n_steps = len(temperatures)

            # {phase: [df_at_T0, df_at_T1, ...]}
            sweep_data: dict[str, list[float]] = {}
            stable_at_each_t: list[list[str]] = []
            temp_list: list[float] = []

            for i, t in enumerate(temperatures):
                stable, dfs = compute_driving_forces(
                    self.db, self.elements, self.compositions,
                    float(t), self.pressure,
                )
                stable_at_each_t.append(stable)
                temp_list.append(float(t))

                for phase, df_val in dfs.items():
                    if phase not in sweep_data:
                        # Back-fill with NaN for previous temperatures
                        sweep_data[phase] = [float("nan")] * i
                    sweep_data[phase].append(df_val)

                # Fill NaN for phases not present at this temperature
                for phase in sweep_data:
                    if len(sweep_data[phase]) <= i:
                        sweep_data[phase].append(float("nan"))

                pct = int((i + 1) / n_steps * 100)
                self.progress.emit(pct)

            self.finished.emit({
                "temperatures": temp_list,
                "sweep_data": sweep_data,
                "stable_at_each_t": stable_at_each_t,
                "error": None,
            })
        except Exception:
            import traceback
            self.finished.emit({"error": traceback.format_exc()})


# ---------------------------------------------------------------------------
# Composition row
# ---------------------------------------------------------------------------

class CompositionRow(QWidget):
    """A single element-composition input row."""

    def __init__(self, elements: list[str], comp_unit: str = "mole_fraction",
                 parent=None):
        super().__init__(parent)
        self._comp_unit = comp_unit
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.element_combo = QComboBox()
        self.element_combo.addItems(elements)
        self.element_combo.setToolTip(
            "Select the alloying element whose composition you want to set."
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
# Main panel
# ---------------------------------------------------------------------------

class DrivingForcePanel(QWidget):
    """Panel for driving force and metastable phase analysis."""

    calculation_done = pyqtSignal(list, dict, str)  # (elements, conditions, summary)

    def __init__(self):
        super().__init__()
        self.db: Database | None = None
        self.elements: list[str] = []
        self.comp_rows: list[CompositionRow] = []
        self._worker: DrivingForcePointWorker | DrivingForceSweepWorker | None = None
        self._last_point_result: tuple | None = None
        self._last_sweep_result: dict | None = None
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

        title = QLabel("Driving Force Analysis")
        title.setObjectName("heading")
        layout.addWidget(title)

        # --- Educational info panel (collapsible) ---
        info_data = TAB_INFO.get("driving_force", {})
        self._info_btn = QPushButton("▶  What Is This?  (click to learn)")
        self._info_btn.setFlat(True)
        self._info_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._info_btn.setStyleSheet(
            "QPushButton { color: #4FC3F7; font-size: 13px; font-weight: bold; "
            "text-align: left; padding: 6px 12px; border: 1px solid #333355; "
            "border-radius: 4px; background: #16213e; }"
            "QPushButton:hover { background: #1a2a4a; border-color: #4FC3F7; }"
        )
        self._info_btn.clicked.connect(self._toggle_info)
        layout.addWidget(self._info_btn)

        simple = info_data.get("simple", "")
        analogy = info_data.get("analogy", "")
        tips = info_data.get("tips", [])
        tips_html = "".join(f"<li>{t}</li>" for t in tips)
        self._info_text = QLabel()
        self._info_text.setWordWrap(True)
        self._info_text.setTextFormat(Qt.TextFormat.RichText)
        self._info_text.setStyleSheet(
            "color: #ccccdd; font-size: 13px; padding: 10px 14px; "
            "background: #16213e; border: 1px solid #333355; border-radius: 4px;"
        )
        self._info_text.setText(
            f'<p style="color: #e0e0e0;">{simple}</p>'
            f'<p style="color: #81C784;"><b>Think of it like:</b> {analogy}</p>'
            f'<p style="color: #FFB74D;"><b>Tips:</b></p><ul>{tips_html}</ul>'
        )
        self._info_text.setVisible(False)
        layout.addWidget(self._info_text)

        # --- Composition inputs ---
        self.comp_group = QGroupBox("Alloy Composition")
        self.comp_layout = QVBoxLayout()

        comp_btn_layout = QHBoxLayout()
        self.add_comp_btn = QPushButton("+ Add Element")
        self.add_comp_btn.setToolTip("Add another alloying element row.")
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

        # Balance indicator
        self.balance_label = QLabel("")
        self.balance_label.setToolTip(
            "Live composition balance. Shows each element and the total."
        )
        self.balance_label.setStyleSheet("padding: 4px; font-weight: bold;")
        self.comp_layout.addWidget(self.balance_label)

        self.comp_group.setLayout(self.comp_layout)
        layout.addWidget(self.comp_group)

        # --- Conditions ---
        cond_group = QGroupBox("Conditions")
        cond_layout = QHBoxLayout()

        self.temp_label = QLabel("Temperature (K):")
        cond_layout.addWidget(self.temp_label)
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(100, 5000)
        self.temp_spin.setValue(800)
        self.temp_spin.setSingleStep(10)
        self.temp_spin.setToolTip(
            "Temperature for equilibrium calculation. "
            "Room temp = 298 K (25 C). Al melts at 933 K (660 C)."
        )
        cond_layout.addWidget(self.temp_spin)

        cond_layout.addWidget(QLabel("Pressure (Pa):"))
        self.pressure_spin = QDoubleSpinBox()
        self.pressure_spin.setRange(1, 1e9)
        self.pressure_spin.setValue(101325)
        self.pressure_spin.setDecimals(0)
        self.pressure_spin.setSingleStep(1000)
        self.pressure_spin.setToolTip(
            "Pressure in Pascals. 101325 Pa = 1 atmosphere (standard)."
        )
        cond_layout.addWidget(self.pressure_spin)

        cond_layout.addStretch()
        cond_group.setLayout(cond_layout)
        layout.addWidget(cond_group)

        # --- Analysis Options ---
        opts_group = QGroupBox("Analysis Options")
        opts_layout = QVBoxLayout()

        # Warning threshold
        thresh_layout = QHBoxLayout()
        thresh_layout.addWidget(QLabel("Warning threshold (J/mol):"))
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0, 100000)
        self.threshold_spin.setValue(1000)
        self.threshold_spin.setDecimals(0)
        self.threshold_spin.setSingleStep(100)
        self.threshold_spin.setToolTip(
            "Phases with a driving force below this value will be flagged as "
            "near-stability warnings."
        )
        thresh_layout.addWidget(self.threshold_spin)
        thresh_layout.addStretch()
        opts_layout.addLayout(thresh_layout)

        # Sweep mode checkbox
        self.sweep_check = QCheckBox("Temperature sweep mode")
        self.sweep_check.setToolTip(
            "Enable to scan driving forces over a temperature range instead "
            "of a single point."
        )
        self.sweep_check.toggled.connect(self._on_sweep_toggled)
        opts_layout.addWidget(self.sweep_check)

        # Sweep range inputs (hidden by default)
        self.sweep_widget = QWidget()
        sweep_layout = QHBoxLayout(self.sweep_widget)
        sweep_layout.setContentsMargins(0, 0, 0, 0)

        self.t_min_label = QLabel("T min (K):")
        sweep_layout.addWidget(self.t_min_label)
        self.t_min_spin = QDoubleSpinBox()
        self.t_min_spin.setRange(100, 5000)
        self.t_min_spin.setValue(300)
        self.t_min_spin.setSingleStep(50)
        self.t_min_spin.setToolTip("Lowest temperature in the sweep (Kelvin).")
        sweep_layout.addWidget(self.t_min_spin)

        self.t_max_label = QLabel("T max (K):")
        sweep_layout.addWidget(self.t_max_label)
        self.t_max_spin = QDoubleSpinBox()
        self.t_max_spin.setRange(100, 5000)
        self.t_max_spin.setValue(1200)
        self.t_max_spin.setSingleStep(50)
        self.t_max_spin.setToolTip("Highest temperature in the sweep (Kelvin).")
        sweep_layout.addWidget(self.t_max_spin)

        sweep_layout.addWidget(QLabel("Step (K):"))
        self.t_step_spin = QDoubleSpinBox()
        self.t_step_spin.setRange(1, 200)
        self.t_step_spin.setValue(10)
        self.t_step_spin.setSingleStep(5)
        self.t_step_spin.setToolTip(
            "Temperature increment between calculations. "
            "Smaller = more precise but slower."
        )
        sweep_layout.addWidget(self.t_step_spin)

        sweep_layout.addStretch()
        self.sweep_widget.setVisible(False)
        opts_layout.addWidget(self.sweep_widget)

        opts_group.setLayout(opts_layout)
        layout.addWidget(opts_group)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        self.calc_btn = QPushButton("Calculate Driving Forces")
        self.calc_btn.setObjectName("primary")
        self.calc_btn.setEnabled(False)
        self.calc_btn.setToolTip(
            "Run the driving force analysis at the specified conditions."
        )
        self.calc_btn.clicked.connect(self._calculate)
        btn_layout.addWidget(self.calc_btn)

        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.setObjectName("success")
        self.export_csv_btn.setEnabled(False)
        self.export_csv_btn.setToolTip("Save driving force results as a CSV file.")
        self.export_csv_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(self.export_csv_btn)

        self.export_png_btn = QPushButton("Export PNG")
        self.export_png_btn.setObjectName("success")
        self.export_png_btn.setEnabled(False)
        self.export_png_btn.setToolTip("Save the driving force chart as a PNG image.")
        self.export_png_btn.clicked.connect(self._export_png)
        btn_layout.addWidget(self.export_png_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # --- Progress ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)

        # --- Plain-English summary ---
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(
            "background-color: rgba(255,255,255,0.05); "
            "border-radius: 6px; padding: 8px; margin-top: 4px;"
        )
        self.summary_label.setVisible(False)
        layout.addWidget(self.summary_label)

        # --- Warning box (orange styled) ---
        self.warning_label = QLabel("")
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet(
            "color: #FFB74D; background-color: #3a2a1a; "
            "border: 1px solid #FFB74D; border-radius: 6px; "
            "padding: 8px; margin-top: 4px; font-weight: bold;"
        )
        self.warning_label.setVisible(False)
        layout.addWidget(self.warning_label)

        # --- Results: table + chart in splitter ---
        self.splitter = QSplitter()

        self.results_table = QTableWidget()
        self.results_table.setMinimumHeight(150)
        self.results_table.setToolTip(
            "Driving force results. Each row shows a metastable phase and its "
            "distance from stability in J/mol."
        )
        self.splitter.addWidget(self.results_table)

        self.figure = Figure(figsize=(6, 4), dpi=100)
        self.figure.patch.set_facecolor("#1e1e2e")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(300)
        self.splitter.addWidget(self.canvas)

        self.splitter.setSizes([300, 500])
        layout.addWidget(self.splitter, stretch=1)

        scroll.setWidget(container)
        outer.addWidget(scroll)

    # -------------------------------------------------------- sweep toggle

    def _on_sweep_toggled(self, checked: bool):
        """Show or hide the sweep range inputs."""
        self.sweep_widget.setVisible(checked)
        if checked:
            self.calc_btn.setText("Calculate Sweep")
        else:
            self.calc_btn.setText("Calculate Driving Forces")

    # -------------------------------------------------------- unit setters

    def set_temp_unit(self, unit: str):
        """Switch the temperature input between 'K' and 'C'."""
        if unit not in ("K", "C") or unit == self._temp_unit:
            return
        old_val = self.temp_spin.value()
        self._temp_unit = unit

        # Point-mode temperature
        if unit == "C":
            self.temp_label.setText("Temperature (C):")
            self.temp_spin.setRange(-173, 4727)
            self.temp_spin.setValue(k_to_c(old_val))
            self.temp_spin.setToolTip(
                "Temperature in Celsius. Room temp = 25 C. "
                "Al melts at 660 C (933 K)."
            )
        else:
            self.temp_label.setText("Temperature (K):")
            self.temp_spin.setRange(100, 5000)
            self.temp_spin.setValue(old_val + 273.15)
            self.temp_spin.setToolTip(
                "Temperature for driving force calculation. "
                "Room temp = 298 K (25 C). Al melts at 933 K (660 C)."
            )

        # Sweep range temperatures
        self.t_min_spin.blockSignals(True)
        self.t_max_spin.blockSignals(True)
        try:
            old_min = self.t_min_spin.value()
            old_max = self.t_max_spin.value()
            if unit == "C":
                self.t_min_spin.setRange(-273, 4727)
                self.t_max_spin.setRange(-273, 4727)
                self.t_min_spin.setValue(k_to_c(old_min))
                self.t_max_spin.setValue(k_to_c(old_max))
                self.t_min_label.setText("T min (\u00b0C):")
                self.t_max_label.setText("T max (\u00b0C):")
            else:
                self.t_min_spin.setRange(100, 5000)
                self.t_max_spin.setRange(100, 5000)
                self.t_min_spin.setValue(c_to_k(old_min))
                self.t_max_spin.setValue(c_to_k(old_max))
                self.t_min_label.setText("T min (K):")
                self.t_max_label.setText("T max (K):")
        finally:
            self.t_min_spin.blockSignals(False)
            self.t_max_spin.blockSignals(False)

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
            self.comp_group.setTitle("Alloy Composition")

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

    # -------------------------------------------------------- database load

    def _toggle_info(self):
        """Toggle the educational info panel visibility."""
        visible = not self._info_text.isVisible()
        self._info_text.setVisible(visible)
        if visible:
            self._info_btn.setText("▼  What Is This?  (click to hide)")
        else:
            self._info_btn.setText("▶  What Is This?  (click to learn)")

    def update_database(self, db: Database, elements: list[str], phases: list[str]):
        """Called when the user loads a new database."""
        self.db = db
        self.elements = elements

        for row in self.comp_rows:
            row.deleteLater()
        self.comp_rows.clear()

        self.add_comp_btn.setEnabled(True)
        self.calc_btn.setEnabled(len(elements) >= 2)

        if len(elements) >= 2:
            self._add_composition_row()

        self._update_balance()

    # ----------------------------------------------------- composition rows

    def _add_composition_row(self):
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
        row.element_combo.currentTextChanged.connect(self._check_duplicate_elements)
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
        """Recalculate and display the composition balance indicator."""
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
        """Highlight element combos that duplicate another row's element."""
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

    # ---------------------------------------------------------- helpers

    def _get_temperature_k(self) -> float:
        """Return the current point-mode temperature in Kelvin."""
        val = self.temp_spin.value()
        if self._temp_unit == "C":
            return val + 273.15
        return val

    def _get_sweep_temps_k(self) -> tuple[float, float, float]:
        """Return (t_min, t_max, t_step) in Kelvin."""
        t_min = self.t_min_spin.value()
        t_max = self.t_max_spin.value()
        t_step = self.t_step_spin.value()
        if self._temp_unit == "C":
            t_min = c_to_k(t_min)
            t_max = c_to_k(t_max)
        return t_min, t_max, t_step

    def _collect_compositions(self) -> tuple[list[str], dict[str, float]] | None:
        """Collect and validate compositions from the UI rows.

        Returns (elements, compositions_mole_frac) or None on validation failure.
        """
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
            return None

        if len(all_elements) < 1:
            QMessageBox.warning(
                self, "Missing Input",
                "Please specify at least one element and its composition."
            )
            return None

        # Convert weight percent to mole fraction for the engine
        if self._comp_unit == "weight_percent":
            total_wt = sum(compositions.values())
            if total_wt > 100.01:
                QMessageBox.warning(
                    self, "Composition Too High",
                    f"The total weight percent ({total_wt:.2f}%) exceeds 100%."
                )
                return None
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
                    f"The total mole fraction ({total:.4f}) exceeds 1.0."
                )
                return None

        # Add balance element
        elements = list(all_elements)
        for el in self.elements:
            if el not in elements:
                elements.append(el)
                break

        return elements, compositions

    # ---------------------------------------------------------- calculate

    def _calculate(self):
        if not self.db or not self.comp_rows:
            QMessageBox.warning(
                self, "Missing Input",
                "Please load a database and add at least one element."
            )
            return

        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(
                self, "Please Wait",
                "Calculation already in progress. Please wait for it to finish."
            )
            return

        result = self._collect_compositions()
        if result is None:
            return
        elements, compositions = result

        pressure = self.pressure_spin.value()

        self.calc_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.summary_label.setVisible(False)
        self.warning_label.setVisible(False)

        if self.sweep_check.isChecked():
            t_min, t_max, t_step = self._get_sweep_temps_k()
            if t_min >= t_max:
                QMessageBox.warning(
                    self, "Temperature Range Issue",
                    "The minimum temperature must be lower than the maximum."
                )
                self.calc_btn.setEnabled(True)
                self.progress_bar.setVisible(False)
                return

            self.progress_bar.setRange(0, 100)
            self.status_label.setText("Calculating driving force sweep...")
            self.status_label.setStyleSheet("color: #FFB74D;")

            self._worker = DrivingForceSweepWorker(
                self.db, elements, compositions,
                t_min, t_max, t_step, pressure,
            )
            self._worker.progress.connect(self._on_sweep_progress)
            self._worker.finished.connect(self._on_sweep_finished)
            self._worker.start()
        else:
            temperature = self._get_temperature_k()
            self.progress_bar.setRange(0, 0)
            self.status_label.setText("Calculating driving forces...")
            self.status_label.setStyleSheet("color: #FFB74D;")

            self._worker = DrivingForcePointWorker(
                self.db, elements, compositions, temperature, pressure,
            )
            self._worker.finished.connect(self._on_point_finished)
            self._worker.start()

    # ------------------------------------------------------- point results

    def _on_point_finished(self, result: tuple):
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(True)

        stable_phases, driving_forces, temperature, error = result

        if error:
            friendly = _friendly_error(error)
            self.status_label.setText("Calculation failed")
            self.status_label.setStyleSheet("color: #E57373;")
            QMessageBox.warning(
                self, "Calculation Did Not Succeed",
                f"{friendly}\n\n(Technical details below.)\n\n{error[-300:]}"
            )
            return

        self._last_point_result = result
        self._last_sweep_result = None

        threshold = self.threshold_spin.value()

        # --- Update table ---
        sorted_phases = sorted(
            driving_forces.items(),
            key=lambda x: x[1] if not np.isnan(x[1]) else float("inf"),
        )

        self.results_table.setRowCount(len(sorted_phases))
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels([
            "Phase", "Name", "Driving Force (J/mol)", "Status",
        ])

        for i, (phase, df_val) in enumerate(sorted_phases):
            # Phase code
            item_phase = QTableWidgetItem(phase)
            self.results_table.setItem(i, 0, item_phase)

            # Translated name
            item_name = QTableWidgetItem(
                f"{translate_phase_short(phase)} - {translate_phase_name(phase)}"
            )
            self.results_table.setItem(i, 1, item_name)

            # Driving force value
            if np.isnan(df_val):
                item_df = QTableWidgetItem("N/A")
            else:
                item_df = QTableWidgetItem(f"{df_val:.1f}")
            self.results_table.setItem(i, 2, item_df)

            # Status label
            color = _df_color(df_val)
            if np.isnan(df_val):
                status_text = "Could not compute"
            elif df_val < 500:
                status_text = "Near stability!"
            elif df_val < 2000:
                status_text = "Approaching"
            else:
                status_text = "Far from stable"
            item_status = QTableWidgetItem(status_text)
            self.results_table.setItem(i, 3, item_status)

            # Color the entire row
            for j in range(4):
                cell = self.results_table.item(i, j)
                if cell is not None:
                    cell.setForeground(QColor(color))

        # Smart column sizing
        n_cols = self.results_table.columnCount()
        if n_cols <= 8:
            self.results_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )
        else:
            self.results_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Interactive
            )
            self.results_table.horizontalHeader().setDefaultSectionSize(90)

        # --- Update chart (horizontal bar) ---
        self._plot_point_bars(sorted_phases, temperature)
        self.canvas.draw()

        # --- Summary ---
        self._show_point_summary(stable_phases, driving_forces, temperature, threshold)

        # --- Warning box ---
        self._show_warnings(driving_forces, temperature, threshold)

        self.export_csv_btn.setEnabled(True)
        self.export_png_btn.setEnabled(True)
        self.status_label.setText(
            f"Driving forces: {len(stable_phases)} stable, "
            f"{len(driving_forces)} metastable phases at "
            f"{format_temp(temperature)}"
        )
        self.status_label.setStyleSheet("color: #81C784;")

        # Emit signal for history logging
        elem_list = list({r.element_combo.currentText() for r in self.comp_rows})
        cond = {"T": temperature, "P": self.pressure_spin.value()}
        summary_text = self.summary_label.text()
        self.calculation_done.emit(elem_list, cond, summary_text)

    def _plot_point_bars(
        self,
        sorted_phases: list[tuple[str, float]],
        temperature: float,
    ):
        """Plot a horizontal bar chart of driving forces."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor("#1a1a2e")

        # Filter out NaN values for plotting
        valid = [(p, df) for p, df in sorted_phases if not np.isnan(df)]
        if not valid:
            ax.text(
                0.5, 0.5, "No valid driving force data",
                transform=ax.transAxes, ha="center", va="center",
                color="white", fontsize=12,
            )
            self.figure.tight_layout()
            return

        phases = [p for p, _ in valid]
        values = [df for _, df in valid]
        labels = [translate_phase_short(p) for p in phases]
        colors = [_df_color(df) for df in values]

        y_pos = range(len(labels))
        ax.barh(y_pos, values, color=colors, edgecolor="#333333", height=0.6)
        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(labels, color="white", fontsize=9)
        ax.set_xlabel("Driving Force (J/mol)", color="white", fontsize=10)
        ax.set_title(
            f"Driving Force at {format_temp(temperature, show_both=False)}",
            color="white", fontsize=11, pad=10,
        )
        ax.tick_params(colors="white")
        ax.invert_yaxis()

        # Add threshold line
        threshold = self.threshold_spin.value()
        if threshold > 0:
            ax.axvline(
                x=threshold, color="#FFB74D", linestyle="--",
                linewidth=1, alpha=0.7, label=f"Threshold ({threshold:.0f} J/mol)",
            )
            ax.legend(
                loc="lower right", fontsize=8,
                facecolor="#1a1a2e", edgecolor="#555555",
                labelcolor="white",
            )

        for spine in ax.spines.values():
            spine.set_color("#555555")

        self.figure.tight_layout()

    def _show_point_summary(
        self,
        stable_phases: list[str],
        driving_forces: dict[str, float],
        temperature: float,
        threshold: float,
    ):
        """Build and display a plain-English summary for point mode."""
        temp_str = format_temp(temperature)
        n_stable = len(stable_phases)

        # Find phases near stability
        near_phases = [
            (p, df) for p, df in driving_forces.items()
            if not np.isnan(df) and df < threshold
        ]

        stable_names = ", ".join(
            f"{p} ({translate_phase_short(p)})" for p in stable_phases
        )

        if near_phases:
            nearest = min(near_phases, key=lambda x: x[1])
            nearest_name = f"{nearest[0]} ({translate_phase_short(nearest[0])})"
            summary = (
                f"At {temp_str}: {n_stable} stable phase(s): {stable_names}. "
                f"{nearest_name} is only {nearest[1]:.0f} J/mol from becoming "
                f"stable!"
            )
        else:
            summary = (
                f"At {temp_str}: {n_stable} stable phase(s): {stable_names}. "
                f"All metastable phases are far from stability "
                f"(> {threshold:.0f} J/mol)."
            )

        self.summary_label.setText(summary)
        self.summary_label.setVisible(True)

    def _show_warnings(
        self,
        driving_forces: dict[str, float],
        temperature: float,
        threshold: float,
    ):
        """Display near-stability warnings in the warning box."""
        near_phases = [
            (p, df) for p, df in driving_forces.items()
            if not np.isnan(df) and df < threshold
        ]

        if not near_phases:
            self.warning_label.setVisible(False)
            return

        near_phases.sort(key=lambda x: x[1])
        lines: list[str] = []
        for phase, df_val in near_phases:
            short = translate_phase_short(phase)
            full = translate_phase_name(phase)
            if df_val < 500:
                urgency = "CRITICAL"
            else:
                urgency = "WARNING"
            lines.append(
                f"[{urgency}] {phase} ({short}, {full}) is only "
                f"{df_val:.0f} J/mol from stability. Small changes in "
                f"temperature or composition could make this phase appear."
            )

        self.warning_label.setText("\n".join(lines))
        self.warning_label.setVisible(True)

    # ------------------------------------------------------- sweep results

    def _on_sweep_progress(self, pct: int):
        self.progress_bar.setValue(pct)

    def _on_sweep_finished(self, result: dict):
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(True)

        error = result.get("error")
        if error:
            friendly = _friendly_error(error)
            self.status_label.setText("Sweep calculation failed")
            self.status_label.setStyleSheet("color: #E57373;")
            QMessageBox.warning(
                self, "Calculation Did Not Succeed",
                f"{friendly}\n\n(Technical details below.)\n\n{error[-300:]}"
            )
            return

        self._last_sweep_result = result
        self._last_point_result = None

        temperatures = result["temperatures"]
        sweep_data = result["sweep_data"]
        threshold = self.threshold_spin.value()

        # --- Update table with summary per phase ---
        self.results_table.setRowCount(len(sweep_data))
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Phase", "Name", "Min DF (J/mol)", "Max DF (J/mol)", "Status",
        ])

        for i, (phase, df_values) in enumerate(sorted(sweep_data.items())):
            valid_dfs = [d for d in df_values if not np.isnan(d)]
            min_df = min(valid_dfs) if valid_dfs else float("nan")
            max_df = max(valid_dfs) if valid_dfs else float("nan")

            self.results_table.setItem(i, 0, QTableWidgetItem(phase))
            self.results_table.setItem(
                i, 1,
                QTableWidgetItem(
                    f"{translate_phase_short(phase)} - "
                    f"{translate_phase_name(phase)}"
                ),
            )
            if np.isnan(min_df):
                self.results_table.setItem(i, 2, QTableWidgetItem("N/A"))
                self.results_table.setItem(i, 3, QTableWidgetItem("N/A"))
            else:
                self.results_table.setItem(i, 2, QTableWidgetItem(f"{min_df:.1f}"))
                self.results_table.setItem(i, 3, QTableWidgetItem(f"{max_df:.1f}"))

            color = _df_color(min_df)
            if np.isnan(min_df):
                status = "No data"
            elif min_df < 500:
                status = "Near stability at some T!"
            elif min_df < 2000:
                status = "Approaching at some T"
            else:
                status = "Far from stable"
            item_status = QTableWidgetItem(status)
            self.results_table.setItem(i, 4, item_status)

            # Color the row
            for j in range(5):
                cell = self.results_table.item(i, j)
                if cell is not None:
                    cell.setForeground(QColor(color))

        # Smart column sizing
        n_cols = self.results_table.columnCount()
        if n_cols <= 8:
            self.results_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )
        else:
            self.results_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Interactive
            )
            self.results_table.horizontalHeader().setDefaultSectionSize(90)

        # --- Update chart (line plot) ---
        self._plot_sweep_lines(temperatures, sweep_data, threshold)
        self.canvas.draw()

        # --- Summary ---
        self._show_sweep_summary(temperatures, sweep_data, threshold)

        # --- Warnings ---
        self._show_sweep_warnings(temperatures, sweep_data, threshold)

        self.export_csv_btn.setEnabled(True)
        self.export_png_btn.setEnabled(True)
        self.status_label.setText(
            f"Sweep complete: {len(sweep_data)} metastable phases "
            f"over {len(temperatures)} temperature points"
        )
        self.status_label.setStyleSheet("color: #81C784;")

        # Emit signal for history logging
        elem_list = list({r.element_combo.currentText() for r in self.comp_rows})
        cond = {
            "T_min": temperatures[0],
            "T_max": temperatures[-1],
            "P": self.pressure_spin.value(),
        }
        summary_text = self.summary_label.text()
        self.calculation_done.emit(elem_list, cond, summary_text)

    def _plot_sweep_lines(
        self,
        temperatures: list[float],
        sweep_data: dict[str, list[float]],
        threshold: float,
    ):
        """Plot driving force vs temperature for all metastable phases."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor("#1a1a2e")

        if not sweep_data:
            ax.text(
                0.5, 0.5, "No metastable phase data",
                transform=ax.transAxes, ha="center", va="center",
                color="white", fontsize=12,
            )
            self.figure.tight_layout()
            return

        color_idx = 0
        for phase in sorted(sweep_data.keys()):
            df_values = sweep_data[phase]
            label = translate_phase_short(phase)
            color = PHASE_COLORS[color_idx % len(PHASE_COLORS)]
            color_idx += 1

            # Only plot if there is at least some valid data
            valid_count = sum(1 for d in df_values if not np.isnan(d))
            if valid_count < 2:
                continue

            ax.plot(
                temperatures, df_values,
                label=label, color=color, linewidth=1.5, alpha=0.85,
            )

        # Threshold line
        if threshold > 0:
            ax.axhline(
                y=threshold, color="#FFB74D", linestyle="--",
                linewidth=1, alpha=0.7,
                label=f"Threshold ({threshold:.0f} J/mol)",
            )

        ax.set_xlabel("Temperature (K)", color="white", fontsize=10)
        ax.set_ylabel("Driving Force (J/mol)", color="white", fontsize=10)
        ax.set_title(
            "Driving Force vs Temperature", color="white", fontsize=11, pad=10,
        )
        ax.tick_params(colors="white")
        handles, labels = ax.get_legend_handles_labels()
        if len(handles) <= 8:
            ax.legend(fontsize=8, loc="best", facecolor="#2d2d3e", edgecolor="#555555", labelcolor="white")
        else:
            ax.legend(fontsize=7, loc="center left", bbox_to_anchor=(1.02, 0.5),
                      facecolor="#2d2d3e", edgecolor="#555555", labelcolor="white", borderaxespad=0)

        for spine in ax.spines.values():
            spine.set_color("#555555")

        self.figure.tight_layout()

    def _show_sweep_summary(
        self,
        temperatures: list[float],
        sweep_data: dict[str, list[float]],
        threshold: float,
    ):
        """Build plain-English summary for sweep mode."""
        t_min_str = format_temp(temperatures[0])
        t_max_str = format_temp(temperatures[-1])

        # Find phases that dip below threshold
        dangerous: list[tuple[str, float, float]] = []
        for phase, df_values in sweep_data.items():
            valid = [(t, d) for t, d in zip(temperatures, df_values) if not np.isnan(d)]
            if not valid:
                continue
            min_pair = min(valid, key=lambda x: x[1])
            if min_pair[1] < threshold:
                dangerous.append((phase, min_pair[1], min_pair[0]))

        if dangerous:
            dangerous.sort(key=lambda x: x[1])
            nearest = dangerous[0]
            nearest_name = (
                f"{nearest[0]} ({translate_phase_short(nearest[0])})"
            )
            summary = (
                f"Sweep from {t_min_str} to {t_max_str}: "
                f"{len(dangerous)} metastable phase(s) approach stability. "
                f"{nearest_name} comes closest at {nearest[1]:.0f} J/mol "
                f"near {format_temp(nearest[2])}."
            )
        else:
            summary = (
                f"Sweep from {t_min_str} to {t_max_str}: "
                f"All metastable phases remain far from stability "
                f"(> {threshold:.0f} J/mol) across the entire range."
            )

        self.summary_label.setText(summary)
        self.summary_label.setVisible(True)

    def _show_sweep_warnings(
        self,
        temperatures: list[float],
        sweep_data: dict[str, list[float]],
        threshold: float,
    ):
        """Display sweep-mode warnings."""
        dangerous: list[tuple[str, float, float]] = []
        for phase, df_values in sweep_data.items():
            valid = [(t, d) for t, d in zip(temperatures, df_values) if not np.isnan(d)]
            if not valid:
                continue
            min_pair = min(valid, key=lambda x: x[1])
            if min_pair[1] < threshold:
                dangerous.append((phase, min_pair[1], min_pair[0]))

        if not dangerous:
            self.warning_label.setVisible(False)
            return

        dangerous.sort(key=lambda x: x[1])
        lines: list[str] = []
        for phase, df_val, t_at_min in dangerous:
            short = translate_phase_short(phase)
            full = translate_phase_name(phase)
            if df_val < 500:
                urgency = "CRITICAL"
            else:
                urgency = "WARNING"
            lines.append(
                f"[{urgency}] {phase} ({short}, {full}) reaches "
                f"{df_val:.0f} J/mol near {format_temp(t_at_min)}. "
                f"This phase may become stable under slight perturbation."
            )

        self.warning_label.setText("\n".join(lines))
        self.warning_label.setVisible(True)

    # -------------------------------------------------------- export CSV

    def _metadata_lines(self) -> list[str]:
        """Return comment lines describing the calculation conditions."""
        lines = [
            f"# Driving Force Analysis Results",
            f"# Generated: {datetime.datetime.now().isoformat(timespec='seconds')}",
            f"# Pressure: {self.pressure_spin.value():.0f} Pa",
        ]
        if self.sweep_check.isChecked():
            t_min, t_max, t_step = self._get_sweep_temps_k()
            lines.append(
                f"# Temperature sweep: {t_min:.0f} - {t_max:.0f} K, "
                f"step {t_step:.0f} K"
            )
        else:
            lines.append(
                f"# Temperature: {format_temp(self._get_temperature_k())}"
            )
        lines.append(f"# Warning threshold: {self.threshold_spin.value():.0f} J/mol")

        comp_parts = []
        for row in self.comp_rows:
            el = row.element_combo.currentText()
            val = row.composition_spin.value()
            if self._comp_unit == "weight_percent":
                comp_parts.append(f"{el}={val:.2f} wt%")
            else:
                comp_parts.append(f"{el}={val:.4f}")
        if comp_parts:
            lines.append(f"# Composition: {', '.join(comp_parts)}")
        return lines

    def _export_csv(self):
        if self._last_point_result is None and self._last_sweep_result is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Driving Force Data", "driving_force.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return

        meta = self._metadata_lines()

        try:
            with open(path, "w", newline="") as f:
                for line in meta:
                    f.write(line + "\n")

                if self._last_point_result is not None:
                    stable, dfs, temperature, _ = self._last_point_result
                    f.write(f"# Stable phases: {', '.join(stable)}\n#\n")
                    f.write("Phase,Name,DrivingForce_J_per_mol,Status\n")
                    for phase in sorted(dfs.keys()):
                        df_val = dfs[phase]
                        short = translate_phase_short(phase)
                        if np.isnan(df_val):
                            status = "N/A"
                            df_str = "NaN"
                        elif df_val < 500:
                            status = "Near stability"
                            df_str = f"{df_val:.1f}"
                        elif df_val < 2000:
                            status = "Approaching"
                            df_str = f"{df_val:.1f}"
                        else:
                            status = "Far from stable"
                            df_str = f"{df_val:.1f}"
                        f.write(f"{phase},{short},{df_str},{status}\n")

                elif self._last_sweep_result is not None:
                    temperatures = self._last_sweep_result["temperatures"]
                    sweep_data = self._last_sweep_result["sweep_data"]
                    phases = sorted(sweep_data.keys())
                    header = "Temperature_K," + ",".join(
                        f"{p}_J_per_mol" for p in phases
                    )
                    f.write(header + "\n")
                    for i, t in enumerate(temperatures):
                        row_vals = [f"{t:.1f}"]
                        for p in phases:
                            vals = sweep_data[p]
                            if i < len(vals):
                                df_val = vals[i]
                                row_vals.append(
                                    "NaN" if np.isnan(df_val) else f"{df_val:.1f}"
                                )
                            else:
                                row_vals.append("NaN")
                        f.write(",".join(row_vals) + "\n")

            self.status_label.setText(f"Exported to {path}")
        except Exception as exc:
            QMessageBox.critical(
                self, "Export Failed", f"Could not write CSV file:\n\n{exc}"
            )

    # -------------------------------------------------------- export PNG

    def _export_png(self):
        if not self.figure:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Driving Force Chart", "driving_force.png",
            "PNG Files (*.png);;All Files (*)",
        )
        if not path:
            return

        # Build conditions subtitle
        comp_parts = []
        for row in self.comp_rows:
            el = row.element_combo.currentText()
            val = row.composition_spin.value()
            if self._comp_unit == "weight_percent":
                comp_parts.append(f"{el}={val:.2f} wt%")
            else:
                comp_parts.append(f"{el}={val:.4f}")
        conditions = ", ".join(comp_parts)
        subtitle = f"P = {self.pressure_spin.value():.0f} Pa  |  {conditions}"

        annotation = self.figure.text(
            0.01, 0.01, subtitle,
            fontsize=7, color="#888888",
            transform=self.figure.transFigure,
            ha="left", va="bottom",
        )

        try:
            self.figure.savefig(
                path, dpi=150, facecolor="#1e1e2e", bbox_inches="tight",
            )
            self.status_label.setText(f"Exported to {path}")
        except Exception as exc:
            QMessageBox.critical(
                self, "Export Failed", f"Could not save PNG file:\n\n{exc}"
            )
        finally:
            annotation.remove()
            self.canvas.draw()
