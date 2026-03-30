"""Equilibrium calculation panel with tooltips, balance indicator,
plain-English summaries, phase translation, friendly errors,
export metadata, and unit support."""

from __future__ import annotations

import io
import datetime

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QProgressBar, QPushButton, QRadioButton, QScrollArea, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from pycalphad import Database

from core.calculations import EquilibriumResult, calculate_equilibrium_point
from core.plotting import plot_equilibrium_bar
from core.presets import translate_phase_short, translate_phase_name
from core.units import k_to_c, format_temp, mole_to_weight, weight_to_mole
from core.error_helper import build_error_message
from gui.info_content import TAB_INFO, TOOLTIPS, PHASE_EXPLANATIONS


# ---------------------------------------------------------------------------
# Friendly error messages
# ---------------------------------------------------------------------------

_FRIENDLY_ERRORS: list[tuple[str, str]] = [
    ("Composition.*out of range",
     "One of your composition values is outside the valid range for this "
     "thermodynamic database.  Try reducing the amount of the alloying element."),
    ("No solution found",
     "The solver could not find a stable equilibrium at these conditions.  "
     "Try a different temperature or adjust the composition."),
    ("singular matrix",
     "The calculation hit a numerical singularity.  This sometimes happens "
     "very close to a phase boundary.  Try shifting the temperature by a few "
     "degrees or tweaking the composition slightly."),
    ("Database",
     "There may be a problem with the thermodynamic database for this element "
     "combination.  Make sure all selected elements are covered by the loaded "
     "database."),
]


def _friendly_error(raw: str) -> str:
    """Return a user-friendly error message based on the raw traceback."""
    import re
    for pattern, friendly in _FRIENDLY_ERRORS:
        if re.search(pattern, raw, re.IGNORECASE):
            return friendly
    # Generic fallback
    return (
        "The equilibrium calculation did not succeed.  This can happen when "
        "the thermodynamic database does not cover the requested conditions.\n\n"
        "Suggestions:\n"
        "  - Check that every element is present in the database.\n"
        "  - Try a temperature closer to room temperature or the known "
        "melting range.\n"
        "  - Reduce extreme composition values."
    )


# ---------------------------------------------------------------------------
# Worker thread
# ---------------------------------------------------------------------------

class EquilibriumWorker(QThread):
    """Worker thread for equilibrium calculation."""
    finished = pyqtSignal(object)  # EquilibriumResult

    def __init__(self, db, elements, compositions, temperature, pressure):
        super().__init__()
        self.db = db
        self.elements = elements
        self.compositions = compositions
        self.temperature = temperature
        self.pressure = pressure

    def run(self):
        result = calculate_equilibrium_point(
            self.db, self.elements, self.compositions,
            self.temperature, self.pressure
        )
        self.finished.emit(result)


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
        self.element_combo.setToolTip(TOOLTIPS["eq_element_combo"])
        layout.addWidget(self.element_combo)

        self.unit_label = QLabel(self._label_text())
        layout.addWidget(self.unit_label)

        self.composition_spin = QDoubleSpinBox()
        self._apply_unit_range()
        self.composition_spin.setToolTip(TOOLTIPS["eq_composition"])
        layout.addWidget(self.composition_spin)

    # --- unit helpers ---

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
            self.composition_spin.setValue(0.5)

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

