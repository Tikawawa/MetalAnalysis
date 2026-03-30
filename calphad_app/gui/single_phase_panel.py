"""Single-phase property calculator panel.

Evaluates thermodynamic properties for individual phases WITHOUT equilibrium
solving.  Uses ``pycalphad.calculate()`` to sweep temperature at a fixed
composition, then overlays one curve per selected phase so users can compare
Gibbs-energy (or other property) landscapes and understand phase stability.
"""

from __future__ import annotations

import datetime
import io
import traceback

import numpy as np
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QProgressBar, QPushButton, QScrollArea, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)
from gui.lazy_canvas import LazyCanvas
from pycalphad import Database, calculate, variables as v

from core.presets import translate_phase_short
from core.units import k_to_c, c_to_k, format_temp
from gui.info_content import TAB_INFO, TOOLTIPS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHASE_COLORS: list[str] = [
    "#4FC3F7", "#81C784", "#FFB74D", "#E57373", "#BA68C8",
    "#4DB6AC", "#FFD54F", "#7986CB", "#A1887F", "#90A4AE",
    "#F06292", "#AED581", "#64B5F6", "#FF8A65", "#CE93D8",
]

_PROPERTY_MAP: dict[str, str] = {
    "Gibbs Energy (GM)":   "GM",
    "Enthalpy (HM)":       "HM",
    "Entropy (SM)":        "SM",
    "Heat Capacity (CPM)": "CPM",
}

_PROPERTY_UNITS: dict[str, str] = {
    "GM":  "J / mol",
    "HM":  "J / mol",
    "SM":  "J / mol / K",
    "CPM": "J / mol / K",
}

# ---------------------------------------------------------------------------
# Friendly error helpers
# ---------------------------------------------------------------------------

_FRIENDLY_ERRORS: list[tuple[str, str]] = [
    ("Database",
     "There may be a problem with the thermodynamic database for this "
     "phase/element combination.  Check that all selected elements are "
     "covered by the loaded database."),
    ("singular matrix",
     "A numerical singularity was encountered.  Try a different composition "
     "or skip the offending phase."),
]


def _friendly_error(raw: str) -> str:
    import re
    for pattern, friendly in _FRIENDLY_ERRORS:
        if re.search(pattern, raw, re.IGNORECASE):
            return friendly
    return (
        "The single-phase calculation did not succeed for one or more phases.\n\n"
        "Suggestions:\n"
        "  - Check that every element is present in the database.\n"
        "  - Try reducing the number of selected phases.\n"
        "  - Verify the composition is within a physically meaningful range."
    )


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

class SinglePhaseWorker(QThread):
    """Compute a thermodynamic property vs temperature for each phase."""

    finished = pyqtSignal(object)          # dict payload
    progress_update = pyqtSignal(int, int)  # (current, total)

    def __init__(
        self,
        db: Database,
        comps: list[str],
        selected_phases: list[str],
        t_min: float,
        t_max: float,
        t_step: float,
        pressure: float,
        composition: dict[str, float],
        property_name: str,
    ):
        super().__init__()
        self.db = db
        self.comps = comps
        self.selected_phases = selected_phases
        self.t_min = t_min
        self.t_max = t_max
        self.t_step = t_step
        self.pressure = pressure
        self.composition = composition
        self.property_name = property_name

    def run(self):  # noqa: D401
        results: dict[str, np.ndarray | None] = {}
        temps = np.arange(
            self.t_min,
            self.t_max + self.t_step / 2.0,
            self.t_step,
        )
        errors: list[str] = []

        for i, phase in enumerate(self.selected_phases):
            self.progress_update.emit(i + 1, len(self.selected_phases))
            try:
                # Build the conditions dict for pycalphad.calculate
                cond = {v.T: temps, v.P: self.pressure, v.N: 1}
                for el, frac in self.composition.items():
                    cond[v.X(el)] = frac

                calc_result = calculate(
                    self.db,
                    self.comps,
                    [phase],
                    T=temps,
                    P=self.pressure,
                    N=1,
                    output=self.property_name,
                )

                prop_values = calc_result[self.property_name].values.squeeze()
                # Collapse internal degrees of freedom (points axis)
                if prop_values.ndim > 1:
                    prop_values = prop_values.min(axis=-1)
                results[phase] = prop_values
            except Exception:
                errors.append(f"{phase}: {traceback.format_exc()[-200:]}")
                results[phase] = None

        self.finished.emit({
            "temps": temps,
            "results": results,
            "property": self.property_name,
            "errors": errors,
        })


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

