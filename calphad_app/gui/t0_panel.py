"""T-Zero (T0) calculation panel.

T0 is the temperature where two phases have identical Gibbs energy at the
same composition.  It represents the theoretical thermodynamic limit for
diffusionless (martensitic) transformations.
"""

from __future__ import annotations

import csv
import datetime

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QProgressBar, QPushButton, QRadioButton, QSplitter,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from pycalphad import Database, calculate, variables as v

from core.presets import translate_phase_short
from core.units import k_to_c, c_to_k, format_temp, mole_to_weight, weight_to_mole
from gui.info_content import TAB_INFO

PHASE_COLORS = [
    "#4FC3F7", "#81C784", "#FFB74D", "#E57373", "#BA68C8",
    "#4DB6AC", "#FFD54F", "#7986CB", "#A1887F", "#90A4AE",
]


# ---------------------------------------------------------------------------
# T0 calculation logic
# ---------------------------------------------------------------------------

def find_t0(
    db: Database,
    elements: list[str],
    phase1: str,
    phase2: str,
    composition: dict[str, float],
    t_min: float = 200,
    t_max: float = 3000,
    tol: float = 0.5,
) -> float | None:
    """Find the T0 temperature where G(phase1) == G(phase2) via bisection.

    Parameters
    ----------
    db : Database
        Loaded pycalphad thermodynamic database.
    elements : list[str]
        Element symbols, e.g. ["FE", "C"].
    phase1, phase2 : str
        Phase names from the database (e.g. "FCC_A1", "BCC_A2").
    composition : dict[str, float]
        Mole-fraction conditions for the dependent component(s),
        e.g. {"C": 0.04}.  The balance element is inferred.
    t_min, t_max : float
        Temperature search window in Kelvin.
    tol : float
        Convergence tolerance in Kelvin.

    Returns
    -------
    float or None
        T0 temperature in Kelvin, or None if no sign change is detected.
    """
    comps = sorted({e.upper() for e in elements} | {"VA"})

    # Build the points dict for composition
    points_kwargs: dict = {}
    for el, xval in composition.items():
        points_kwargs[v.X(el.upper())] = xval

    def delta_g(T: float) -> float:
        """G(phase1) - G(phase2) at temperature T."""
        calc1 = calculate(
            db, comps, [phase1],
            T=float(T), P=101325, N=1, output="GM",
            **points_kwargs,
        )
        calc2 = calculate(
            db, comps, [phase2],
            T=float(T), P=101325, N=1, output="GM",
            **points_kwargs,
        )
        g1 = float(np.nanmin(calc1.GM.values))
        g2 = float(np.nanmin(calc2.GM.values))
        return g1 - g2

    dg_low = delta_g(t_min)
    dg_high = delta_g(t_max)

    if dg_low * dg_high > 0:
        return None  # No T0 in this range

    for _ in range(100):
        t_mid = (t_min + t_max) / 2.0
        dg_mid = delta_g(t_mid)
        if abs(dg_mid) < tol or (t_max - t_min) < tol:
            return t_mid
        if dg_low * dg_mid < 0:
            t_max = t_mid
        else:
            t_min = t_mid
            dg_low = dg_mid

    return (t_min + t_max) / 2.0


# ---------------------------------------------------------------------------
# Worker threads
# ---------------------------------------------------------------------------

