"""Molar Volume & Density calculator panel.

Computes molar volume and density vs temperature by detecting volume
parameters (V0, VA) in the loaded thermodynamic database.  When volume
data is unavailable, a fallback mode shows phase fractions vs temperature
with an explanatory banner.
"""

from __future__ import annotations

import datetime
import traceback
from dataclasses import dataclass, field

import numpy as np
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget,
)
from gui.lazy_canvas import LazyCanvas
from pycalphad import Database, Model, equilibrium, variables as v

from core.units import k_to_c, c_to_k, format_temp
from core.presets import ATOMIC_WEIGHTS
from gui.info_content import TAB_INFO


# ---------------------------------------------------------------------------
# Volume parameter detection
# ---------------------------------------------------------------------------

def has_volume_params(db: Database) -> bool:
    """Check whether the database contains volume parameters (V0, VA, etc.)."""
    try:
        from tinydb import where
        results = db._parameters.search(
            where("parameter_type").matches("V[0-9A-Z]")
        )
        return len(results) > 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Result data class
# ---------------------------------------------------------------------------

@dataclass
class VolumeResult:
    """Holds molar volume / density scan results."""
    temperatures: np.ndarray = field(default_factory=lambda: np.array([]))
    molar_volumes: np.ndarray = field(default_factory=lambda: np.array([]))
    densities: np.ndarray = field(default_factory=lambda: np.array([]))
    phase_fractions: dict[str, np.ndarray] = field(default_factory=dict)
    has_volume_data: bool = False
    error: str | None = None

    def to_dataframe(self):
        import pandas as pd
        data: dict[str, list] = {"Temperature (K)": list(self.temperatures)}
        if self.has_volume_data:
            data["Molar Volume (m^3/mol)"] = list(self.molar_volumes)
            data["Density (kg/m^3)"] = list(self.densities)
        for phase, fracs in self.phase_fractions.items():
            data[f"NP({phase})"] = list(fracs)
        return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

class VolumeWorker(QThread):
    """Background worker for volume / density calculation."""
    finished = pyqtSignal(object)  # VolumeResult
    progress = pyqtSignal(int)     # percent 0-100

    def __init__(
        self, db, elements, composition, t_min, t_max, t_step, pressure
    ):
        super().__init__()
        self.db = db
        self.elements = elements
        self.composition = composition
        self.t_min = t_min
        self.t_max = t_max
        self.t_step = t_step
        self.pressure = pressure

    def run(self):
        result = VolumeResult()
        try:
            comps = sorted([e.upper() for e in self.elements]) + ["VA"]
            phases = list(self.db.phases.keys())
            temps = np.arange(
                self.t_min, self.t_max + self.t_step / 2, self.t_step
            )
            result.temperatures = temps

            # Check for volume parameters
            vol_available = has_volume_params(self.db)
            result.has_volume_data = vol_available

            # Compute average molar mass for density estimation
            el2 = list(self.composition.keys())[0]
            x2 = self.composition[el2]
            el1 = [e for e in self.elements if e != el2][0]
            x1 = 1.0 - x2
            aw1 = ATOMIC_WEIGHTS.get(el1.upper(), 27.0)
            aw2 = ATOMIC_WEIGHTS.get(el2.upper(), 27.0)
            avg_molar_mass = x1 * aw1 + x2 * aw2  # g/mol

            molar_vols = np.full(len(temps), np.nan)
            densities = np.full(len(temps), np.nan)
            phase_frac_data: dict[str, list[float]] = {}

            total = len(temps)
            for idx, T in enumerate(temps):
                conds = {v.T: float(T), v.P: self.pressure, v.N: 1}
                for el, x in self.composition.items():
                    conds[v.X(el.upper())] = x

                try:
                    eq = equilibrium(self.db, comps, phases, conds)

                    # Extract phase fractions
                    phase_names = eq.Phase.values.squeeze()
                    np_values = eq.NP.values.squeeze()

                    if phase_names.ndim == 0:
                        phase_names = np.array([phase_names])
                        np_values = np.array([np_values])

                    current_phases: dict[str, float] = {}
                    for pname, frac in zip(phase_names, np_values):
                        pname_str = str(pname).strip()
                        if (
                            pname_str
                            and not np.isnan(frac)
                            and frac > 1e-10
                        ):
                            current_phases[pname_str] = (
                                current_phases.get(pname_str, 0.0) + float(frac)
                            )

                    for pname in current_phases:
                        if pname not in phase_frac_data:
                            phase_frac_data[pname] = [0.0] * idx

                    for pname in phase_frac_data:
                        phase_frac_data[pname].append(
                            current_phases.get(pname, 0.0)
                        )

                    # Attempt volume extraction if parameters exist
                    if vol_available:
                        total_vm = 0.0
                        total_frac = 0.0
                        for pname, frac in current_phases.items():
                            try:
                                model = Model(self.db, comps, pname)
                                # Try to evaluate volume energy
                                vol_energy = model.models.get("vol", None)
                                if vol_energy is not None and vol_energy != 0:
                                    # Rough extraction: volume contribution
                                    # in J/mol can be related to molar volume
                                    # via V = dG/dP at constant T
                                    from sympy import Symbol, lambdify
                                    syms = list(vol_energy.free_symbols)
                                    sub_dict = {
                                        s: float(T) if "T" in str(s)
                                        else self.pressure if "P" in str(s)
                                        else 0.5
                                        for s in syms
                                    }
                                    vm_phase = float(vol_energy.subs(sub_dict))
                                    total_vm += frac * abs(vm_phase)
                                    total_frac += frac
                            except Exception:
                                pass

                        if total_frac > 0.5:
                            vm = total_vm / total_frac
                            molar_vols[idx] = vm
                            if vm > 0:
                                # density = M / V (convert g/mol to kg/mol)
                                densities[idx] = (avg_molar_mass / 1000.0) / vm

                except Exception:
                    for pname in phase_frac_data:
                        phase_frac_data[pname].append(0.0)

                self.progress.emit(int((idx + 1) / total * 100))

            result.molar_volumes = molar_vols
            result.densities = densities
            result.phase_fractions = {
                k: np.array(v_arr) for k, v_arr in phase_frac_data.items()
            }

        except Exception:
            result.error = traceback.format_exc()

        self.finished.emit(result)


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

