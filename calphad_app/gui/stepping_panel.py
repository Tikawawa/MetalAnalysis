"""Stepping (1-D scan) calculation panel."""

from __future__ import annotations

import datetime

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QMessageBox, QProgressBar,
    QPushButton, QRadioButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)
from gui.lazy_canvas import LazyCanvas
from pycalphad import Database

from core.calculations import SteppingResult, calculate_stepping, CompositionSteppingResult, calculate_composition_stepping
from core.plotting import plot_stepping_result, plot_composition_stepping
from core.presets import get_binary_preset, translate_phase_short, MELTING_POINTS_K
from core.units import k_to_c, c_to_k, format_temp, mole_to_weight, weight_to_mole
from core.error_helper import build_error_message
from gui.info_content import TAB_INFO, TOOLTIPS, PHASE_EXPLANATIONS


class SteppingWorker(QThread):
    """Worker thread for stepping calculation."""
    finished = pyqtSignal(object)  # SteppingResult

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
        result = calculate_stepping(
            self.db, self.elements, self.compositions,
            self.t_min, self.t_max, self.t_step, self.pressure
        )
        self.finished.emit(result)


class CompSteppingWorker(QThread):
    """Worker thread for composition sweep calculation."""
    finished = pyqtSignal(object)  # CompositionSteppingResult

    def __init__(self, db, elements, varied_element, comp_min, comp_max, comp_step,
                 temperature, pressure):
        super().__init__()
        self.db = db
        self.elements = elements
        self.varied_element = varied_element
        self.comp_min = comp_min
        self.comp_max = comp_max
        self.comp_step = comp_step
        self.temperature = temperature
        self.pressure = pressure

    def run(self):
        result = calculate_composition_stepping(
            self.db, self.elements, self.varied_element,
            self.comp_min, self.comp_max, self.comp_step,
            self.temperature, self.pressure,
        )
        self.finished.emit(result)