class SinglePhasePanel(QWidget):
    """Panel for single-phase property calculations via pycalphad.calculate()."""

    calculation_done = pyqtSignal(list, dict, str)  # (elements, conditions, summary)

    def __init__(self):
        super().__init__()
        self.db: Database | None = None
        self.elements: list[str] = []
        self.phases: list[str] = []
        self._worker: SinglePhaseWorker | None = None
        self._last_payload: dict | None = None
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

        # Title
        title = QLabel("Single-Phase Calculator")
        title.setObjectName("heading")
        layout.addWidget(title)

        # --- Educational info panel ---
        info_data = TAB_INFO.get("single_phase", {})
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

        # --- Elements ---
        el_group = QGroupBox("Elements")
        el_layout = QHBoxLayout()

        el_layout.addWidget(QLabel("Element 1:"))
        self.el1_combo = QComboBox()
        self.el1_combo.setToolTip("Base element of the binary system.")
        el_layout.addWidget(self.el1_combo)

        el_layout.addWidget(QLabel("Element 2:"))
        self.el2_combo = QComboBox()
        self.el2_combo.setToolTip("Second element -- composition axis.")
        el_layout.addWidget(self.el2_combo)

        el_layout.addStretch()
        el_group.setLayout(el_layout)
        layout.addWidget(el_group)

        # --- Phase Selection ---
        phase_group = QGroupBox("Phase Selection")
        phase_layout = QVBoxLayout()

        btn_row = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all_phases)
        btn_row.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self._deselect_all_phases)
        btn_row.addWidget(self.deselect_all_btn)

        self.select_common_btn = QPushButton("Select Common")
        self.select_common_btn.setToolTip(
            "Select only the most common phases: LIQUID, FCC (aluminum/copper), "
            "BCC (iron/steel), HCP (titanium/magnesium). These are the phases "
            "you'll encounter most often."
        )
        self.select_common_btn.clicked.connect(self._select_common_phases)
        btn_row.addWidget(self.select_common_btn)

        btn_row.addStretch()
        self.phase_counter_label = QLabel("0 phases selected")
        btn_row.addWidget(self.phase_counter_label)
        phase_layout.addLayout(btn_row)

        self.phase_list = QListWidget()
        self.phase_list.setToolTip(TOOLTIPS["sp_phase_list"])
        self.phase_list.itemChanged.connect(self._update_phase_counter)
        phase_layout.addWidget(self.phase_list)

        phase_group.setLayout(phase_layout)
        layout.addWidget(phase_group)

        # --- Composition ---
        comp_group = QGroupBox("Composition")
        comp_layout = QHBoxLayout()

        self.comp_label = QLabel("X(El2) =")
        comp_layout.addWidget(self.comp_label)

        self.comp_spin = QDoubleSpinBox()
        self.comp_spin.setRange(0.001, 0.999)
        self.comp_spin.setDecimals(4)
        self.comp_spin.setSingleStep(0.01)
        self.comp_spin.setValue(0.5)
        self.comp_spin.setToolTip(
            "Mole fraction of Element 2 (0.001 -- 0.999). "
            "The balance is Element 1."
        )
        comp_layout.addWidget(self.comp_spin)

        comp_layout.addStretch()
        comp_group.setLayout(comp_layout)
        layout.addWidget(comp_group)

        # --- Temperature Range ---
        temp_group = QGroupBox("Temperature Range")
        temp_layout = QHBoxLayout()

        self.t_min_label = QLabel("T min (K):")
        temp_layout.addWidget(self.t_min_label)
        self.t_min_spin = QDoubleSpinBox()
        self.t_min_spin.setRange(100, 5000)
        self.t_min_spin.setValue(300)
        self.t_min_spin.setSingleStep(50)
        temp_layout.addWidget(self.t_min_spin)

        self.t_max_label = QLabel("T max (K):")
        temp_layout.addWidget(self.t_max_label)
        self.t_max_spin = QDoubleSpinBox()
        self.t_max_spin.setRange(100, 5000)
        self.t_max_spin.setValue(2000)
        self.t_max_spin.setSingleStep(50)
        temp_layout.addWidget(self.t_max_spin)

        temp_layout.addWidget(QLabel("T step (K):"))
        self.t_step_spin = QDoubleSpinBox()
        self.t_step_spin.setRange(1, 500)
        self.t_step_spin.setValue(10)
        self.t_step_spin.setSingleStep(5)
        temp_layout.addWidget(self.t_step_spin)

        temp_layout.addStretch()
        temp_group.setLayout(temp_layout)
        layout.addWidget(temp_group)

        # --- Property ---
        prop_group = QGroupBox("Property")
        prop_layout = QHBoxLayout()

        self.property_combo = QComboBox()
        self.property_combo.addItems(list(_PROPERTY_MAP.keys()))
        self.property_combo.setToolTip(
            "Thermodynamic property to evaluate for each phase.\n"
            "GM = Gibbs energy, HM = enthalpy, SM = entropy, CPM = heat capacity."
        )
        prop_layout.addWidget(self.property_combo)
        prop_layout.addStretch()

        prop_group.setLayout(prop_layout)
        layout.addWidget(prop_group)

        # --- Buttons ---
        btn_layout = QHBoxLayout()

        self.calc_btn = QPushButton("Calculate")
        self.calc_btn.setObjectName("primary")
        self.calc_btn.setEnabled(False)
        self.calc_btn.setToolTip(
            "Compute the selected property vs temperature for every checked phase."
        )
        self.calc_btn.clicked.connect(self._calculate)
        btn_layout.addWidget(self.calc_btn)

        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.setObjectName("success")
        self.export_csv_btn.setEnabled(False)
        self.export_csv_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(self.export_csv_btn)

        self.export_png_btn = QPushButton("Export PNG")
        self.export_png_btn.setObjectName("success")
        self.export_png_btn.setEnabled(False)
        self.export_png_btn.clicked.connect(self._export_png)
        btn_layout.addWidget(self.export_png_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # --- Progress / status / summary ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

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

        # --- Results: chart + table ---
        self.canvas = LazyCanvas(figsize=(7, 4), dpi=100)
        self.canvas.setMinimumHeight(320)
        layout.addWidget(self.canvas, stretch=2)

        self.results_table = QTableWidget()
        self.results_table.setMinimumHeight(150)
        self.results_table.setToolTip(
            "Tabular results: one column per phase, rows are temperature steps."
        )
        layout.addWidget(self.results_table, stretch=1)

        scroll.setWidget(container)
        outer.addWidget(scroll)

    # -------------------------------------------------------- unit setters

    def set_temp_unit(self, unit: str):
        """Switch the temperature inputs between 'K' and 'C'."""
        if unit not in ("K", "C") or unit == self._temp_unit:
            return

        old_min = self.t_min_spin.value()
        old_max = self.t_max_spin.value()
        self._temp_unit = unit

        if unit == "C":
            self.t_min_label.setText("T min (C):")
            self.t_max_label.setText("T max (C):")
            self.t_min_spin.setRange(-173, 4727)
            self.t_max_spin.setRange(-173, 4727)
            self.t_min_spin.setValue(k_to_c(old_min))
            self.t_max_spin.setValue(k_to_c(old_max))
        else:
            self.t_min_label.setText("T min (K):")
            self.t_max_label.setText("T max (K):")
            self.t_min_spin.setRange(100, 5000)
            self.t_max_spin.setRange(100, 5000)
            self.t_min_spin.setValue(c_to_k(old_min))
            self.t_max_spin.setValue(c_to_k(old_max))

    def set_comp_unit(self, unit: str):
        """Switch composition between 'mole_fraction' and 'weight_percent'."""
        if unit not in ("mole_fraction", "weight_percent"):
            return
        if unit == self._comp_unit:
            return

        old_val = self.comp_spin.value()
        self._comp_unit = unit

        if unit == "weight_percent":
            self.comp_label.setText("wt%(El2) =")
            self.comp_spin.setRange(0.01, 99.99)
            self.comp_spin.setDecimals(2)
            self.comp_spin.setSingleStep(0.5)
            # Rough conversion -- accurate conversion needs atomic weights
            self.comp_spin.setValue(min(99.99, max(0.01, old_val * 100.0)))
        else:
            self.comp_label.setText("X(El2) =")
            self.comp_spin.setRange(0.001, 0.999)
            self.comp_spin.setDecimals(4)
            self.comp_spin.setSingleStep(0.01)
            self.comp_spin.setValue(min(0.999, max(0.001, old_val / 100.0)))

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

    def update_database(self, db: Database, elements: list[str], phases: list[str]):
        """Populate combos and phase list after a database is loaded."""
        self.db = db
        self.elements = elements
        self.phases = phases

        # Element combos
        self.el1_combo.blockSignals(True)
        self.el2_combo.blockSignals(True)
        self.el1_combo.clear()
        self.el2_combo.clear()
        self.el1_combo.addItems(elements)
        self.el2_combo.addItems(elements)
        if len(elements) >= 2:
            self.el1_combo.setCurrentIndex(0)
            self.el2_combo.setCurrentIndex(1)
        self.el1_combo.blockSignals(False)
        self.el2_combo.blockSignals(False)

        # Phase list
        self.phase_list.blockSignals(True)
        self.phase_list.clear()
        # Common phases to auto-check (user-friendly defaults)
        _COMMON_PHASES = {"LIQUID", "FCC_A1", "BCC_A2", "HCP_A3", "BCC_B2",
                          "DIAMOND_A4", "CEMENTITE", "AL2CU", "MG2SI"}
        for phase in phases:
            short = translate_phase_short(phase)
            label = f"{phase}  ({short})" if short != phase else phase
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, phase)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if phase in _COMMON_PHASES:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            self.phase_list.addItem(item)
        self.phase_list.blockSignals(False)
        self._update_phase_counter()

        self.calc_btn.setEnabled(len(elements) >= 2 and len(phases) >= 1)

        # Update composition label
        if len(elements) >= 2:
            el2 = self.el2_combo.currentText()
            if self._comp_unit == "weight_percent":
                self.comp_label.setText(f"wt%({el2}) =")
            else:
                self.comp_label.setText(f"X({el2}) =")

    # ----------------------------------------------------- phase helpers

    def _get_selected_phases(self) -> list[str]:
        """Return the list of checked phase names."""
        selected: list[str] = []
        for idx in range(self.phase_list.count()):
            item = self.phase_list.item(idx)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                phase = item.data(Qt.ItemDataRole.UserRole)
                selected.append(phase)
        return selected

    def _select_all_phases(self):
        self.phase_list.blockSignals(True)
        for idx in range(self.phase_list.count()):
            item = self.phase_list.item(idx)
            if item is not None:
                item.setCheckState(Qt.CheckState.Checked)
        self.phase_list.blockSignals(False)
        self._update_phase_counter()

    def _deselect_all_phases(self):
        self.phase_list.blockSignals(True)
        for idx in range(self.phase_list.count()):
            item = self.phase_list.item(idx)
            if item is not None:
                item.setCheckState(Qt.CheckState.Unchecked)
        self.phase_list.blockSignals(False)
        self._update_phase_counter()

    def _select_common_phases(self):
        """Select only common/fundamental phases."""
        common = {"LIQUID", "FCC_A1", "BCC_A2", "HCP_A3", "BCC_B2",
                  "DIAMOND_A4", "CEMENTITE", "AL2CU", "MG2SI"}
        self.phase_list.blockSignals(True)
        for idx in range(self.phase_list.count()):
            item = self.phase_list.item(idx)
            if item is not None:
                phase = item.data(Qt.ItemDataRole.UserRole)
                if phase in common:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
        self.phase_list.blockSignals(False)
        self._update_phase_counter()

    def _update_phase_counter(self):
        count = len(self._get_selected_phases())
        self.phase_counter_label.setText(f"{count} phases selected")

    # -------------------------------------------------------- temperature

    def _get_t_min_k(self) -> float:
        val = self.t_min_spin.value()
        return c_to_k(val) if self._temp_unit == "C" else val

    def _get_t_max_k(self) -> float:
        val = self.t_max_spin.value()
        return c_to_k(val) if self._temp_unit == "C" else val

    # ---------------------------------------------------------- calculate

    def _calculate(self):
        if not self.db:
            QMessageBox.warning(
                self, "No Database",
                "Please load a thermodynamic database first."
            )
            return

        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(
                self, "Please Wait",
                "A calculation is already in progress."
            )
            return

        selected_phases = self._get_selected_phases()
        if not selected_phases:
            QMessageBox.warning(
                self, "No Phases Selected",
                "Please check at least one phase in the Phase Selection list."
            )
            return

        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()
        if el1 == el2:
            QMessageBox.warning(
                self, "Same Element",
                "Element 1 and Element 2 must be different."
            )
            return

        t_min_k = self._get_t_min_k()
        t_max_k = self._get_t_max_k()
        t_step = self.t_step_spin.value()

        if t_min_k >= t_max_k:
            QMessageBox.warning(
                self, "Invalid Range",
                "T min must be less than T max."
            )
            return

        comp_val = self.comp_spin.value()
        if self._comp_unit == "weight_percent":
            # Convert weight percent to mole fraction for pycalphad
            from core.units import weight_to_mole
            converted = weight_to_mole({el1: 100.0 - comp_val, el2: comp_val})
            x_el2 = converted.get(el2, 0.5)
        else:
            x_el2 = comp_val

        # Components must include VA for pycalphad
        comps = sorted({el1, el2, "VA"})
        composition = {el2: x_el2}

        property_label = self.property_combo.currentText()
        property_name = _PROPERTY_MAP.get(property_label, "GM")

        # UI feedback
        self.calc_btn.setEnabled(False)
        self.progress_bar.setRange(0, len(selected_phases))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Calculating...")
        self.status_label.setStyleSheet("color: #FFB74D;")
        self.summary_label.setVisible(False)

        self._worker = SinglePhaseWorker(
            db=self.db,
            comps=comps,
            selected_phases=selected_phases,
            t_min=t_min_k,
            t_max=t_max_k,
            t_step=t_step,
            pressure=101325.0,
            composition=composition,
            property_name=property_name,
        )
        self._worker.progress_update.connect(self._on_progress)
        self._worker.finished.connect(self._on_calculated)
        self._worker.start()

    def _on_progress(self, current: int, total: int):
        self.progress_bar.setValue(current)
        self.status_label.setText(f"Computing phase {current}/{total}...")

    # ------------------------------------------------------- results

    def _on_calculated(self, payload: dict):
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(True)

        temps: np.ndarray = payload["temps"]
        results: dict[str, np.ndarray | None] = payload["results"]
        property_name: str = payload["property"]
        errors: list[str] = payload.get("errors", [])

        # Count successes
        successful = {k: v for k, v in results.items() if v is not None}
        if not successful:
            friendly = _friendly_error("\n".join(errors) if errors else "")
            self.status_label.setText("All phases failed")
            self.status_label.setStyleSheet("color: #E57373;")
            QMessageBox.warning(
                self, "Calculation Failed",
                f"No phases could be computed.\n\n{friendly}"
            )
            return

        self._last_payload = payload
        self._plot_results(temps, successful, property_name)
        self._fill_table(temps, successful, property_name)
        self._show_summary(temps, successful, property_name)

        failed_count = len(results) - len(successful)
        status_parts = [
            f"Computed {property_name} for {len(successful)} phase(s)"
        ]
        if failed_count:
            status_parts.append(f"({failed_count} skipped)")
        self.status_label.setText(" ".join(status_parts))
        self.status_label.setStyleSheet("color: #81C784;")

        self.export_csv_btn.setEnabled(True)
        self.export_png_btn.setEnabled(True)

        # History signal
        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()
        t_min_k = self._get_t_min_k()
        t_max_k = self._get_t_max_k()
        cond = {
            "T_min": t_min_k,
            "T_max": t_max_k,
            "property": property_name,
            "phases": list(successful.keys()),
        }
        self.calculation_done.emit(
            [el1, el2], cond, self.summary_label.text()
        )

    # -------------------------------------------------------- plotting

    def _plot_results(
        self,
        temps: np.ndarray,
        results: dict[str, np.ndarray],
        property_name: str,
    ):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        ax.set_facecolor("#1e1e2e")
        ax.tick_params(colors="white", which="both")
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.title.set_color("white")
        for spine in ax.spines.values():
            spine.set_color("#555577")

        for i, (phase, values) in enumerate(results.items()):
            color = PHASE_COLORS[i % len(PHASE_COLORS)]
            label = translate_phase_short(phase)
            # Ensure arrays have the same length (trim if needed)
            n = min(len(temps), len(values))
            ax.plot(temps[:n], values[:n], color=color, label=label, linewidth=1.5)

        unit_str = _PROPERTY_UNITS.get(property_name, "")
        ax.set_xlabel("Temperature (K)", fontsize=10)
        ax.set_ylabel(f"{property_name} ({unit_str})", fontsize=10)
        ax.set_title(
            f"{property_name} vs Temperature -- Single-Phase",
            fontsize=11, fontweight="bold",
        )

        ax.grid(True, alpha=0.2, color="#555577")

        # Legend: if many phases, place it outside the plot to avoid overlap
        n_phases = len(results)
        if n_phases <= 8:
            ax.legend(
                fontsize=8, loc="best",
                facecolor="#2a2a3e", edgecolor="#555577",
                labelcolor="white",
            )
        else:
            # Move legend outside the plot area on the right
            ax.legend(
                fontsize=7, loc="center left", bbox_to_anchor=(1.02, 0.5),
                facecolor="#2a2a3e", edgecolor="#555577",
                labelcolor="white", ncol=1 + n_phases // 20,
                borderaxespad=0,
            )

        # Secondary Celsius axis on top
        try:
            ax_c = ax.secondary_xaxis("top", functions=(k_to_c, c_to_k))
            ax_c.set_xlabel("Temperature (\u00b0C)", fontsize=9, color="#aaaacc")
            ax_c.tick_params(colors="#aaaacc", which="both")
        except Exception:
            pass

        self.figure.tight_layout()
        self.canvas.draw()

    # -------------------------------------------------------- table

    def _fill_table(
        self,
        temps: np.ndarray,
        results: dict[str, np.ndarray],
        property_name: str,
    ):
        phase_names = list(results.keys())
        columns = ["T (K)", "T (C)"] + [
            f"{translate_phase_short(p)} ({property_name})" for p in phase_names
        ]
        n_rows = len(temps)

        self.results_table.setRowCount(n_rows)
        self.results_table.setColumnCount(len(columns))
        self.results_table.setHorizontalHeaderLabels(columns)

        for row_idx in range(n_rows):
            # Temperature columns
            t_k = temps[row_idx]
            self.results_table.setItem(
                row_idx, 0, QTableWidgetItem(f"{t_k:.1f}")
            )
            self.results_table.setItem(
                row_idx, 1, QTableWidgetItem(f"{k_to_c(t_k):.1f}")
            )
            # Property columns
            for col_offset, phase in enumerate(phase_names):
                values = results[phase]
                if row_idx < len(values):
                    val = values[row_idx]
                    self.results_table.setItem(
                        row_idx, 2 + col_offset,
                        QTableWidgetItem(f"{val:.4g}"),
                    )
                else:
                    self.results_table.setItem(
                        row_idx, 2 + col_offset, QTableWidgetItem("--")
                    )

        # Use Stretch for few columns, Interactive (scrollable) for many
        if len(phase_names) <= 6:
            self.results_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )
        else:
            self.results_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Interactive
            )
            self.results_table.horizontalHeader().setDefaultSectionSize(90)
            # Make first two columns (T(K), T(C)) narrower and fixed
            self.results_table.horizontalHeader().setSectionResizeMode(
                0, QHeaderView.ResizeMode.ResizeToContents
            )
            self.results_table.horizontalHeader().setSectionResizeMode(
                1, QHeaderView.ResizeMode.ResizeToContents
            )

    # -------------------------------------------------------- summary

    def _show_summary(
        self,
        temps: np.ndarray,
        results: dict[str, np.ndarray],
        property_name: str,
    ):
        n_phases = len(results)
        mid_idx = len(temps) // 2
        mid_t = temps[mid_idx] if mid_idx < len(temps) else temps[-1]

        # Find the phase with the lowest value at the midpoint temperature
        best_phase: str | None = None
        best_val: float = float("inf")
        for phase, values in results.items():
            if mid_idx < len(values):
                val = values[mid_idx]
                if val < best_val:
                    best_val = val
                    best_phase = phase

        best_display = translate_phase_short(best_phase) if best_phase else "N/A"
        summary = (
            f"Calculated {property_name} for {n_phases} phase(s). "
            f"Phase with lowest {property_name} at midpoint "
            f"({format_temp(mid_t)}): {best_display}."
        )
        self.summary_label.setText(summary)
        self.summary_label.setVisible(True)

    # -------------------------------------------------------- export CSV

    def _metadata_lines(self) -> list[str]:
        """Return comment lines describing the calculation conditions."""
        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()
        comp_val = self.comp_spin.value()
        prop_label = self.property_combo.currentText()
        t_min_k = self._get_t_min_k()
        t_max_k = self._get_t_max_k()

        lines = [
            "# Single-Phase Calculation Results",
            f"# Generated: {datetime.datetime.now().isoformat(timespec='seconds')}",
            f"# System: {el1}-{el2}",
            f"# Composition: X({el2}) = {comp_val}",
            f"# Temperature range: {t_min_k:.0f} -- {t_max_k:.0f} K",
            f"# Property: {prop_label}",
            f"# Pressure: 101325 Pa",
        ]
        return lines

    def _export_csv(self):
        if self._last_payload is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Single-Phase Data", "single_phase.csv",
            "CSV Files (*.csv);;All Files (*)",
        )
        if not path:
            return

        temps = self._last_payload["temps"]
        results = self._last_payload["results"]
        property_name = self._last_payload["property"]
        successful = {k: v for k, v in results.items() if v is not None}
        phase_names = list(successful.keys())

        meta = self._metadata_lines()
        header = ",".join(
            ["T_K", "T_C"]
            + [f"{p}_{property_name}" for p in phase_names]
        )

        with open(path, "w", newline="") as f:
            for line in meta:
                f.write(line + "\n")
            f.write(header + "\n")
            for i in range(len(temps)):
                row_parts = [f"{temps[i]:.2f}", f"{k_to_c(temps[i]):.2f}"]
                for phase in phase_names:
                    vals = successful[phase]
                    if i < len(vals):
                        row_parts.append(f"{vals[i]:.6g}")
                    else:
                        row_parts.append("")
                f.write(",".join(row_parts) + "\n")

        self.status_label.setText(f"Exported to {path}")

    # -------------------------------------------------------- export PNG

    def _export_png(self):
        if self._last_payload is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Chart", "single_phase.png",
            "PNG Files (*.png);;All Files (*)",
        )
        if not path:
            return

        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()
        comp_val = self.comp_spin.value()
        prop_label = self.property_combo.currentText()

        subtitle = f"{el1}-{el2}, X({el2})={comp_val:.4f}, {prop_label}"
        self.canvas.figure.suptitle(subtitle, fontsize=8, color="#CCCCCC", y=0.02)
        self.canvas.draw()
        self.canvas.figure.savefig(path, dpi=150, facecolor="#1e1e2e")
        self.canvas.figure.suptitle("")
        self.canvas.draw()
        self.status_label.setText(f"Exported to {path}")