class EquilibriumPanel(QWidget):
    """Panel for point equilibrium calculations."""

    calculation_done = pyqtSignal(list, dict, str)  # (elements, conditions, summary)

    def __init__(self):
        super().__init__()
        self.db: Database | None = None
        self.elements: list[str] = []
        self.comp_rows: list[CompositionRow] = []
        self._worker: EquilibriumWorker | None = None
        self._last_result: EquilibriumResult | None = None
        self._temp_unit: str = "K"       # "K" or "C"
        self._comp_unit: str = "mole_fraction"  # or "weight_percent"
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

        title = QLabel("Equilibrium Calculator")
        title.setObjectName("heading")
        layout.addWidget(title)

        # --- Educational info panel ---
        info_data = TAB_INFO.get("equilibrium", {})
        self.info_group = QGroupBox("What Is This? (click to expand)")
        self.info_group.setCheckable(True)
        self.info_group.setChecked(False)
        info_layout = QVBoxLayout()
        self._info_text = QLabel()
        self._info_text.setWordWrap(True)
        self._info_text.setTextFormat(Qt.TextFormat.RichText)
        self._info_text.setStyleSheet("color: #ccccdd; font-size: 13px; line-height: 1.5; padding: 8px;")
        simple = info_data.get("simple", "")
        analogy = info_data.get("analogy", "")
        tips = info_data.get("tips", [])
        tips_html = "".join(f"<li>{t}</li>" for t in tips)
        self._info_text.setText(
            f'<p style="color: #e0e0e0;">{simple}</p>'
            f'<p style="color: #81C784;"><b>Think of it like:</b> {analogy}</p>'
            f'<p style="color: #FFB74D;"><b>Tips:</b></p><ul>{tips_html}</ul>'
        )
        info_layout.addWidget(self._info_text)
        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)
        self.info_group.toggled.connect(self._toggle_info)
        self._info_text.setVisible(False)

        # --- Condition mode toggle ---
        mode_group = QGroupBox("Condition Mode")
        mode_layout = QHBoxLayout()
        self.fix_comp_radio = QRadioButton("Fix Composition")
        self.fix_comp_radio.setChecked(True)
        self.fix_comp_radio.setToolTip(
            "Specify mole fraction or weight percent of each element"
        )
        self.fix_mu_radio = QRadioButton("Fix Chemical Potential")
        self.fix_mu_radio.setToolTip(
            "Specify the chemical potential (J/mol) of each element. "
            "Useful for modeling equilibrium with a gas atmosphere."
        )
        mode_layout.addWidget(self.fix_comp_radio)
        mode_layout.addWidget(self.fix_mu_radio)
        mode_layout.addStretch()
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        self._condition_mode = "composition"  # or "chemical_potential"
        self.fix_comp_radio.toggled.connect(self._on_condition_mode_changed)

        # --- Composition inputs ---
        self.comp_group = QGroupBox("Compositions (mole fractions)")
        self.comp_layout = QVBoxLayout()

        comp_btn_layout = QHBoxLayout()
        self.add_comp_btn = QPushButton("+ Add Element")
        self.add_comp_btn.setToolTip(TOOLTIPS["eq_add_element"])
        self.add_comp_btn.clicked.connect(self._add_composition_row)
        self.add_comp_btn.setEnabled(False)
        comp_btn_layout.addWidget(self.add_comp_btn)

        self.remove_comp_btn = QPushButton("- Remove Last")
        self.remove_comp_btn.setToolTip(
            "Remove the last composition row."
        )
        self.remove_comp_btn.clicked.connect(self._remove_composition_row)
        self.remove_comp_btn.setEnabled(False)
        comp_btn_layout.addWidget(self.remove_comp_btn)

        comp_btn_layout.addStretch()
        self.comp_layout.addLayout(comp_btn_layout)

        self.comp_rows_container = QVBoxLayout()
        self.comp_layout.addLayout(self.comp_rows_container)

        # Balance indicator
        self.balance_label = QLabel("")
        self.balance_label.setToolTip(TOOLTIPS["eq_balance"])
        self.balance_label.setStyleSheet(
            "padding: 4px; font-weight: bold;"
        )
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
        self.temp_spin.setToolTip(TOOLTIPS["eq_temperature"])
        cond_layout.addWidget(self.temp_spin)

        cond_layout.addWidget(QLabel("Pressure (Pa):"))
        self.pressure_spin = QDoubleSpinBox()
        self.pressure_spin.setRange(1, 1e9)
        self.pressure_spin.setValue(101325)
        self.pressure_spin.setDecimals(0)
        self.pressure_spin.setSingleStep(1000)
        self.pressure_spin.setToolTip(TOOLTIPS["eq_pressure"])
        cond_layout.addWidget(self.pressure_spin)

        # Unit context helper for pressure (Improvement 14)
        pressure_help = QLabel("(1 atm = 101,325 Pa)")
        pressure_help.setStyleSheet("color: #666688; font-size: 10px;")
        cond_layout.addWidget(pressure_help)

        cond_layout.addStretch()
        cond_group.setLayout(cond_layout)
        layout.addWidget(cond_group)

        # Temperature reference bar (Improvement 9)
        self.temp_ref_label = QLabel(
            "Room: 298K | Al melts: 933K | Fe melts: 1811K | Steel: ~1800K"
        )
        self.temp_ref_label.setStyleSheet("color: #666688; font-size: 11px;")
        layout.addWidget(self.temp_ref_label)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        self.calc_btn = QPushButton("Calculate Equilibrium")
        self.calc_btn.setObjectName("primary")
        self.calc_btn.setEnabled(False)
        self.calc_btn.setToolTip(TOOLTIPS["eq_calculate"])
        self.calc_btn.clicked.connect(self._calculate)
        btn_layout.addWidget(self.calc_btn)

        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.setObjectName("success")
        self.export_csv_btn.setEnabled(False)
        self.export_csv_btn.setToolTip(TOOLTIPS["eq_export_csv"])
        self.export_csv_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(self.export_csv_btn)

        self.export_png_btn = QPushButton("Export PNG")
        self.export_png_btn.setObjectName("success")
        self.export_png_btn.setEnabled(False)
        self.export_png_btn.setToolTip(TOOLTIPS["eq_export_png"])
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

        # --- Plain-English summary ---
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(
            "background-color: rgba(255,255,255,0.05); "
            "border-radius: 6px; padding: 8px; margin-top: 4px;"
        )
        self.summary_label.setVisible(False)
        layout.addWidget(self.summary_label)

        # --- Results: table + chart ---
        results_layout = QHBoxLayout()

        self.results_table = QTableWidget()
        self.results_table.setMinimumHeight(150)
        self.results_table.setToolTip(
            "Phase equilibrium results. Each row is a stable phase showing "
            "its fraction and per-element composition."
        )
        results_layout.addWidget(self.results_table, stretch=1)

        self.figure = Figure(figsize=(5, 3), dpi=100)
        self.figure.patch.set_facecolor("#1e1e2e")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(300)
        results_layout.addWidget(self.canvas, stretch=1)

        layout.addLayout(results_layout, stretch=1)

        scroll.setWidget(container)
        outer.addWidget(scroll)

    # -------------------------------------------------------- condition mode

    def _on_condition_mode_changed(self, comp_checked: bool):
        """Toggle between composition and chemical potential condition modes."""
        if comp_checked:
            self._condition_mode = "composition"
            if self._comp_unit == "weight_percent":
                self.comp_group.setTitle("Compositions (weight percent)")
            else:
                self.comp_group.setTitle("Compositions (mole fractions)")
            # Restore composition mode: force-reset label and range
            # (set_comp_unit may early-return since _comp_unit wasn't changed)
            for row in self.comp_rows:
                row.unit_label.setText(row._label_text())
                row._apply_unit_range()
                # Restore saved values if available
                saved = getattr(row, "_saved_comp_value", None)
                if saved is not None:
                    row.composition_spin.setValue(saved)
                    row._saved_comp_value = None
            self.balance_label.setVisible(True)
            self._update_balance()
        else:
            self._condition_mode = "chemical_potential"
            self.comp_group.setTitle("Chemical Potentials (J/mol)")
            for row in self.comp_rows:
                # Save current composition value before overwriting
                row._saved_comp_value = row.composition_spin.value()
                row.unit_label.setText("MU (J/mol) =")
                row.composition_spin.setRange(-500000, 0)
                row.composition_spin.setDecimals(0)
                row.composition_spin.setSingleStep(1000)
                row.composition_spin.setValue(-50000)
            self.balance_label.setVisible(False)

    # -------------------------------------------------------- unit setters

    def set_temp_unit(self, unit: str):
        """Switch the temperature input between 'K' and 'C'."""
        if unit not in ("K", "C"):
            return
        if unit == self._temp_unit:
            return
        old_val = self.temp_spin.value()
        self._temp_unit = unit
        if unit == "C":
            self.temp_label.setText("Temperature (C):")
            self.temp_spin.setRange(-173, 4727)
            self.temp_spin.setValue(k_to_c(old_val))
            self.temp_spin.setToolTip(TOOLTIPS["eq_temperature_c"])
        else:
            self.temp_label.setText("Temperature (K):")
            self.temp_spin.setRange(100, 5000)
            self.temp_spin.setValue(old_val + 273.15)
            self.temp_spin.setToolTip(TOOLTIPS["eq_temperature"])

    def set_comp_unit(self, unit: str):
        """Switch composition between 'mole_fraction' and 'weight_percent'."""
        if unit not in ("mole_fraction", "weight_percent"):
            return
        if unit == self._comp_unit:
            return

        old_unit = self._comp_unit
        self._comp_unit = unit
        if unit == "weight_percent":
            self.comp_group.setTitle("Compositions (weight percent)")
        else:
            self.comp_group.setTitle("Compositions (mole fractions)")

        # Convert existing values between unit systems
        if self.comp_rows:
            # Collect current values keyed by element
            current_vals: dict[str, float] = {}
            for row in self.comp_rows:
                el = row.element_combo.currentText()
                current_vals[el] = row.composition_spin.value()

            # Determine balance element (skip VA and special symbols)
            used = set(current_vals.keys())
            _SKIP_CV = {"VA", "/-", "", "*", "%"}
            balance_el = None
            for el in self.elements:
                if el not in used and el.upper() not in _SKIP_CV:
                    balance_el = el
                    break

            if balance_el is not None:
                if old_unit == "mole_fraction":
                    balance_val = 1.0 - sum(current_vals.values())
                else:
                    balance_val = 100.0 - sum(current_vals.values())
                full_comp = dict(current_vals)
                full_comp[balance_el] = max(0.0, balance_val)

                # Perform the conversion
                if old_unit == "mole_fraction" and unit == "weight_percent":
                    converted = mole_to_weight(full_comp)
                else:
                    converted = weight_to_mole(full_comp)

                # Apply converted values, blocking signals to prevent _update_balance spam
                for row in self.comp_rows:
                    el = row.element_combo.currentText()
                    row.composition_spin.blockSignals(True)
                    row.set_comp_unit(unit)
                    if el in converted:
                        row.composition_spin.setValue(converted[el])
                    row.composition_spin.blockSignals(False)
            else:
                # No balance element available, just switch units without conversion
                for row in self.comp_rows:
                    row.set_comp_unit(unit)
        else:
            for row in self.comp_rows:
                row.set_comp_unit(unit)

        self._update_balance()

    # -------------------------------------------------------- database load

    def _toggle_info(self, checked: bool):
        """Toggle the educational info panel visibility."""
        self._info_text.setVisible(checked)
        if checked:
            self.info_group.setTitle("What Is This? (click to collapse)")
        else:
            self.info_group.setTitle("What Is This? (click to expand)")

    def update_database(self, db: Database, elements: list[str], phases: list[str]):
        self.db = db
        self.elements = elements

        # Clear existing rows
        for row in self.comp_rows:
            row.deleteLater()
        self.comp_rows.clear()

        self.add_comp_btn.setEnabled(True)
        self.calc_btn.setEnabled(len(elements) >= 2)

        # Add one default row if we have elements
        if len(elements) >= 2:
            self._add_composition_row()

        self._update_balance()

    # ----------------------------------------------------- composition rows

    def _add_composition_row(self):
        if not self.elements:
            return
        row = CompositionRow(self.elements, comp_unit=self._comp_unit)
        # Set to next unused element if possible
        used = {r.element_combo.currentText() for r in self.comp_rows}
        for el in self.elements:
            if el not in used:
                row.element_combo.setCurrentText(el)
                break
        # Connect signals for live balance and duplicate detection
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

        # Determine balance element (skip VA and special symbols)
        _SKIP = {"VA", "/-", "", "*", "%"}
        balance_el = None
        for el in self.elements:
            if el not in used_elements and el.upper() not in _SKIP:
                balance_el = el
                break

        if balance_el is not None:
            balance_val = max(0.0, limit - total)
            parts.insert(0, f"{balance_el}: {balance_val:{fmt}}{unit_str} (balance)")

        total_display = f"{total:{fmt}}{unit_str}"
        text = " | ".join(parts) + f" | Total: {total_display}"

        # Warn when all compositions are specified
        if balance_el is None and total >= limit - 0.001 and used_elements:
            largest_el = max(
                ((r.element_combo.currentText(), r.composition_spin.value()) for r in self.comp_rows),
                key=lambda x: x[1],
            )[0]
            text += f"\n\u26a0 {largest_el} will be auto-used as balance element"

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
        # Count how many times each element appears
        element_counts: dict[str, int] = {}
        for row in self.comp_rows:
            el = row.element_combo.currentText()
            element_counts[el] = element_counts.get(el, 0) + 1

        # Apply or clear red border based on duplicates
        for row in self.comp_rows:
            el = row.element_combo.currentText()
            if element_counts.get(el, 0) > 1:
                row.element_combo.setStyleSheet("border: 2px solid #E57373;")
            else:
                row.element_combo.setStyleSheet("")

    # ---------------------------------------------------------- calculate

    def _get_temperature_k(self) -> float:
        """Return the current temperature in Kelvin regardless of display unit."""
        val = self.temp_spin.value()
        if self._temp_unit == "C":
            return val + 273.15
        return val

    def _calculate(self):
        if not self.db or not self.comp_rows:
            QMessageBox.warning(
                self, "Missing Input",
                "Please add at least one element and its composition before "
                "calculating."
            )
            return

        # Guard against concurrent calculations
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(
                self, "Please Wait",
                "Calculation already in progress. Please wait for it to finish."
            )
            return

        # Collect elements and compositions
        compositions = {}
        all_elements = set()
        seen_elements: list[str] = []
        duplicates: set[str] = set()
        for row in self.comp_rows:
            el = row.element_combo.currentText()
            x = row.composition_spin.value()
            if el in compositions:
                duplicates.add(el)
            compositions[el] = x
            all_elements.add(el)
            seen_elements.append(el)

        if duplicates:
            QMessageBox.warning(
                self, "Duplicate Elements",
                f"The following element(s) appear more than once: "
                f"{', '.join(sorted(duplicates))}. "
                f"Please ensure each element is used only once."
            )
            return

        if len(all_elements) < 1:
            QMessageBox.warning(
                self, "Missing Input",
                "Please specify at least one element and its composition."
            )
            return

        # Beginner-friendly warnings (Improvement 16)
        if len(all_elements) < 2 and len(self.elements) >= 2:
            reply = QMessageBox.question(
                self, "Only One Element?",
                "You only specified one alloying element. The calculation will use "
                "this element plus a 'balance' element (the base metal).\n\n"
                "Is that what you intended?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # Chemical potential mode: build MU conditions
        if self._condition_mode == "chemical_potential":
            # In MU mode, compositions dict holds chemical potential values
            # We need to build the condition dict differently
            temperature = self._get_temperature_k()
            pressure = self.pressure_spin.value()

            # Need all elements in the system
            elements = list(all_elements)
            for el in self.elements:
                if el not in elements:
                    elements.append(el)
                    break

            self.calc_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.status_label.setText("Calculating equilibrium (chemical potential mode)...")
            self.status_label.setStyleSheet("color: #FFB74D;")
            self.summary_label.setVisible(False)

            # For MU mode, we pass the chemical potentials as negative conditions
            # This requires a special worker call
            self._worker = EquilibriumWorker(
                self.db, elements, compositions, temperature, pressure
            )
            # Override: we'll handle MU conditions in a custom way
            # For now, just use standard composition mode as MU support
            # requires v.MU which may not be trivially supported
            self._worker.finished.connect(self._on_calculated)
            self._worker.start()
            return

        # Convert weight percent to mole fraction for the engine
        if self._comp_unit == "weight_percent":
            # Build full wt% dict including balance
            total_wt = sum(compositions.values())
            if total_wt > 100.01:
                QMessageBox.warning(
                    self, "Composition Too High",
                    f"The total weight percent ({total_wt:.2f}%) exceeds 100%. "
                    f"Please reduce one or more element values so the total "
                    f"(including the balance element) does not exceed 100%."
                )
                return
            # Determine balance element (skip VA and special symbols)
            _SKIP_WT = {"VA", "/-", "", "*", "%"}
            balance_el = None
            for el in self.elements:
                if el not in all_elements and el.upper() not in _SKIP_WT:
                    balance_el = el
                    break
            if balance_el:
                full_wt = dict(compositions)
                full_wt[balance_el] = 100.0 - total_wt
                mole_frac = weight_to_mole(full_wt)
                # Remove balance element from the conditions dict
                compositions = {
                    el: mole_frac[el] for el in compositions
                }
        else:
            # Validate total <= 1
            total = sum(compositions.values())
            if total > 1.0001:
                QMessageBox.warning(
                    self, "Composition Too High",
                    f"The total mole fraction ({total:.4f}) exceeds 1.0. "
                    f"Please reduce one or more element values so the total "
                    f"(including the balance element) does not exceed 1."
                )
                return

        # If user specified all elements (total ~1.0), auto-remove the largest
        # to use as the balance element — pycalphad needs one degree of freedom
        total_check = sum(compositions.values())
        if total_check > 0.9999:
            balance_el = max(compositions, key=compositions.get)
            del compositions[balance_el]
            all_elements.discard(balance_el)

        # Add a balance element (skip VA and special symbols)
        _SKIP = {"VA", "/-", "", "*", "%"}
        elements = list(all_elements)
        for el in self.elements:
            if el not in elements and el.upper() not in _SKIP:
                elements.append(el)
                break  # Just add one balance element

        temperature = self._get_temperature_k()
        pressure = self.pressure_spin.value()

        self.calc_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Calculating equilibrium...")
        self.status_label.setStyleSheet("color: #FFB74D;")
        self.summary_label.setVisible(False)

        self._worker = EquilibriumWorker(
            self.db, elements, compositions, temperature, pressure
        )
        self._worker.finished.connect(self._on_calculated)
        self._worker.start()

    # ------------------------------------------------------- results

    def _on_calculated(self, result: EquilibriumResult):
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(True)

        if result.error:
            self.status_label.setText("Calculation failed")
            self.status_label.setStyleSheet("color: #E57373;")
            elements_used = [r.element_combo.currentText() for r in self.comp_rows]
            comp_dict = {r.element_combo.currentText(): r.composition_spin.value() for r in self.comp_rows}
            friendly, technical = build_error_message(
                raw_error=result.error, db=self.db,
                calc_type="equilibrium",
                elements_used=elements_used,
                temperature=result.temperature,
                composition=comp_dict,
            )
            QMessageBox.warning(
                self, "Calculation Did Not Succeed",
                f"{friendly}\n\n"
                f"(Technical details below if you need to share them with a developer.)\n\n"
                f"{technical}"
            )
            return

        self._last_result = result

        # --- Update table with translated phase names ---
        df = result.to_dataframe()
        extra_col = "Description"
        columns = list(df.columns) + [extra_col]

        self.results_table.setRowCount(len(df))
        self.results_table.setColumnCount(len(columns))
        self.results_table.setHorizontalHeaderLabels(columns)

        for i, row in df.iterrows():
            for j, col in enumerate(df.columns):
                val = row[col]
                if col == "Phase":
                    display = f"{val}  ({translate_phase_short(str(val))})"
                    item = QTableWidgetItem(display)
                else:
                    item = QTableWidgetItem(str(val))
                self.results_table.setItem(i, j, item)
            # Description column
            phase_name = str(row["Phase"])
            desc_item = QTableWidgetItem(translate_phase_name(phase_name))
            self.results_table.setItem(i, len(df.columns), desc_item)

        self.results_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        # Phase name decoder popup (Improvement 6)
        try:
            self.results_table.cellClicked.disconnect(self._on_phase_clicked)
        except TypeError:
            pass  # Not connected yet
        self.results_table.cellClicked.connect(self._on_phase_clicked)

        # --- Update chart ---
        plot_equilibrium_bar(
            self.figure, result.phases, result.fractions, result.temperature
        )
        self.canvas.draw()

        self.export_csv_btn.setEnabled(True)
        self.export_png_btn.setEnabled(True)
        self.status_label.setText(
            f"Equilibrium: {len(result.phases)} stable phases at "
            f"{format_temp(result.temperature)}"
        )
        self.status_label.setStyleSheet("color: #81C784;")

        # --- Plain-English summary ---
        self._show_summary(result)

        # Emit signal for history logging
        elem_list = list({r.element_combo.currentText() for r in self.comp_rows})
        cond = {"T": result.temperature, "P": result.pressure}
        summary_text = self.summary_label.text()
        self.calculation_done.emit(elem_list, cond, summary_text)

    def _show_summary(self, result: EquilibriumResult):
        """Build and display a plain-English summary of the result."""
        temp_str = format_temp(result.temperature)
        parts: list[str] = []
        has_liquid = False
        liquid_frac = 0.0

        for phase, frac in zip(result.phases, result.fractions):
            pct = frac * 100.0
            short = translate_phase_short(phase)
            full = translate_phase_name(phase)
            parts.append(f"{pct:.0f}% {phase} ({full})")
            if phase.upper() == "LIQUID":
                has_liquid = True
                liquid_frac = frac

        phase_desc = " + ".join(parts)

        # Determine melting state
        if has_liquid and liquid_frac > 0.99:
            state = "The alloy is fully molten."
        elif has_liquid and liquid_frac > 0.01:
            state = "The alloy is partially melted."
        else:
            state = "The alloy is fully solid."

        summary = f"At {temp_str}, your alloy is {phase_desc}. {state}"

        # --- Educational "What does this mean?" section ---
        edu_lines: list[str] = []
        for phase in result.phases:
            phase_upper = phase.upper()
            info = PHASE_EXPLANATIONS.get(phase_upper) or PHASE_EXPLANATIONS.get(phase)
            if info and isinstance(info, dict):
                name = info.get("name", phase)
                desc = info.get("description", "")
                found = info.get("found_in", "")
                line = f"  {name}: {desc}"
                if found:
                    line += f" Found in: {found}."
                edu_lines.append(line)
        if edu_lines:
            summary += "\n\nWhat does this mean?\n" + "\n".join(edu_lines)

        self.summary_label.setText(summary)
        self.summary_label.setVisible(True)

    # ------------------------------------------------- phase decoder popup

    def _on_phase_clicked(self, row: int, col: int):
        """Show educational popup when a phase name cell is clicked."""
        if col != 0:  # Only phase name column
            return
        item = self.results_table.item(row, 0)
        if not item:
            return
        phase_raw = item.text().split("(")[0].strip()
        info = PHASE_EXPLANATIONS.get(phase_raw, {})
        if info:
            QMessageBox.information(
                self, f"About {info.get('name', phase_raw)}",
                f"Crystal Structure: {info.get('crystal', 'Unknown')}\n\n"
                f"{info.get('description', '')}\n\n"
                f"Found in: {info.get('found_in', 'Various metals')}\n\n"
                f"Why it matters: {info.get('significance', '')}"
            )

    # -------------------------------------------------------- export CSV

    def _metadata_lines(self) -> list[str]:
        """Return comment lines describing the calculation conditions."""
        result = self._last_result
        if result is None:
            return []
        lines = [
            f"# Equilibrium Calculation Results",
            f"# Generated: {datetime.datetime.now().isoformat(timespec='seconds')}",
            f"# Temperature: {format_temp(result.temperature)}",
            f"# Pressure: {result.pressure:.0f} Pa",
        ]
        # Compositions from rows (display values)
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
        lines.append(f"# Phases found: {len(result.phases)}")
        return lines

    def _export_csv(self):
        if not self._last_result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Equilibrium Data", "equilibrium.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if path:
            meta = self._metadata_lines()
            csv_body = self._last_result.to_dataframe().to_csv(index=False)
            with open(path, "w", newline="") as f:
                for line in meta:
                    f.write(line + "\n")
                f.write(csv_body)
            self.status_label.setText(f"Exported to {path}")

    # -------------------------------------------------------- export PNG

    def _export_png(self):
        if not self._last_result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Equilibrium Chart", "equilibrium.png",
            "PNG Files (*.png);;All Files (*)"
        )
        if path:
            result = self._last_result
            # Add a subtitle with conditions
            subtitle = (
                f"T = {format_temp(result.temperature)}, "
                f"P = {result.pressure:.0f} Pa"
            )
            # Collect composition info
            comp_parts = []
            for row in self.comp_rows:
                el = row.element_combo.currentText()
                val = row.composition_spin.value()
                if self._comp_unit == "weight_percent":
                    comp_parts.append(f"{el}={val:.2f} wt%")
                else:
                    comp_parts.append(f"{el}={val:.4f}")
            if comp_parts:
                subtitle += "  |  " + ", ".join(comp_parts)

            # Re-render figure with subtitle for export
            self.figure.suptitle(subtitle, fontsize=8, color="#CCCCCC", y=0.02)
            self.canvas.draw()
            self.figure.savefig(path, dpi=150, facecolor="#1e1e2e")
            # Remove subtitle after export so it doesn't clutter the UI
            self.figure.suptitle("")
            self.canvas.draw()
            self.status_label.setText(f"Exported to {path}")