class SteppingPanel(QWidget):
    """Panel for stepping calculations (phase fraction vs temperature)."""

    calculation_done = pyqtSignal(list, dict, str)  # (elements, conditions, summary)

    def __init__(self):
        super().__init__()
        self.db: Database | None = None
        self.elements: list[str] = []
        self._worker: SteppingWorker | None = None
        self._last_result: SteppingResult | None = None
        self._temp_unit: str = "K"   # "K" or "C"
        self._comp_unit: str = "mole_fraction"  # "mole_fraction" or "weight_percent"
        self._sweep_mode: str = "temperature"  # "temperature" or "composition"
        self._comp_worker: CompSteppingWorker | None = None
        self._last_comp_result: CompositionSteppingResult | None = None
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

        # Block signals to prevent triggering side effects during conversion
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
        old_value = self.comp_spin.value()

        if unit == "weight_percent":
            self.comp_label.setText(f"wt%({el2}):" if el2 else "wt%(El2):")
            self.comp_spin.setToolTip(
                "Weight percent of the second element. "
                "For example, 10.0 means 10 wt% of Element 2."
            )
            # Convert mole fraction -> weight percent
            if el1 and el2 and el1 != el2:
                mole_dict = {el2: old_value, el1: 1.0 - old_value}
                wt_dict = mole_to_weight(mole_dict)
                self.comp_spin.blockSignals(True)
                self.comp_spin.setRange(0.01, 99.99)
                self.comp_spin.setDecimals(2)
                self.comp_spin.setSingleStep(1.0)
                self.comp_spin.setValue(wt_dict.get(el2, old_value * 100))
                self.comp_spin.blockSignals(False)
        else:
            self.comp_label.setText(f"X({el2}):" if el2 else "X(El2):")
            self.comp_spin.setToolTip(
                "Mole fraction of the second element. "
                "For example, 0.10 means 10% of Element 2."
            )
            # Convert weight percent -> mole fraction
            if el1 and el2 and el1 != el2:
                wt_dict = {el2: old_value, el1: 100.0 - old_value}
                mole_dict = weight_to_mole(wt_dict)
                self.comp_spin.blockSignals(True)
                self.comp_spin.setRange(0.001, 0.999)
                self.comp_spin.setDecimals(4)
                self.comp_spin.setSingleStep(0.01)
                self.comp_spin.setValue(mole_dict.get(el2, old_value / 100))
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
        layout.setSpacing(6)

        title = QLabel("Stepping Calculator")
        title.setObjectName("heading")
        layout.addWidget(title)

        # --- Educational info panel ---
        info_data = TAB_INFO.get("stepping", {})
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

        # --- Sweep mode toggle ---
        mode_group = QGroupBox("Sweep Mode")
        mode_layout = QHBoxLayout()
        self.temp_sweep_radio = QRadioButton("Sweep Temperature")
        self.temp_sweep_radio.setChecked(True)
        self.temp_sweep_radio.setToolTip(
            "Sweep temperature at fixed composition (standard mode)"
        )
        self.comp_sweep_radio = QRadioButton("Sweep Composition")
        self.comp_sweep_radio.setToolTip(
            "Sweep composition at fixed temperature to see how phases change "
            "as you add more of an element"
        )
        mode_layout.addWidget(self.temp_sweep_radio)
        mode_layout.addWidget(self.comp_sweep_radio)
        mode_layout.addStretch()
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        self.temp_sweep_radio.toggled.connect(self._on_sweep_mode_changed)

        # --- Composition input ---
        comp_group = QGroupBox("Fixed Composition")
        comp_layout = QHBoxLayout()

        comp_layout.addWidget(QLabel("Element 1:"))
        self.el1_combo = QComboBox()
        self.el1_combo.setToolTip(TOOLTIPS["step_el1"])
        comp_layout.addWidget(self.el1_combo)

        comp_layout.addWidget(QLabel("Element 2:"))
        self.el2_combo = QComboBox()
        self.el2_combo.setToolTip(TOOLTIPS["step_el2"])
        comp_layout.addWidget(self.el2_combo)

        self.comp_label = QLabel("X(El2):")
        comp_layout.addWidget(self.comp_label)
        self.comp_spin = QDoubleSpinBox()
        self.comp_spin.setRange(0.001, 0.999)
        self.comp_spin.setDecimals(4)
        self.comp_spin.setSingleStep(0.01)
        self.comp_spin.setValue(0.10)
        self.comp_spin.setToolTip(TOOLTIPS["step_composition"])
        comp_layout.addWidget(self.comp_spin)

        # Alloy composition hint (Improvement 10)
        self.alloy_hint_label = QLabel("")
        self.alloy_hint_label.setStyleSheet("color: #90CAF9; font-size: 11px;")
        self.alloy_hint_label.setWordWrap(True)
        self.alloy_hint_label.setVisible(False)
        comp_layout.addWidget(self.alloy_hint_label)

        # Connect composition changes to alloy hint updater
        self.comp_spin.valueChanged.connect(self._update_alloy_hint)

        comp_group.setLayout(comp_layout)
        layout.addWidget(comp_group)

        # Info label for preset information (below composition group)
        self.info_label = QLabel("")
        self.info_label.setStyleSheet(
            "color: #90CAF9; font-size: 12px; padding: 2px 6px;"
        )
        self.info_label.setWordWrap(True)
        self.info_label.setVisible(False)
        layout.addWidget(self.info_label)

        # --- Temperature range ---
        temp_group = QGroupBox("Temperature Range")
        temp_layout = QHBoxLayout()

        self.t_min_label = QLabel("T min (K):")
        temp_layout.addWidget(self.t_min_label)
        self.t_min_spin = QDoubleSpinBox()
        self.t_min_spin.setRange(100, 5000)
        self.t_min_spin.setValue(300)
        self.t_min_spin.setSingleStep(50)
        self.t_min_spin.setToolTip(TOOLTIPS["step_t_min"])
        temp_layout.addWidget(self.t_min_spin)

        self.t_max_label = QLabel("T max (K):")
        temp_layout.addWidget(self.t_max_label)
        self.t_max_spin = QDoubleSpinBox()
        self.t_max_spin.setRange(100, 5000)
        self.t_max_spin.setValue(1200)
        self.t_max_spin.setSingleStep(50)
        self.t_max_spin.setToolTip(TOOLTIPS["step_t_max"])
        temp_layout.addWidget(self.t_max_spin)

        temp_layout.addWidget(QLabel("Step (K):"))
        self.t_step_spin = QDoubleSpinBox()
        self.t_step_spin.setRange(1, 100)
        self.t_step_spin.setValue(5)
        self.t_step_spin.setSingleStep(1)
        self.t_step_spin.setToolTip(TOOLTIPS["step_t_step"])
        temp_layout.addWidget(self.t_step_spin)

        temp_layout.addWidget(QLabel("Pressure (Pa):"))
        self.pressure_spin = QDoubleSpinBox()
        self.pressure_spin.setRange(1, 1e9)
        self.pressure_spin.setValue(101325)
        self.pressure_spin.setDecimals(0)
        self.pressure_spin.setToolTip(TOOLTIPS["step_pressure"])
        temp_layout.addWidget(self.pressure_spin)

        temp_group.setLayout(temp_layout)
        layout.addWidget(temp_group)
        self.temp_range_group = temp_group

        # Temperature reference bar (Improvement 9)
        self.temp_ref_label = QLabel(
            "Room: 298K | Al melts: 933K | Fe melts: 1811K | Steel: ~1800K"
        )
        self.temp_ref_label.setStyleSheet("color: #666688; font-size: 11px;")
        layout.addWidget(self.temp_ref_label)

        # --- Composition Sweep Conditions (hidden by default) ---
        self.comp_sweep_group = QGroupBox("Composition Sweep Range")
        comp_sweep_layout = QHBoxLayout()

        comp_sweep_layout.addWidget(QLabel("Fixed T (K):"))
        self.fixed_temp_spin = QDoubleSpinBox()
        self.fixed_temp_spin.setRange(100, 5000)
        self.fixed_temp_spin.setValue(800)
        self.fixed_temp_spin.setSingleStep(50)
        self.fixed_temp_spin.setToolTip(
            "Fixed temperature for the composition sweep"
        )
        comp_sweep_layout.addWidget(self.fixed_temp_spin)

        comp_sweep_layout.addWidget(QLabel("X min:"))
        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(0.001, 0.999)
        self.x_min_spin.setValue(0.01)
        self.x_min_spin.setDecimals(3)
        self.x_min_spin.setSingleStep(0.01)
        self.x_min_spin.setToolTip("Minimum composition (mole fraction)")
        comp_sweep_layout.addWidget(self.x_min_spin)

        comp_sweep_layout.addWidget(QLabel("X max:"))
        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(0.001, 0.999)
        self.x_max_spin.setValue(0.50)
        self.x_max_spin.setDecimals(3)
        self.x_max_spin.setSingleStep(0.01)
        self.x_max_spin.setToolTip("Maximum composition (mole fraction)")
        comp_sweep_layout.addWidget(self.x_max_spin)

        comp_sweep_layout.addWidget(QLabel("X step:"))
        self.x_step_spin = QDoubleSpinBox()
        self.x_step_spin.setRange(0.001, 0.1)
        self.x_step_spin.setValue(0.01)
        self.x_step_spin.setDecimals(3)
        self.x_step_spin.setSingleStep(0.005)
        self.x_step_spin.setToolTip("Composition step size")
        comp_sweep_layout.addWidget(self.x_step_spin)

        self.comp_sweep_group.setLayout(comp_sweep_layout)
        self.comp_sweep_group.setVisible(False)
        layout.addWidget(self.comp_sweep_group)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        self.calc_btn = QPushButton("Calculate Stepping")
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
            "Save the phase fraction data to a CSV file, "
            "including calculation conditions as header comments."
        )
        self.export_csv_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(self.export_csv_btn)

        self.export_png_btn = QPushButton("Export PNG")
        self.export_png_btn.setObjectName("success")
        self.export_png_btn.setEnabled(False)
        self.export_png_btn.setToolTip(
            "Save the current plot as a PNG image, "
            "with calculation conditions annotated on the figure."
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

        # --- Solidus / Liquidus display ---
        self.temps_label = QLabel("")
        self.temps_label.setStyleSheet(
            "color: #FFB74D; font-size: 13px; font-weight: bold;"
        )
        layout.addWidget(self.temps_label)

        # --- Plain-English result summary (above the plot) ---
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet(
            "color: #E0E0E0; font-size: 12px; padding: 4px 6px; "
            "background: #2a2a3c; border-radius: 4px;"
        )
        self.summary_label.setWordWrap(True)
        self.summary_label.setVisible(False)
        layout.addWidget(self.summary_label)

        # --- Sanity-check warning label (below summary, orange) ---
        self.sanity_label = QLabel("")
        self.sanity_label.setStyleSheet(
            "color: #FFB74D; font-size: 12px; padding: 4px 6px; "
            "background: #3a2a1a; border-radius: 4px;"
        )
        self.sanity_label.setWordWrap(True)
        self.sanity_label.setVisible(False)
        layout.addWidget(self.sanity_label)

        # --- Plot ---
        self.canvas = LazyCanvas(figsize=(8, 5), dpi=100)
        self.canvas.setMinimumHeight(400)
        layout.addWidget(self.canvas, stretch=1)

        # Connect element combo signals for auto-fill
        self.el1_combo.currentTextChanged.connect(self._on_element_changed)
        self.el2_combo.currentTextChanged.connect(self._on_element_changed)

        scroll.setWidget(container)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    # Sweep mode toggle
    # ------------------------------------------------------------------

    def _on_sweep_mode_changed(self, temp_checked: bool):
        """Toggle between temperature sweep and composition sweep modes."""
        if temp_checked:
            self._sweep_mode = "temperature"
            self.temp_range_group.setVisible(True)
            self.comp_sweep_group.setVisible(False)
            self.comp_label.setVisible(True)
            self.comp_spin.setVisible(True)
            self.calc_btn.setText("Calculate Stepping")
        else:
            self._sweep_mode = "composition"
            self.temp_range_group.setVisible(False)
            self.comp_sweep_group.setVisible(True)
            self.comp_label.setVisible(False)
            self.comp_spin.setVisible(False)
            self.calc_btn.setText("Calculate Composition Sweep")

    # ------------------------------------------------------------------
    # Smart temperature range auto-fill
    # ------------------------------------------------------------------

    def _on_element_changed(self):
        """Auto-fill temperature range when element selection changes."""
        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()
        if not el1 or not el2 or el1 == el2:
            self.info_label.setVisible(False)
            return

        preset = get_binary_preset(el1, el2)
        if preset is not None:
            self.t_min_spin.setValue(preset.t_min_k)
            self.t_max_spin.setValue(preset.t_max_k)
            desc = preset.description
            info_parts = [f"{el1}-{el2} system: {desc}"]
            if preset.eutectic_t_k is not None:
                info_parts.append(
                    f"Eutectic at {format_temp(preset.eutectic_t_k)}, "
                    f"X({preset.el2}) = {preset.eutectic_comp:.3f}"
                )
            self.info_label.setText("  |  ".join(info_parts))
            self.info_label.setStyleSheet("color: #4FC3F7;")
            self.info_label.setVisible(True)
        else:
            # No preset -- estimate from melting points and warn
            known = "Al-Cu, Al-Si, Al-Mg, Al-Zn, Mg-Al, Mg-Zn, Cu-Zn, Cu-Sn, Fe-C, Fe-Cr, Ti-Al"
            mp1 = MELTING_POINTS_K.get(el1.upper())
            mp2 = MELTING_POINTS_K.get(el2.upper())
            if mp1 and mp2:
                t_max_est = min(max(mp1, mp2) * 1.15, 5000.0)
                self.t_min_spin.setValue(300)
                self.t_max_spin.setValue(round(t_max_est / 50) * 50)
                self.info_label.setText(
                    f"No common alloys use {el1}-{el2}. "
                    f"Range estimated from melting points. "
                    f"Known systems: {known}."
                )
            else:
                self.info_label.setText(
                    f"No common alloys use {el1}-{el2}. "
                    f"Known systems: {known}."
                )
            self.info_label.setStyleSheet("color: #FFB74D;")
            self.info_label.setVisible(True)

    # ------------------------------------------------------------------
    # Alloy composition hint (Improvement 10)
    # ------------------------------------------------------------------

    def _update_alloy_hint(self):
        """Show a hint about common alloys near the current composition."""
        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()
        x = self.comp_spin.value()

        # Simple lookup of common alloy compositions
        hints = {
            ("AL", "CU"): [
                (0.04, "2024 (aircraft skin)"),
                (0.05, "2024"),
                (0.10, "bronze territory"),
            ],
            ("AL", "SI"): [
                (0.07, "A356 (engine blocks)"),
                (0.12, "A413 (die casting)"),
            ],
            ("AL", "MG"): [
                (0.04, "5083 (marine grade)"),
                (0.01, "6061 (structural)"),
            ],
            ("FE", "C"): [
                (0.004, "1045 steel"),
                (0.008, "1080 spring steel"),
                (0.02, "cast iron range"),
            ],
        }

        key = (el1.upper(), el2.upper())
        matches = hints.get(key, [])
        closest = None
        min_dist = float("inf")
        for comp, name in matches:
            dist = abs(x - comp)
            if dist < min_dist and dist < 0.03:
                min_dist = dist
                closest = name

        if closest:
            self.alloy_hint_label.setText(f"Near this composition: {closest}")
            self.alloy_hint_label.setVisible(True)
        else:
            self.alloy_hint_label.setVisible(False)

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

    def update_database(self, db: Database, elements: list[str], phases: list[str]):
        self.db = db
        self.elements = elements

        # Block signals while populating to avoid premature auto-fill
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
                "Run a stepping calculation that scans temperature from "
                "T min to T max and records phase fractions at each step."
            )

        self.el1_combo.blockSignals(False)
        self.el2_combo.blockSignals(False)

        # Trigger auto-fill now that both combos are populated
        self._on_element_changed()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_conditions_text(self) -> str:
        """Build a human-readable string of the current calculation conditions."""
        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()
        x = self.comp_spin.value()
        comp_str = (
            f"wt%({el2}) = {x:.4f}"
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
            f"(step {self.t_step_spin.value():.0f} K)  |  "
            f"P: {self.pressure_spin.value():.0f} Pa"
        )

    def _friendly_error(self, raw_error: str) -> str:
        """Translate a raw traceback into a user-friendly message."""
        lower = raw_error.lower()
        if "database" in lower or "tdb" in lower:
            return (
                "The thermodynamic database does not seem to support these "
                "elements or phases. Please check that the loaded TDB file "
                "covers the selected system."
            )
        if "convergence" in lower or "singular" in lower or "did not converge" in lower:
            return (
                "The solver could not converge at one or more temperatures. "
                "Try a wider temperature step, a narrower range, or check "
                "that the composition is within a physically meaningful region."
            )
        if "memory" in lower or "killed" in lower:
            return (
                "The calculation ran out of memory. Try increasing the "
                "temperature step or narrowing the temperature range."
            )
        if "phase" in lower and "not found" in lower:
            return (
                "One or more phases required for this system were not found "
                "in the database. The TDB file may not cover the full "
                "composition space."
            )
        # Fallback: show the last line of the traceback
        lines = [l.strip() for l in raw_error.strip().splitlines() if l.strip()]
        last_line = lines[-1] if lines else raw_error
        return (
            f"The calculation encountered an error:\n\n{last_line}\n\n"
            "If this persists, try different conditions or a different database."
        )

    def _sanity_check(self, result: SteppingResult, el1: str, el2: str) -> str | None:
        """Check if solidus/liquidus look reasonable for the given elements.

        Returns a warning string, or None if everything looks fine.
        """
        warnings: list[str] = []

        mp1 = MELTING_POINTS_K.get(el1.upper())
        mp2 = MELTING_POINTS_K.get(el2.upper())

        if mp1 is None or mp2 is None:
            return None  # can't check without melting point data

        lower_mp = min(mp1, mp2)
        upper_mp = max(mp1, mp2)

        if result.solidus is not None:
            if result.solidus > upper_mp:
                warnings.append(
                    f"The calculated solidus ({result.solidus:.0f} K) is above "
                    f"the melting point of both pure elements "
                    f"({el1}: {mp1:.0f} K, {el2}: {mp2:.0f} K). "
                    "This is unusual -- check the database and composition."
                )
            if result.solidus < 100:
                warnings.append(
                    f"The calculated solidus ({result.solidus:.0f} K) is "
                    "unrealistically low. The calculation may not have "
                    "converged properly."
                )

        if result.liquidus is not None:
            if result.liquidus > upper_mp * 1.3:
                warnings.append(
                    f"The calculated liquidus ({result.liquidus:.0f} K) is "
                    f"significantly above the highest pure-element melting "
                    f"point ({upper_mp:.0f} K). Verify the database covers "
                    "this system correctly."
                )

        if result.solidus is not None and result.liquidus is not None:
            if result.solidus > result.liquidus:
                warnings.append(
                    "The solidus is higher than the liquidus, which is "
                    "physically impossible. The scan resolution may be too "
                    "coarse -- try a smaller temperature step."
                )
            mushy = result.liquidus - result.solidus
            if mushy > 0.7 * (upper_mp - 273):
                warnings.append(
                    f"The mushy zone spans {mushy:.0f} K, which is unusually "
                    "wide. Consider verifying the composition and database."
                )

        return "\n".join(warnings) if warnings else None

    # ------------------------------------------------------------------
    # Calculation
    # ------------------------------------------------------------------

    def _calculate(self):
        if not self.db:
            return

        # Guard against race condition
        if self._worker is not None and self._worker.isRunning():
            return
        if self._comp_worker is not None and self._comp_worker.isRunning():
            return

        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()

        if el1 == el2:
            QMessageBox.warning(
                self, "Same Element Selected",
                "Please select two different elements. Element 1 is the "
                "solvent (base metal) and Element 2 is the solute."
            )
            return

        # Dispatch based on sweep mode
        if self._sweep_mode == "composition":
            self._calculate_comp_sweep(el1, el2)
        else:
            self._calculate_temp_sweep(el1, el2)

    def _calculate_comp_sweep(self, el1: str, el2: str):
        """Run a composition sweep at fixed temperature."""
        fixed_t = self.fixed_temp_spin.value()
        if self._temp_unit == "C":
            fixed_t = c_to_k(fixed_t)

        x_min = self.x_min_spin.value()
        x_max = self.x_max_spin.value()
        x_step = self.x_step_spin.value()

        if x_min >= x_max:
            QMessageBox.warning(
                self, "Composition Range Issue",
                "X min must be less than X max."
            )
            return

        elements = [el1, el2]
        pressure = self.pressure_spin.value()

        self.calc_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Calculating composition sweep...")
        self.status_label.setStyleSheet("color: #FFB74D;")
        self.summary_label.setVisible(False)
        self.sanity_label.setVisible(False)

        self._comp_worker = CompSteppingWorker(
            self.db, elements, el2, x_min, x_max, x_step, fixed_t, pressure,
        )
        self._comp_worker.finished.connect(self._on_comp_calculated)
        self._comp_worker.start()

    def _on_comp_calculated(self, result: CompositionSteppingResult):
        """Handle composition sweep results."""
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(True)

        if result.error:
            self.status_label.setText("Calculation failed")
            self.status_label.setStyleSheet("color: #E57373;")
            el1 = self.el1_combo.currentText()
            el2 = self.el2_combo.currentText()
            friendly, technical = build_error_message(
                raw_error=result.error, db=self.db,
                calc_type="composition stepping",
                elements_used=[el1, el2],
                temperature=result.temperature,
            )
            QMessageBox.warning(self, "Calculation Did Not Succeed",
                                f"{friendly}\n\n{technical}")
            return

        self._last_comp_result = result
        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()

        translated_fracs = {}
        for phase, fracs in result.phase_fractions.items():
            label = translate_phase_short(phase)
            translated_fracs[label] = fracs

        plot_composition_stepping(
            self.canvas.figure, result.compositions, translated_fracs,
            el2, result.temperature,
        )
        self.canvas.draw()
        self.canvas.enable_line_hover()

        n_phases = len(result.phase_fractions)
        self.temps_label.setText("")
        self.summary_label.setText(
            f"Composition sweep at {result.temperature:.0f} K "
            f"({k_to_c(result.temperature):.0f} \u00b0C): "
            f"{n_phases} phases found across X({el2}) = "
            f"{result.compositions[0]:.3f} to {result.compositions[-1]:.3f}."
        )
        self.summary_label.setVisible(True)
        self.sanity_label.setVisible(False)

        self.export_csv_btn.setEnabled(True)
        self.export_png_btn.setEnabled(True)
        self.status_label.setText(f"Composition sweep complete: {n_phases} phases found")
        self.status_label.setStyleSheet("color: #81C784;")

        cond = {"T": result.temperature, "X_min": result.compositions[0],
                "X_max": result.compositions[-1]}
        self.calculation_done.emit([el1, el2], cond, self.summary_label.text())

    def _calculate_temp_sweep(self, el1: str, el2: str):
        """Run a temperature sweep at fixed composition (original mode)."""
        t_min = self.t_min_spin.value()
        t_max = self.t_max_spin.value()
        t_step = self.t_step_spin.value()
        if self._temp_unit == "C":
            t_min = c_to_k(t_min)
            t_max = c_to_k(t_max)

        if t_min >= t_max:
            QMessageBox.warning(
                self, "Temperature Range Issue",
                "The minimum temperature must be lower than the maximum. "
                f"Currently T min = {t_min:.0f} K and T max = {t_max:.0f} K."
            )
            return

        compositions = {el2: self.comp_spin.value()}
        elements = [el1, el2]
        pressure = self.pressure_spin.value()

        self.calc_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Calculating stepping... This may take a while.")
        self.status_label.setStyleSheet("color: #FFB74D;")
        self.summary_label.setVisible(False)
        self.sanity_label.setVisible(False)

        self._worker = SteppingWorker(
            self.db, elements, compositions, t_min, t_max, t_step, pressure
        )
        self._worker.finished.connect(self._on_calculated)
        self._worker.start()

    def _on_calculated(self, result: SteppingResult):
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(True)

        if result.error:
            self.status_label.setText("Calculation failed")
            self.status_label.setStyleSheet("color: #E57373;")
            self.calc_btn.setEnabled(True)
            el1 = self.el1_combo.currentText()
            el2 = self.el2_combo.currentText()
            friendly, technical = build_error_message(
                raw_error=result.error, db=self.db,
                calc_type="temperature stepping",
                elements_used=[el1, el2],
                composition={el2: self.comp_spin.value()},
            )
            QMessageBox.warning(self, "Calculation Did Not Succeed",
                                f"{friendly}\n\n{technical}")
            return

        self._last_result = result

        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()
        x = self.comp_spin.value()

        # Build translated phase labels for the plot legend
        translated_fractions: dict[str, any] = {}
        for phase, fracs in result.phase_fractions.items():
            label = translate_phase_short(phase)
            translated_fractions[label] = fracs

        plot_stepping_result(
            self.canvas.figure,
            result.temperatures,
            translated_fractions,
            result.solidus,
            result.liquidus,
            title=f"Phase Fractions: {el1}-{x:.2%}{el2}",
        )
        self.canvas.draw()
        self.canvas.enable_line_hover()

        # --- Solidus / Liquidus display (both K and C) ---
        temps_parts = []
        if result.solidus is not None:
            temps_parts.append(
                f"Solidus: {result.solidus:.0f} K "
                f"({k_to_c(result.solidus):.0f} \u00b0C)"
            )
        if result.liquidus is not None:
            temps_parts.append(
                f"Liquidus: {result.liquidus:.0f} K "
                f"({k_to_c(result.liquidus):.0f} \u00b0C)"
            )
        self.temps_label.setText(
            "  |  ".join(temps_parts) if temps_parts else ""
        )

        # --- Plain-English result summary ---
        n_phases = len(result.phase_fractions)
        comp_pct = x * 100
        summary_parts = [
            f"Your {el1}-{comp_pct:.1f}%{el2} alloy"
        ]
        if result.solidus is not None and result.liquidus is not None:
            mushy = result.liquidus - result.solidus
            summary_parts.append(
                f" melts between {result.solidus:.0f} K "
                f"({k_to_c(result.solidus):.0f} \u00b0C, solidus) and "
                f"{result.liquidus:.0f} K "
                f"({k_to_c(result.liquidus):.0f} \u00b0C, liquidus). "
                f"The 'mushy zone' spans {mushy:.0f} K."
            )
        elif result.solidus is not None:
            summary_parts.append(
                f" begins to melt at {result.solidus:.0f} K "
                f"({k_to_c(result.solidus):.0f} \u00b0C)."
            )
        elif result.liquidus is not None:
            summary_parts.append(
                f" is fully liquid above {result.liquidus:.0f} K "
                f"({k_to_c(result.liquidus):.0f} \u00b0C)."
            )
        else:
            summary_parts.append(
                " did not show a clear melting transition in this range."
            )
        summary_parts.append(
            f" {n_phases} distinct phase{'s were' if n_phases != 1 else ' was'} found."
        )

        # --- Educational context about solidus/liquidus ---
        if result.solidus is not None and result.liquidus is not None:
            summary_parts.append(
                "\n\nIn plain English: The solidus is where the first drop of "
                "liquid appears (melting begins). The liquidus is where the "
                "last bit of solid disappears (fully molten). Between them is "
                "the 'mushy zone' -- a mix of solid crystals and liquid metal, "
                "important for casting and welding."
            )
        elif result.solidus is not None:
            summary_parts.append(
                "\n\nIn plain English: The solidus is where the first drop of "
                "liquid appears -- below this temperature, the alloy is "
                "completely solid."
            )

        self.summary_label.setText("".join(summary_parts))
        self.summary_label.setVisible(True)

        # --- Sanity check ---
        warning = self._sanity_check(result, el1, el2)
        if warning:
            self.sanity_label.setText(f"Warning: {warning}")
            self.sanity_label.setVisible(True)
        else:
            self.sanity_label.setVisible(False)

        self.export_csv_btn.setEnabled(True)
        self.export_png_btn.setEnabled(True)
        self.status_label.setText(
            f"Stepping complete: {n_phases} phases found"
        )
        self.status_label.setStyleSheet("color: #81C784;")

        # Emit signal for history logging
        cond = {
            "T_min": self.t_min_spin.value(),
            "T_max": self.t_max_spin.value(),
            "X": x,
        }
        summary_text = self.summary_label.text()
        self.calculation_done.emit([el1, el2], cond, summary_text)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_csv(self):
        if not self._last_result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Stepping Data", "stepping.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return

        conditions = self._build_conditions_text()
        df = self._last_result.to_dataframe()

        try:
            with open(path, "w", newline="") as f:
                f.write(f"# CALPHAD Stepping Calculation\n")
                f.write(f"# Exported: {datetime.datetime.now().isoformat()}\n")
                f.write(f"# {conditions}\n")
                if self._last_result.solidus is not None:
                    f.write(
                        f"# Solidus: {format_temp(self._last_result.solidus)}\n"
                    )
                if self._last_result.liquidus is not None:
                    f.write(
                        f"# Liquidus: {format_temp(self._last_result.liquidus)}\n"
                    )
                f.write("#\n")
                df.to_csv(f, index=False)
            self.status_label.setText(f"Exported to {path}")
        except Exception as exc:
            QMessageBox.critical(
                self, "Export Failed",
                f"Could not write CSV file:\n\n{exc}"
            )

    def _export_png(self):
        if not self.canvas.is_materialized:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Stepping Plot", "stepping.png",
            "PNG Files (*.png);;All Files (*)"
        )
        if not path:
            return

        # Add metadata annotation to the figure before saving
        conditions = self._build_conditions_text()
        annotation = self.canvas.figure.text(
            0.01, 0.01, conditions,
            fontsize=7, color="#888888",
            transform=self.canvas.figure.transFigure,
            ha="left", va="bottom",
        )

        try:
            self.canvas.figure.savefig(
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
            # Remove the annotation so it doesn't accumulate on the canvas
            annotation.remove()
            self.canvas.draw()