class VolumePanel(QWidget):
    """Panel for molar volume and density calculations."""

    calculation_done = pyqtSignal(list, dict, str)

    def __init__(self):
        super().__init__()
        self.db: Database | None = None
        self.elements: list[str] = []
        self._worker: VolumeWorker | None = None
        self._last_result: VolumeResult | None = None
        self._temp_unit: str = "K"
        self._comp_unit: str = "mole_fraction"
        self._has_volume: bool = False
        self._setup_ui()

    # ------------------------------------------------------------------
    # Unit setters (match stepping_panel pattern)
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
        self._comp_unit = unit

        el2 = self.el2_combo.currentText()
        if unit == "weight_percent":
            self.comp_label.setText(f"wt%({el2}):" if el2 else "wt%(El2):")
            self.comp_spin.blockSignals(True)
            self.comp_spin.setRange(0.01, 99.99)
            self.comp_spin.setDecimals(2)
            self.comp_spin.setSingleStep(1.0)
            self.comp_spin.blockSignals(False)
        else:
            self.comp_label.setText(f"X({el2}):" if el2 else "X(El2):")
            self.comp_spin.blockSignals(True)
            self.comp_spin.setRange(0.001, 0.999)
            self.comp_spin.setDecimals(4)
            self.comp_spin.setSingleStep(0.01)
            self.comp_spin.blockSignals(False)

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

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
        title = QLabel("Molar Volume & Density")
        title.setObjectName("heading")
        layout.addWidget(title)

        # --- Educational info panel ---
        info_data = TAB_INFO.get("volume", {})
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

        # Info banner for volume parameter detection
        self.info_banner = QLabel(
            "Load a database to check for volume parameters (V0, VA)."
        )
        self.info_banner.setObjectName("infoLabel")
        self.info_banner.setWordWrap(True)
        layout.addWidget(self.info_banner)

        # --- Elements ---
        elem_group = QGroupBox("Elements")
        elem_layout = QHBoxLayout()

        elem_layout.addWidget(QLabel("Element 1:"))
        self.el1_combo = QComboBox()
        self.el1_combo.setToolTip(
            "Primary (balance) element of the alloy."
        )
        elem_layout.addWidget(self.el1_combo)

        elem_layout.addWidget(QLabel("Element 2:"))
        self.el2_combo = QComboBox()
        self.el2_combo.setToolTip(
            "Secondary (solute) element."
        )
        elem_layout.addWidget(self.el2_combo)

        elem_group.setLayout(elem_layout)
        layout.addWidget(elem_group)

        # --- Composition ---
        comp_group = QGroupBox("Composition")
        comp_layout = QHBoxLayout()

        self.comp_label = QLabel("X(El2):")
        comp_layout.addWidget(self.comp_label)
        self.comp_spin = QDoubleSpinBox()
        self.comp_spin.setRange(0.001, 0.999)
        self.comp_spin.setDecimals(4)
        self.comp_spin.setSingleStep(0.01)
        self.comp_spin.setValue(0.10)
        self.comp_spin.setToolTip(
            "Mole fraction of the second element."
        )
        comp_layout.addWidget(self.comp_spin)

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
        self.t_min_spin.setToolTip("Lowest temperature in the scan.")
        temp_layout.addWidget(self.t_min_spin)

        self.t_max_label = QLabel("T max (K):")
        temp_layout.addWidget(self.t_max_label)
        self.t_max_spin = QDoubleSpinBox()
        self.t_max_spin.setRange(100, 5000)
        self.t_max_spin.setValue(1200)
        self.t_max_spin.setSingleStep(50)
        self.t_max_spin.setToolTip("Highest temperature in the scan.")
        temp_layout.addWidget(self.t_max_spin)

        temp_layout.addWidget(QLabel("Step (K):"))
        self.t_step_spin = QDoubleSpinBox()
        self.t_step_spin.setRange(1, 100)
        self.t_step_spin.setValue(10)
        self.t_step_spin.setSingleStep(1)
        self.t_step_spin.setToolTip(
            "Temperature increment between calculations. "
            "Smaller = more precise but slower."
        )
        temp_layout.addWidget(self.t_step_spin)

        temp_group.setLayout(temp_layout)
        layout.addWidget(temp_group)

        # --- Buttons ---
        btn_layout = QHBoxLayout()

        self.calc_btn = QPushButton("Calculate")
        self.calc_btn.setObjectName("primary")
        self.calc_btn.setEnabled(False)
        self.calc_btn.setToolTip(
            "Run molar volume and density calculation across "
            "the temperature range."
        )
        self.calc_btn.clicked.connect(self._calculate)
        btn_layout.addWidget(self.calc_btn)

        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.setObjectName("success")
        self.export_csv_btn.setEnabled(False)
        self.export_csv_btn.setToolTip("Save results to a CSV file.")
        self.export_csv_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(self.export_csv_btn)

        self.export_png_btn = QPushButton("Export PNG")
        self.export_png_btn.setObjectName("success")
        self.export_png_btn.setEnabled(False)
        self.export_png_btn.setToolTip("Save the current plot as a PNG image.")
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

        # --- Summary ---
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("summaryLabel")
        self.summary_label.setWordWrap(True)
        self.summary_label.setVisible(False)
        layout.addWidget(self.summary_label)

        # --- Tab widget for plots ---
        self.tab_widget = QTabWidget()

        # Molar Volume tab
        self.vol_canvas = LazyCanvas(figsize=(8, 4), dpi=100)
        self.vol_canvas.setMinimumHeight(350)
        self.tab_widget.addTab(self.vol_canvas, "Molar Volume")

        # Density tab
        self.dens_canvas = LazyCanvas(figsize=(8, 4), dpi=100)
        self.dens_canvas.setMinimumHeight(350)
        self.tab_widget.addTab(self.dens_canvas, "Density")

        layout.addWidget(self.tab_widget, stretch=1)

        scroll.setWidget(container)
        outer.addWidget(scroll)

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
    ):
        """Called when a new database is loaded."""
        self.db = db
        self.elements = elements

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
                "Run a volume/density scan across the temperature range."
            )

        self.el1_combo.blockSignals(False)
        self.el2_combo.blockSignals(False)

        # Update composition label
        el2 = self.el2_combo.currentText()
        if self._comp_unit == "weight_percent":
            self.comp_label.setText(f"wt%({el2}):" if el2 else "wt%(El2):")
        else:
            self.comp_label.setText(f"X({el2}):" if el2 else "X(El2):")

        # Detect volume parameters
        self._has_volume = has_volume_params(db)
        if self._has_volume:
            self.info_banner.setText(
                "Volume parameters (V0, VA) detected in this database. "
                "Molar volume and density will be computed from the "
                "thermodynamic model."
            )
            self.info_banner.setStyleSheet(
                "background-color: #0d2744; color: #81C784; "
                "border: 1px solid #2E7D32; border-radius: 5px; "
                "padding: 8px 12px; font-size: 12px;"
            )
        else:
            self.info_banner.setText(
                "No volume parameters (V0, VA) found in this database. "
                "Volume calculations require TDB files with volume data. "
                "Phase fractions vs temperature will be shown instead."
            )
            self.info_banner.setStyleSheet(
                "background-color: #3a2a1a; color: #FFB74D; "
                "border: 1px solid #E65100; border-radius: 5px; "
                "padding: 8px 12px; font-size: 12px;"
            )

    # ------------------------------------------------------------------
    # Calculation
    # ------------------------------------------------------------------

    def _calculate(self):
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

        t_min = self.t_min_spin.value()
        t_max = self.t_max_spin.value()
        t_step = self.t_step_spin.value()
        if self._temp_unit == "C":
            t_min = c_to_k(t_min)
            t_max = c_to_k(t_max)

        if t_min >= t_max:
            QMessageBox.warning(
                self, "Temperature Range Issue",
                f"T min ({t_min:.0f} K) must be less than T max ({t_max:.0f} K)."
            )
            return

        compositions = {el2: self.comp_spin.value()}
        pressure = 101325.0

        self.calc_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Calculating volume/density scan...")
        self.status_label.setStyleSheet("color: #FFB74D;")
        self.summary_label.setVisible(False)

        self._worker = VolumeWorker(
            self.db, [el1, el2], compositions,
            t_min, t_max, t_step, pressure
        )
        self._worker.progress.connect(self.progress_bar.setValue)
        self._worker.finished.connect(self._on_calculated)
        self._worker.start()

    def _on_calculated(self, result: VolumeResult):
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(True)

        if result.error:
            self.status_label.setText("Calculation failed")
            self.status_label.setStyleSheet("color: #E57373;")
            QMessageBox.critical(
                self, "Calculation Failed",
                f"The volume calculation encountered an error:\n\n"
                f"{result.error[-400:]}"
            )
            return

        self._last_result = result
        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()
        x = self.comp_spin.value()

        # --- Molar volume plot ---
        self.vol_figure.clear()
        ax_vol = self.vol_figure.add_subplot(111)
        ax_vol.set_facecolor("#1e1e2e")

        if result.has_volume_data and not np.all(np.isnan(result.molar_volumes)):
            valid = ~np.isnan(result.molar_volumes)
            ax_vol.plot(
                result.temperatures[valid],
                result.molar_volumes[valid] * 1e6,  # m^3 -> cm^3
                color="#4FC3F7", linewidth=2,
            )
            ax_vol.set_ylabel(
                "Molar Volume (cm\u00b3/mol)",
                color="#ccccdd", fontsize=11,
            )
            ax_vol.set_title(
                f"Molar Volume: {el1}-{x:.2%}{el2}",
                color="#4FC3F7", fontsize=13, fontweight="bold",
            )
        else:
            # Fallback: show phase fractions
            for phase, fracs in result.phase_fractions.items():
                ax_vol.plot(
                    result.temperatures, fracs,
                    linewidth=2, label=phase,
                )
            ax_vol.set_ylabel(
                "Phase Fraction", color="#ccccdd", fontsize=11,
            )
            ax_vol.set_title(
                f"Phase Fractions (no volume data): {el1}-{x:.2%}{el2}",
                color="#FFB74D", fontsize=13, fontweight="bold",
            )
            ax_vol.legend(
                facecolor="#16213e", edgecolor="#333355",
                labelcolor="#e0e0e0", fontsize=9,
            )

        ax_vol.set_xlabel("Temperature (K)", color="#ccccdd", fontsize=11)
        ax_vol.tick_params(colors="#aaaacc")
        for spine in ax_vol.spines.values():
            spine.set_color("#333355")
        ax_vol.grid(True, color="#2a2a4a", alpha=0.5)
        self.vol_figure.tight_layout()
        self.vol_canvas.draw()

        # --- Density plot ---
        self.dens_canvas.figure.clear()
        ax_dens = self.dens_canvas.figure.add_subplot(111)
        ax_dens.set_facecolor("#1e1e2e")

        if result.has_volume_data and not np.all(np.isnan(result.densities)):
            valid = ~np.isnan(result.densities)
            ax_dens.plot(
                result.temperatures[valid],
                result.densities[valid],
                color="#81C784", linewidth=2,
            )
            ax_dens.set_ylabel(
                "Density (kg/m\u00b3)", color="#ccccdd", fontsize=11,
            )
            ax_dens.set_title(
                f"Density: {el1}-{x:.2%}{el2}",
                color="#4FC3F7", fontsize=13, fontweight="bold",
            )
        else:
            # Fallback: show phase fractions
            for phase, fracs in result.phase_fractions.items():
                ax_dens.plot(
                    result.temperatures, fracs,
                    linewidth=2, label=phase,
                )
            ax_dens.set_ylabel(
                "Phase Fraction", color="#ccccdd", fontsize=11,
            )
            ax_dens.set_title(
                f"Phase Fractions (no density data): {el1}-{x:.2%}{el2}",
                color="#FFB74D", fontsize=13, fontweight="bold",
            )
            ax_dens.legend(
                facecolor="#16213e", edgecolor="#333355",
                labelcolor="#e0e0e0", fontsize=9,
            )

        ax_dens.set_xlabel("Temperature (K)", color="#ccccdd", fontsize=11)
        ax_dens.tick_params(colors="#aaaacc")
        for spine in ax_dens.spines.values():
            spine.set_color("#333355")
        ax_dens.grid(True, color="#2a2a4a", alpha=0.5)
        self.dens_canvas.figure.tight_layout()
        self.dens_canvas.draw()

        # --- Summary ---
        n_phases = len(result.phase_fractions)
        if result.has_volume_data and not np.all(np.isnan(result.molar_volumes)):
            valid_vols = result.molar_volumes[~np.isnan(result.molar_volumes)]
            valid_dens = result.densities[~np.isnan(result.densities)]
            summary = (
                f"Volume scan complete for {el1}-{x*100:.1f}%{el2}. "
                f"{n_phases} phase(s) found across "
                f"{result.temperatures[0]:.0f}-{result.temperatures[-1]:.0f} K. "
            )
            if len(valid_vols) > 0:
                summary += (
                    f"Molar volume range: "
                    f"{valid_vols.min()*1e6:.3f} - "
                    f"{valid_vols.max()*1e6:.3f} cm\u00b3/mol. "
                )
            if len(valid_dens) > 0:
                summary += (
                    f"Density range: "
                    f"{valid_dens.min():.1f} - "
                    f"{valid_dens.max():.1f} kg/m\u00b3."
                )
        else:
            summary = (
                f"Phase fraction scan complete for {el1}-{x*100:.1f}%{el2}. "
                f"{n_phases} phase(s) found. "
                "Volume/density data unavailable -- this database lacks "
                "volume parameters (V0, VA)."
            )

        self.summary_label.setText(summary)
        self.summary_label.setVisible(True)

        self.export_csv_btn.setEnabled(True)
        self.export_png_btn.setEnabled(True)
        self.status_label.setText(
            f"Scan complete: {n_phases} phases, "
            f"{len(result.temperatures)} temperature points"
        )
        self.status_label.setStyleSheet("color: #81C784;")

        # Emit history signal
        cond = {
            "T_min": self.t_min_spin.value(),
            "T_max": self.t_max_spin.value(),
            "X": x,
        }
        self.calculation_done.emit(
            [el1, el2], cond, self.summary_label.text()
        )

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _build_conditions_text(self) -> str:
        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()
        x = self.comp_spin.value()
        comp_str = (
            f"wt%({el2}) = {x:.2f}"
            if self._comp_unit == "weight_percent"
            else f"X({el2}) = {x:.4f}"
        )
        t_min = self.t_min_spin.value()
        t_max = self.t_max_spin.value()
        if self._temp_unit == "C":
            t_min = c_to_k(t_min)
            t_max = c_to_k(t_max)
        return (
            f"System: {el1}-{el2}  |  {comp_str}  |  "
            f"T: {t_min:.0f}-{t_max:.0f} K "
            f"(step {self.t_step_spin.value():.0f} K)"
        )

    def _export_csv(self):
        if not self._last_result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Volume Data", "volume_density.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return

        conditions = self._build_conditions_text()
        df = self._last_result.to_dataframe()

        try:
            with open(path, "w", newline="") as f:
                f.write("# CALPHAD Volume & Density Calculation\n")
                f.write(
                    f"# Exported: {datetime.datetime.now().isoformat()}\n"
                )
                f.write(f"# {conditions}\n")
                f.write("#\n")
                df.to_csv(f, index=False)
            self.status_label.setText(f"Exported to {path}")
        except Exception as exc:
            QMessageBox.critical(
                self, "Export Failed",
                f"Could not write CSV file:\n\n{exc}"
            )

    def _export_png(self):
        # Export whichever tab is currently active
        if self.tab_widget.currentIndex() == 0:
            figure = self.vol_figure
            default_name = "molar_volume.png"
        else:
            figure = self.dens_figure
            default_name = "density.png"

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Plot", default_name,
            "PNG Files (*.png);;All Files (*)"
        )
        if not path:
            return

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
            if self.tab_widget.currentIndex() == 0:
                self.vol_canvas.draw()
            else:
                self.dens_canvas.draw()