class T0SingleWorker(QThread):
    """Worker for a single-point T0 calculation."""

    finished = pyqtSignal(object)  # float | None | str (error message)

    def __init__(self, db, elements, phase1, phase2, composition, t_min, t_max):
        super().__init__()
        self.db = db
        self.elements = elements
        self.phase1 = phase1
        self.phase2 = phase2
        self.composition = composition
        self.t_min = t_min
        self.t_max = t_max

    def run(self):
        try:
            result = find_t0(
                self.db, self.elements,
                self.phase1, self.phase2,
                self.composition,
                t_min=self.t_min, t_max=self.t_max,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.finished.emit(str(exc))


class T0SweepWorker(QThread):
    """Worker for a composition-sweep T0 calculation."""

    progress = pyqtSignal(int)           # percent 0-100
    finished = pyqtSignal(object, object)  # (x_values list, t0_values list)

    def __init__(
        self, db, elements, phase1, phase2,
        el2, x_min, x_max, x_step, t_min, t_max,
    ):
        super().__init__()
        self.db = db
        self.elements = elements
        self.phase1 = phase1
        self.phase2 = phase2
        self.el2 = el2
        self.x_min = x_min
        self.x_max = x_max
        self.x_step = x_step
        self.t_min = t_min
        self.t_max = t_max

    def run(self):
        x_values: list[float] = []
        t0_values: list[float | None] = []

        xs = np.arange(self.x_min, self.x_max + self.x_step / 2, self.x_step)
        total = len(xs)

        try:
            for i, x in enumerate(xs):
                composition = {self.el2: float(x)}
                t0 = find_t0(
                    self.db, self.elements,
                    self.phase1, self.phase2,
                    composition,
                    t_min=self.t_min, t_max=self.t_max,
                )
                x_values.append(float(x))
                t0_values.append(t0)
                self.progress.emit(int((i + 1) / total * 100))

            self.finished.emit(x_values, t0_values)
        except Exception as exc:
            self.finished.emit(str(exc), None)


# ---------------------------------------------------------------------------
# Panel widget
# ---------------------------------------------------------------------------

class T0Panel(QWidget):
    """Panel for T-zero (T0) calculations."""

    calculation_done = pyqtSignal(list, dict, str)  # (elements, conditions, summary)

    def __init__(self):
        super().__init__()
        self.db: Database | None = None
        self.elements: list[str] = []
        self.phases: list[str] = []
        self._worker: T0SingleWorker | T0SweepWorker | None = None
        self._last_x: list[float] = []
        self._last_t0: list[float | None] = []
        self._last_single_t0: float | None = None
        self._temp_unit: str = "K"
        self._comp_unit: str = "mole_fraction"
        self._setup_ui()

    # ------------------------------------------------------------------
    # Unit setters
    # ------------------------------------------------------------------

    def set_temp_unit(self, unit: str) -> None:
        """Set the temperature display unit ('K' or 'C')."""
        if unit == self._temp_unit:
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
        """Set the composition display unit ('mole_fraction' or 'weight_percent')."""
        if unit == self._comp_unit:
            return
        old_unit = self._comp_unit
        self._comp_unit = unit

        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()

        # Convert single-point spinbox
        self._convert_comp_spin(self.x_single_spin, el1, el2, old_unit, unit)

        # Convert sweep spinboxes
        for spin in (self.x_min_spin, self.x_max_spin, self.x_step_spin):
            self._convert_comp_spin(spin, el1, el2, old_unit, unit)

        # Update labels
        if unit == "weight_percent":
            label = f"wt%({el2})" if el2 else "wt%(El2)"
            self.x_single_label.setText(f"{label}:")
            self.x_min_label.setText(f"{label} min:")
            self.x_max_label.setText(f"{label} max:")
            self.x_step_label.setText(f"{label} step:")
        else:
            label = f"X({el2})" if el2 else "X(El2)"
            self.x_single_label.setText(f"{label}:")
            self.x_min_label.setText(f"{label} min:")
            self.x_max_label.setText(f"{label} max:")
            self.x_step_label.setText(f"{label} step:")

    def _convert_comp_spin(
        self, spin: QDoubleSpinBox,
        el1: str, el2: str,
        old_unit: str, new_unit: str,
    ) -> None:
        """Convert a composition spinbox value between units."""
        old_value = spin.value()
        spin.blockSignals(True)
        try:
            if new_unit == "weight_percent":
                if el1 and el2 and el1 != el2:
                    mole_dict = {el2: old_value, el1: 1.0 - old_value}
                    wt_dict = mole_to_weight(mole_dict)
                    spin.setRange(0.01, 99.99)
                    spin.setDecimals(2)
                    spin.setSingleStep(1.0)
                    spin.setValue(wt_dict.get(el2, old_value * 100))
                else:
                    spin.setRange(0.01, 99.99)
                    spin.setDecimals(2)
                    spin.setSingleStep(1.0)
                    spin.setValue(old_value * 100)
            else:
                if el1 and el2 and el1 != el2:
                    wt_dict = {el2: old_value, el1: 100.0 - old_value}
                    mole_dict = weight_to_mole(wt_dict)
                    spin.setRange(0.001, 0.999)
                    spin.setDecimals(4)
                    spin.setSingleStep(0.01)
                    spin.setValue(mole_dict.get(el2, old_value / 100))
                else:
                    spin.setRange(0.001, 0.999)
                    spin.setDecimals(4)
                    spin.setSingleStep(0.01)
                    spin.setValue(old_value / 100)
        finally:
            spin.blockSignals(False)

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # --- Title ---
        title = QLabel("T-Zero Calculator")
        title.setObjectName("heading")
        layout.addWidget(title)

        # --- Educational info panel ---
        info_data = TAB_INFO.get("t_zero", {})
        self.info_group = QGroupBox("What Is This? (click to expand)")
        self.info_group.setCheckable(True)
        self.info_group.setChecked(False)
        info_layout = QVBoxLayout()
        info_text = QLabel()
        info_text.setWordWrap(True)
        info_text.setTextFormat(Qt.TextFormat.RichText)
        info_text.setStyleSheet("color: #ccccdd; font-size: 13px; line-height: 1.5; padding: 8px;")
        simple = info_data.get("simple", "")
        analogy = info_data.get("analogy", "")
        tips = info_data.get("tips", [])
        tips_html = "".join(f"<li>{t}</li>" for t in tips)
        info_text.setText(
            f'<p style="color: #e0e0e0;">{simple}</p>'
            f'<p style="color: #81C784;"><b>Think of it like:</b> {analogy}</p>'
            f'<p style="color: #FFB74D;"><b>Tips:</b></p><ul>{tips_html}</ul>'
        )
        info_layout.addWidget(info_text)
        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)
        self.info_group.toggled.connect(lambda checked: [
            w.setVisible(checked) for w in [info_text]
        ])
        info_text.setVisible(False)

        # --- System group ---
        system_group = QGroupBox("System")
        system_layout = QHBoxLayout()

        system_layout.addWidget(QLabel("Element 1:"))
        self.el1_combo = QComboBox()
        self.el1_combo.setToolTip(
            "Primary (balance) element of the alloy. "
            "This is the solvent, e.g. FE in a steel."
        )
        system_layout.addWidget(self.el1_combo)

        system_layout.addWidget(QLabel("Element 2:"))
        self.el2_combo = QComboBox()
        self.el2_combo.setToolTip(
            "Secondary (solute) element whose mole fraction is varied."
        )
        system_layout.addWidget(self.el2_combo)

        system_group.setLayout(system_layout)
        layout.addWidget(system_group)

        # --- Phase selection group ---
        phase_group = QGroupBox("Phase Selection")
        phase_layout = QHBoxLayout()

        phase_layout.addWidget(QLabel("Phase 1:"))
        self.phase1_combo = QComboBox()
        self.phase1_combo.setToolTip(
            "First phase for the T0 comparison (e.g. FCC_A1)."
        )
        phase_layout.addWidget(self.phase1_combo)

        phase_layout.addWidget(QLabel("Phase 2:"))
        self.phase2_combo = QComboBox()
        self.phase2_combo.setToolTip(
            "Second phase for the T0 comparison (e.g. BCC_A2)."
        )
        phase_layout.addWidget(self.phase2_combo)

        phase_group.setLayout(phase_layout)
        layout.addWidget(phase_group)

        # --- Calculation mode group ---
        mode_group = QGroupBox("Calculation Mode")
        mode_layout = QVBoxLayout()

        # Radio buttons
        radio_row = QHBoxLayout()
        self.single_radio = QRadioButton("Single point")
        self.single_radio.setChecked(True)
        self.single_radio.setToolTip(
            "Calculate T0 at a single composition."
        )
        self.single_radio.toggled.connect(self._on_mode_changed)
        radio_row.addWidget(self.single_radio)

        self.sweep_radio = QRadioButton("T0 line (sweep composition)")
        self.sweep_radio.setToolTip(
            "Sweep across a range of compositions to compute the full T0 line."
        )
        radio_row.addWidget(self.sweep_radio)
        radio_row.addStretch()
        mode_layout.addLayout(radio_row)

        # Single-point composition
        self.single_row = QHBoxLayout()
        self.x_single_label = QLabel("X(El2):")
        self.single_row.addWidget(self.x_single_label)
        self.x_single_spin = QDoubleSpinBox()
        self.x_single_spin.setRange(0.001, 0.999)
        self.x_single_spin.setDecimals(4)
        self.x_single_spin.setSingleStep(0.01)
        self.x_single_spin.setValue(0.10)
        self.x_single_spin.setToolTip(
            "Mole fraction of the second element for the T0 calculation."
        )
        self.single_row.addWidget(self.x_single_spin)
        self.single_row.addStretch()

        self.single_widget = QWidget()
        self.single_widget.setLayout(self.single_row)
        mode_layout.addWidget(self.single_widget)

        # Sweep composition range
        self.sweep_row = QHBoxLayout()

        self.x_min_label = QLabel("X(El2) min:")
        self.sweep_row.addWidget(self.x_min_label)
        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(0.001, 0.999)
        self.x_min_spin.setDecimals(4)
        self.x_min_spin.setSingleStep(0.01)
        self.x_min_spin.setValue(0.01)
        self.sweep_row.addWidget(self.x_min_spin)

        self.x_max_label = QLabel("X(El2) max:")
        self.sweep_row.addWidget(self.x_max_label)
        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(0.001, 0.999)
        self.x_max_spin.setDecimals(4)
        self.x_max_spin.setSingleStep(0.01)
        self.x_max_spin.setValue(0.30)
        self.sweep_row.addWidget(self.x_max_spin)

        self.x_step_label = QLabel("X(El2) step:")
        self.sweep_row.addWidget(self.x_step_label)
        self.x_step_spin = QDoubleSpinBox()
        self.x_step_spin.setRange(0.001, 0.500)
        self.x_step_spin.setDecimals(4)
        self.x_step_spin.setSingleStep(0.005)
        self.x_step_spin.setValue(0.01)
        self.sweep_row.addWidget(self.x_step_spin)

        self.sweep_widget = QWidget()
        self.sweep_widget.setLayout(self.sweep_row)
        self.sweep_widget.setVisible(False)
        mode_layout.addWidget(self.sweep_widget)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # --- Search range group ---
        range_group = QGroupBox("Search Range")
        range_layout = QHBoxLayout()

        self.t_min_label = QLabel("T min (K):")
        range_layout.addWidget(self.t_min_label)
        self.t_min_spin = QDoubleSpinBox()
        self.t_min_spin.setRange(100, 5000)
        self.t_min_spin.setValue(200)
        self.t_min_spin.setSingleStep(50)
        self.t_min_spin.setToolTip(
            "Lower bound of the temperature search window in Kelvin."
        )
        range_layout.addWidget(self.t_min_spin)

        self.t_max_label = QLabel("T max (K):")
        range_layout.addWidget(self.t_max_label)
        self.t_max_spin = QDoubleSpinBox()
        self.t_max_spin.setRange(100, 5000)
        self.t_max_spin.setValue(3000)
        self.t_max_spin.setSingleStep(50)
        self.t_max_spin.setToolTip(
            "Upper bound of the temperature search window in Kelvin."
        )
        range_layout.addWidget(self.t_max_spin)

        range_group.setLayout(range_layout)
        layout.addWidget(range_group)

        # --- Buttons ---
        btn_layout = QHBoxLayout()

        self.calc_btn = QPushButton("Calculate T0")
        self.calc_btn.setObjectName("primary")
        self.calc_btn.setEnabled(False)
        self.calc_btn.setToolTip(
            "Load a database with at least 2 elements first"
        )
        self.calc_btn.clicked.connect(self._calculate)
        btn_layout.addWidget(self.calc_btn)

        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.setObjectName("success")
        self.export_csv_btn.setEnabled(False)
        self.export_csv_btn.setToolTip(
            "Save the T0 results to a CSV file."
        )
        self.export_csv_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(self.export_csv_btn)

        self.export_png_btn = QPushButton("Export PNG")
        self.export_png_btn.setObjectName("success")
        self.export_png_btn.setEnabled(False)
        self.export_png_btn.setToolTip(
            "Save the T0 plot as a PNG image."
        )
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

        # --- Single-point result label ---
        self.result_label = QLabel("")
        self.result_label.setStyleSheet(
            "color: #F06292; font-size: 18px; font-weight: bold; "
            "padding: 8px 12px; background: #2a2a3c; border-radius: 6px;"
        )
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setVisible(False)
        layout.addWidget(self.result_label)

        # --- Summary label ---
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet(
            "color: #E0E0E0; font-size: 12px; padding: 4px 6px; "
            "background: #2a2a3c; border-radius: 4px;"
        )
        self.summary_label.setWordWrap(True)
        self.summary_label.setVisible(False)
        layout.addWidget(self.summary_label)

        # --- Sweep results: splitter with table + plot ---
        self.results_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.results_splitter.setVisible(False)

        # Table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(2)
        self.results_table.setHorizontalHeaderLabels(["X(El2)", "T0 (K)"])
        self.results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.results_table.setAlternatingRowColors(True)
        self.results_splitter.addWidget(self.results_table)

        # Plot
        self.figure = Figure(figsize=(6, 4), dpi=100)
        self.figure.patch.set_facecolor("#1e1e2e")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(350)
        self.results_splitter.addWidget(self.canvas)

        self.results_splitter.setSizes([300, 500])
        layout.addWidget(self.results_splitter, stretch=1)

        # Connect element combos to update composition labels
        self.el2_combo.currentTextChanged.connect(self._on_element_changed)

    # ------------------------------------------------------------------
    # Mode toggle
    # ------------------------------------------------------------------

    def _on_mode_changed(self, checked: bool) -> None:
        """Toggle between single-point and sweep UI."""
        is_single = self.single_radio.isChecked()
        self.single_widget.setVisible(is_single)
        self.sweep_widget.setVisible(not is_single)

    # ------------------------------------------------------------------
    # Element changed
    # ------------------------------------------------------------------

    def _on_element_changed(self) -> None:
        """Update composition labels when element selection changes."""
        el2 = self.el2_combo.currentText()
        if not el2:
            return
        if self._comp_unit == "weight_percent":
            label = f"wt%({el2})"
        else:
            label = f"X({el2})"
        self.x_single_label.setText(f"{label}:")
        self.x_min_label.setText(f"{label} min:")
        self.x_max_label.setText(f"{label} max:")
        self.x_step_label.setText(f"{label} step:")

    # ------------------------------------------------------------------
    # Database update
    # ------------------------------------------------------------------

    def update_database(self, db: Database, elements: list[str], phases: list[str]):
        """Called when a new database is loaded."""
        self.db = db
        self.elements = elements
        self.phases = phases

        # Populate element combos
        self.el1_combo.blockSignals(True)
        self.el2_combo.blockSignals(True)

        self.el1_combo.clear()
        self.el2_combo.clear()
        self.el1_combo.addItems(elements)
        self.el2_combo.addItems(elements)

        if len(elements) >= 2:
            self.el2_combo.setCurrentIndex(1)
            self.calc_btn.setEnabled(True)
            self.calc_btn.setToolTip(
                "Compute the T0 temperature where two phases have "
                "equal Gibbs energy at the specified composition."
            )

        self.el1_combo.blockSignals(False)
        self.el2_combo.blockSignals(False)

        # Populate phase combos
        self.phase1_combo.blockSignals(True)
        self.phase2_combo.blockSignals(True)

        self.phase1_combo.clear()
        self.phase2_combo.clear()

        phase_labels = []
        for ph in phases:
            short = translate_phase_short(ph)
            display = f"{ph} ({short})" if short != ph else ph
            phase_labels.append((ph, display))

        for _ph, display in phase_labels:
            self.phase1_combo.addItem(display, _ph)
            self.phase2_combo.addItem(display, _ph)

        # Try to default to FCC / BCC if available
        phase_upper = [p.upper() for p in phases]
        fcc_idx = next(
            (i for i, p in enumerate(phase_upper) if "FCC" in p), 0
        )
        bcc_idx = next(
            (i for i, p in enumerate(phase_upper) if "BCC" in p),
            min(1, len(phases) - 1),
        )
        self.phase1_combo.setCurrentIndex(fcc_idx)
        self.phase2_combo.setCurrentIndex(bcc_idx)

        self.phase1_combo.blockSignals(False)
        self.phase2_combo.blockSignals(False)

        # Update element labels
        self._on_element_changed()

    # ------------------------------------------------------------------
    # Calculation
    # ------------------------------------------------------------------

    def _calculate(self) -> None:
        if not self.db:
            return

        if self._worker is not None and self._worker.isRunning():
            return

        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()

        if el1 == el2:
            QMessageBox.warning(
                self, "Same Element Selected",
                "Please select two different elements."
            )
            return

        phase1 = self.phase1_combo.currentData()
        phase2 = self.phase2_combo.currentData()

        if phase1 == phase2:
            QMessageBox.warning(
                self, "Same Phase Selected",
                "Please select two different phases for the T0 calculation."
            )
            return

        t_min = self.t_min_spin.value()
        t_max = self.t_max_spin.value()
        if self._temp_unit == "C":
            t_min = c_to_k(t_min)
            t_max = c_to_k(t_max)

        if t_min >= t_max:
            QMessageBox.warning(
                self, "Temperature Range Issue",
                "The minimum temperature must be lower than the maximum."
            )
            return

        elements = [el1, el2]

        # Reset result displays
        self.result_label.setVisible(False)
        self.results_splitter.setVisible(False)
        self.summary_label.setVisible(False)
        self.export_csv_btn.setEnabled(False)
        self.export_png_btn.setEnabled(False)

        self.calc_btn.setEnabled(False)
        self.status_label.setStyleSheet("color: #FFB74D;")

        if self.single_radio.isChecked():
            # --- Single point ---
            x_val = self.x_single_spin.value()
            if self._comp_unit == "weight_percent":
                wt_dict = {el2: x_val, el1: 100.0 - x_val}
                mole_dict = weight_to_mole(wt_dict)
                x_val = mole_dict.get(el2, x_val / 100)

            composition = {el2: x_val}

            self.progress_bar.setRange(0, 0)  # indeterminate
            self.progress_bar.setVisible(True)
            self.status_label.setText("Computing T0... This may take a moment.")

            self._worker = T0SingleWorker(
                self.db, elements, phase1, phase2,
                composition, t_min, t_max,
            )
            self._worker.finished.connect(self._on_single_finished)
            self._worker.start()

        else:
            # --- Sweep ---
            x_min_val = self.x_min_spin.value()
            x_max_val = self.x_max_spin.value()
            x_step_val = self.x_step_spin.value()

            if self._comp_unit == "weight_percent":
                # Convert sweep bounds from wt% to mole fraction
                wt_min = {el2: x_min_val, el1: 100.0 - x_min_val}
                wt_max = {el2: x_max_val, el1: 100.0 - x_max_val}
                x_min_val = weight_to_mole(wt_min).get(el2, x_min_val / 100)
                x_max_val = weight_to_mole(wt_max).get(el2, x_max_val / 100)
                # Approximate step conversion
                x_step_val = (x_max_val - x_min_val) / max(
                    1, round((self.x_max_spin.value() - self.x_min_spin.value())
                             / self.x_step_spin.value())
                )

            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
            self.status_label.setText("Computing T0 line... Sweeping compositions.")

            self._worker = T0SweepWorker(
                self.db, elements, phase1, phase2,
                el2, x_min_val, x_max_val, x_step_val,
                t_min, t_max,
            )
            self._worker.progress.connect(self.progress_bar.setValue)
            self._worker.finished.connect(self._on_sweep_finished)
            self._worker.start()

    # ------------------------------------------------------------------
    # Result handlers
    # ------------------------------------------------------------------

    def _on_single_finished(self, result) -> None:
        """Handle single-point T0 result."""
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(True)

        phase1 = self.phase1_combo.currentData()
        phase2 = self.phase2_combo.currentData()
        el2 = self.el2_combo.currentText()
        x_val = self.x_single_spin.value()

        p1_short = translate_phase_short(phase1)
        p2_short = translate_phase_short(phase2)

        if isinstance(result, str):
            # Error
            self.status_label.setText("Calculation failed")
            self.status_label.setStyleSheet("color: #E57373;")
            QMessageBox.critical(
                self, "T0 Calculation Failed",
                f"The T0 calculation encountered an error:\n\n{result}\n\n"
                "Try adjusting the temperature range or composition."
            )
            return

        self._last_single_t0 = result

        if result is None:
            self.result_label.setText(
                f"No T0 found for {p1_short}/{p2_short} in the search range"
            )
            self.result_label.setStyleSheet(
                "color: #FFB74D; font-size: 16px; font-weight: bold; "
                "padding: 8px 12px; background: #2a2a3c; border-radius: 6px;"
            )
            self.result_label.setVisible(True)
            self.status_label.setText("No sign change detected in search range")
            self.status_label.setStyleSheet("color: #FFB74D;")

            summary = (
                f"No T0 temperature was found for {p1_short}/{p2_short} "
                f"at X({el2}) = {x_val:.4f} within the search range. "
                "The Gibbs energies of the two phases may not cross in this "
                "temperature window. Try widening the search range."
            )
            self.summary_label.setText(summary)
            self.summary_label.setVisible(True)
            return

        t0_c = k_to_c(result)
        self.result_label.setText(
            f"T0({p1_short}/{p2_short}) = {result:.1f} K ({t0_c:.1f} \u00b0C)"
        )
        self.result_label.setStyleSheet(
            "color: #F06292; font-size: 18px; font-weight: bold; "
            "padding: 8px 12px; background: #2a2a3c; border-radius: 6px;"
        )
        self.result_label.setVisible(True)

        comp_str = (
            f"wt%({el2}) = {x_val:.2f}"
            if self._comp_unit == "weight_percent"
            else f"X({el2}) = {x_val:.4f}"
        )
        summary = (
            f"T0({p1_short}/{p2_short}) = {result:.1f} K ({t0_c:.1f} \u00b0C) "
            f"at {comp_str}"
        )
        self.summary_label.setText(summary)
        self.summary_label.setVisible(True)

        self.status_label.setText("T0 calculation complete")
        self.status_label.setStyleSheet("color: #81C784;")

        self.export_csv_btn.setEnabled(True)

        # Emit for history
        cond = {"T0": result, "X": x_val, "phase1": phase1, "phase2": phase2}
        self.calculation_done.emit(
            [self.el1_combo.currentText(), el2], cond, summary,
        )

    def _on_sweep_finished(self, x_values, t0_values) -> None:
        """Handle sweep T0 result."""
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(True)

        if isinstance(x_values, str):
            # Error
            self.status_label.setText("Calculation failed")
            self.status_label.setStyleSheet("color: #E57373;")
            QMessageBox.critical(
                self, "T0 Sweep Failed",
                f"The T0 sweep encountered an error:\n\n{x_values}\n\n"
                "Try adjusting the temperature range or composition bounds."
            )
            return

        self._last_x = x_values
        self._last_t0 = t0_values

        phase1 = self.phase1_combo.currentData()
        phase2 = self.phase2_combo.currentData()
        el2 = self.el2_combo.currentText()

        p1_short = translate_phase_short(phase1)
        p2_short = translate_phase_short(phase2)

        # Filter valid (non-None) results
        valid_x = [x for x, t in zip(x_values, t0_values) if t is not None]
        valid_t0 = [t for t in t0_values if t is not None]

        # Populate table
        self.results_table.setRowCount(len(x_values))
        self.results_table.setHorizontalHeaderLabels(
            [f"X({el2})", "T0 (K)"]
        )
        for row, (x, t0) in enumerate(zip(x_values, t0_values)):
            x_item = QTableWidgetItem(f"{x:.4f}")
            x_item.setFlags(x_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(row, 0, x_item)

            t0_str = f"{t0:.1f}" if t0 is not None else "N/A"
            t0_item = QTableWidgetItem(t0_str)
            t0_item.setFlags(t0_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.results_table.setItem(row, 1, t0_item)

        # Plot
        self._plot_t0_line(valid_x, valid_t0, el2, p1_short, p2_short)
        self.results_splitter.setVisible(True)

        # Summary
        n_total = len(x_values)
        n_valid = len(valid_t0)

        if n_valid > 0:
            t0_min = min(valid_t0)
            t0_max = max(valid_t0)
            summary = (
                f"T0 line computed for {n_total} compositions "
                f"({n_valid} with valid T0). "
                f"T0 ranges from {t0_min:.0f} to {t0_max:.0f} K."
            )
            self.status_label.setText(
                f"T0 sweep complete: {n_valid}/{n_total} points found"
            )
            self.status_label.setStyleSheet("color: #81C784;")
        else:
            summary = (
                f"T0 line computed for {n_total} compositions "
                "but no valid T0 was found at any point. "
                "Try widening the temperature search range."
            )
            self.status_label.setText("No T0 found at any composition")
            self.status_label.setStyleSheet("color: #FFB74D;")

        self.summary_label.setText(summary)
        self.summary_label.setVisible(True)

        self.export_csv_btn.setEnabled(n_valid > 0)
        self.export_png_btn.setEnabled(n_valid > 0)

        # Emit for history
        cond = {
            "X_min": x_values[0] if x_values else 0,
            "X_max": x_values[-1] if x_values else 0,
            "phase1": phase1,
            "phase2": phase2,
        }
        self.calculation_done.emit(
            [self.el1_combo.currentText(), el2], cond, summary,
        )

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def _plot_t0_line(
        self,
        x_values: list[float],
        t0_values: list[float],
        el2: str,
        p1_label: str,
        p2_label: str,
    ) -> None:
        """Plot the T0 line on the matplotlib figure."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        ax.set_facecolor("#1e1e2e")
        ax.tick_params(colors="white")
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.title.set_color("white")
        for spine in ax.spines.values():
            spine.set_color("#555555")

        if not x_values or not t0_values:
            ax.text(
                0.5, 0.5, "No valid T0 data",
                transform=ax.transAxes, ha="center", va="center",
                color="#FFB74D", fontsize=14,
            )
            self.canvas.draw()
            return

        ax.plot(
            x_values, t0_values,
            color="#F06292", linewidth=2, marker="o",
            markersize=4, markerfacecolor="#F06292",
            markeredgecolor="white", markeredgewidth=0.5,
            label=f"T0 ({p1_label}/{p2_label})",
        )

        ax.set_xlabel(f"X({el2})", fontsize=11)
        ax.set_ylabel("T0 (K)", fontsize=11, color="#F06292")
        ax.set_title(
            f"T0 Line: {p1_label} / {p2_label}",
            fontsize=13, fontweight="bold",
        )

        ax.grid(True, color="#555555", alpha=0.2, linestyle="--")
        ax.legend(
            facecolor="#2a2a3c", edgecolor="#555555",
            labelcolor="white", fontsize=9,
        )

        # Secondary Celsius axis on the right
        ax2 = ax.twinx()
        ax2.set_facecolor("#1e1e2e")
        ax2.tick_params(colors="#90CAF9")
        ax2.yaxis.label.set_color("#90CAF9")

        y_min, y_max = ax.get_ylim()
        ax2.set_ylim(k_to_c(y_min), k_to_c(y_max))
        ax2.set_ylabel("T0 (\u00b0C)", fontsize=11, color="#90CAF9")
        for spine in ax2.spines.values():
            spine.set_color("#555555")

        self.figure.tight_layout()
        self.canvas.draw()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_conditions_text(self) -> str:
        """Build a human-readable string of the current calculation conditions."""
        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()
        phase1 = self.phase1_combo.currentData() or ""
        phase2 = self.phase2_combo.currentData() or ""
        t_min = self.t_min_spin.value()
        t_max = self.t_max_spin.value()
        if self._temp_unit == "C":
            t_min = c_to_k(t_min)
            t_max = c_to_k(t_max)

        mode = "single" if self.single_radio.isChecked() else "sweep"
        return (
            f"T0 Calculation  |  System: {el1}-{el2}  |  "
            f"Phases: {phase1} / {phase2}  |  Mode: {mode}  |  "
            f"Search: {t_min:.0f}-{t_max:.0f} K"
        )

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_csv(self) -> None:
        """Export T0 results to a CSV file."""
        is_single = self.single_radio.isChecked()

        default_name = "t0_single.csv" if is_single else "t0_sweep.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export T0 Data", default_name,
            "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return

        conditions = self._build_conditions_text()
        el2 = self.el2_combo.currentText()

        try:
            with open(path, "w", newline="") as f:
                f.write(f"# CALPHAD T0 Calculation\n")
                f.write(f"# Exported: {datetime.datetime.now().isoformat()}\n")
                f.write(f"# {conditions}\n")
                f.write("#\n")

                writer = csv.writer(f)

                if is_single:
                    writer.writerow([f"X({el2})", "T0 (K)", "T0 (C)"])
                    x_val = self.x_single_spin.value()
                    if self._last_single_t0 is not None:
                        writer.writerow([
                            f"{x_val:.4f}",
                            f"{self._last_single_t0:.1f}",
                            f"{k_to_c(self._last_single_t0):.1f}",
                        ])
                else:
                    writer.writerow([f"X({el2})", "T0 (K)", "T0 (C)"])
                    for x, t0 in zip(self._last_x, self._last_t0):
                        if t0 is not None:
                            writer.writerow([
                                f"{x:.4f}", f"{t0:.1f}", f"{k_to_c(t0):.1f}",
                            ])
                        else:
                            writer.writerow([f"{x:.4f}", "N/A", "N/A"])

            self.status_label.setText(f"Exported to {path}")
            self.status_label.setStyleSheet("color: #81C784;")
        except Exception as exc:
            QMessageBox.critical(
                self, "Export Failed",
                f"Could not write CSV file:\n\n{exc}"
            )

    def _export_png(self) -> None:
        """Export the T0 plot as a PNG image."""
        if not self.figure.get_axes():
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export T0 Plot", "t0_line.png",
            "PNG Files (*.png);;All Files (*)"
        )
        if not path:
            return

        conditions = self._build_conditions_text()
        annotation = self.figure.text(
            0.01, 0.01, conditions,
            fontsize=7, color="#888888",
            transform=self.figure.transFigure,
            ha="left", va="bottom",
        )

        try:
            self.figure.savefig(
                path, dpi=150, facecolor="#1e1e2e",
                bbox_inches="tight",
            )
            self.status_label.setText(f"Exported to {path}")
            self.status_label.setStyleSheet("color: #81C784;")
        except Exception as exc:
            QMessageBox.critical(
                self, "Export Failed",
                f"Could not save PNG file:\n\n{exc}"
            )
        finally:
            annotation.remove()
            self.canvas.draw()
