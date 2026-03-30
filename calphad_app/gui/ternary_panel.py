"""Ternary phase diagram panel — isothermal sections and isopleths."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QMessageBox, QProgressBar,
    QPushButton, QRadioButton, QButtonGroup, QScrollArea, QVBoxLayout, QWidget,
)
from gui.lazy_canvas import LazyCanvas
from pycalphad import Database

from core.calculations import calculate_ternary_isothermal, calculate_isopleth
from core.plotting import plot_ternary_isothermal, plot_isopleth
from core.units import k_to_c, c_to_k, format_temp
from core.error_helper import build_error_message
from gui.info_content import TAB_INFO


class TernaryIsothermalWorker(QThread):
    """Worker thread for ternary isothermal section calculation."""
    finished = pyqtSignal(object, str)

    def __init__(self, db, el1, el2, el3, temperature, pressure=101325.0):
        super().__init__()
        self.db = db
        self.el1 = el1
        self.el2 = el2
        self.el3 = el3
        self.temperature = temperature
        self.pressure = pressure

    def run(self):
        strategy, error = calculate_ternary_isothermal(
            self.db, self.el1, self.el2, self.el3,
            self.temperature, self.pressure,
        )
        self.finished.emit(strategy, error or "")


class IsoplethWorker(QThread):
    """Worker thread for isopleth calculation."""
    finished = pyqtSignal(object, str)

    def __init__(self, db, elements, fixed_el, fixed_comp, varied_el, t_min, t_max, pressure=101325.0):
        super().__init__()
        self.db = db
        self.elements = elements
        self.fixed_el = fixed_el
        self.fixed_comp = fixed_comp
        self.varied_el = varied_el
        self.t_min = t_min
        self.t_max = t_max
        self.pressure = pressure

    def run(self):
        strategy, error = calculate_isopleth(
            self.db, self.elements, self.fixed_el, self.fixed_comp,
            self.varied_el, self.t_min, self.t_max, self.pressure,
        )
        self.finished.emit(strategy, error or "")


class TernaryPanel(QWidget):
    """Panel for ternary phase diagram calculations."""

    calculation_done = pyqtSignal(list, dict, str)

    def __init__(self):
        super().__init__()
        self.db: Database | None = None
        self.elements: list[str] = []
        self._worker = None
        self._temp_unit: str = "K"
        self._comp_unit: str = "mole_fraction"
        self._setup_ui()

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

        title = QLabel("Ternary Phase Diagram")
        title.setObjectName("heading")
        layout.addWidget(title)

        # --- Educational info panel ---
        info_data = TAB_INFO.get("ternary", {})
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

        # Element selection
        el_group = QGroupBox("Elements (select 3)")
        el_layout = QHBoxLayout()

        el_layout.addWidget(QLabel("Element 1:"))
        self.el1_combo = QComboBox()
        self.el1_combo.setToolTip("Base element (e.g. AL for aluminum alloys)")
        el_layout.addWidget(self.el1_combo)

        el_layout.addWidget(QLabel("Element 2:"))
        self.el2_combo = QComboBox()
        self.el2_combo.setToolTip("Second element")
        el_layout.addWidget(self.el2_combo)

        el_layout.addWidget(QLabel("Element 3:"))
        self.el3_combo = QComboBox()
        self.el3_combo.setToolTip("Third element")
        el_layout.addWidget(self.el3_combo)

        el_group.setLayout(el_layout)
        layout.addWidget(el_group)

        # Mode selection
        mode_group = QGroupBox("Calculation Mode")
        mode_layout = QVBoxLayout()

        self.mode_btn_group = QButtonGroup()
        self.iso_radio = QRadioButton("Isothermal Section — all phase regions at one temperature")
        self.iso_radio.setToolTip(
            "Shows all phase regions at a single temperature.\n"
            "Like a horizontal slice through 3D composition-temperature space.\n"
            "Result is a triangular phase diagram."
        )
        self.iso_radio.setChecked(True)
        self.isopleth_radio = QRadioButton("Isopleth — fix one element, sweep temperature")
        self.isopleth_radio.setToolTip(
            "Fixes one element's composition and shows how phases change with temperature.\n"
            "Like looking at a vertical slice through the ternary system.\n"
            "Result looks like a binary phase diagram."
        )
        self.mode_btn_group.addButton(self.iso_radio, 0)
        self.mode_btn_group.addButton(self.isopleth_radio, 1)
        mode_layout.addWidget(self.iso_radio)
        mode_layout.addWidget(self.isopleth_radio)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        self.mode_btn_group.idClicked.connect(self._on_mode_changed)

        # Isothermal settings
        self.iso_group = QGroupBox("Isothermal Settings")
        iso_layout = QHBoxLayout()
        iso_layout.addWidget(QLabel("Temperature (K):"))
        self.iso_temp_spin = QDoubleSpinBox()
        self.iso_temp_spin.setRange(100, 5000)
        self.iso_temp_spin.setValue(800)
        self.iso_temp_spin.setSingleStep(50)
        self.iso_temp_spin.setToolTip(
            "Temperature for the isothermal section.\n"
            "All phases shown are stable at this temperature.\n"
            "Try values near eutectic temperatures for interesting diagrams."
        )
        iso_layout.addWidget(self.iso_temp_spin)
        iso_layout.addStretch()
        self.iso_group.setLayout(iso_layout)
        layout.addWidget(self.iso_group)

        # Isopleth settings
        self.isopleth_group = QGroupBox("Isopleth Settings")
        isopleth_layout = QHBoxLayout()

        isopleth_layout.addWidget(QLabel("Fix:"))
        self.fixed_el_combo = QComboBox()
        self.fixed_el_combo.setToolTip("Element whose composition is held constant")
        isopleth_layout.addWidget(self.fixed_el_combo)

        isopleth_layout.addWidget(QLabel("at X ="))
        self.fixed_comp_spin = QDoubleSpinBox()
        self.fixed_comp_spin.setRange(0.001, 0.999)
        self.fixed_comp_spin.setDecimals(4)
        self.fixed_comp_spin.setSingleStep(0.01)
        self.fixed_comp_spin.setValue(0.10)
        self.fixed_comp_spin.setToolTip("Mole fraction of the fixed element (0-1)")
        isopleth_layout.addWidget(self.fixed_comp_spin)

        isopleth_layout.addWidget(QLabel("Vary:"))
        self.varied_el_combo = QComboBox()
        self.varied_el_combo.setToolTip("Element whose composition varies on the X-axis")
        isopleth_layout.addWidget(self.varied_el_combo)

        isopleth_layout.addWidget(QLabel("T min:"))
        self.t_min_spin = QDoubleSpinBox()
        self.t_min_spin.setRange(100, 5000)
        self.t_min_spin.setValue(300)
        self.t_min_spin.setSingleStep(50)
        isopleth_layout.addWidget(self.t_min_spin)

        isopleth_layout.addWidget(QLabel("T max:"))
        self.t_max_spin = QDoubleSpinBox()
        self.t_max_spin.setRange(100, 5000)
        self.t_max_spin.setValue(1200)
        self.t_max_spin.setSingleStep(50)
        isopleth_layout.addWidget(self.t_max_spin)

        self.isopleth_group.setLayout(isopleth_layout)
        self.isopleth_group.setVisible(False)
        layout.addWidget(self.isopleth_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.calc_btn = QPushButton("Calculate Ternary")
        self.calc_btn.setObjectName("primary")
        self.calc_btn.setEnabled(False)
        self.calc_btn.setToolTip("Load a database with at least 3 elements first")
        self.calc_btn.clicked.connect(self._calculate)
        btn_layout.addWidget(self.calc_btn)

        self.export_png_btn = QPushButton("Export PNG")
        self.export_png_btn.setObjectName("success")
        self.export_png_btn.setEnabled(False)
        self.export_png_btn.clicked.connect(self._export_png)
        btn_layout.addWidget(self.export_png_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(
            "color: #ccccdd; background: #1e2a3e; "
            "border-radius: 4px; padding: 8px; font-size: 12px;"
        )
        self.summary_label.setVisible(False)
        layout.addWidget(self.summary_label)

        # Plot
        self.canvas = LazyCanvas(figsize=(8, 6), dpi=100)
        self.canvas.setMinimumHeight(400)
        layout.addWidget(self.canvas, stretch=1)

        scroll.setWidget(container)
        outer.addWidget(scroll)

    def _on_mode_changed(self, mode_id: int):
        self.iso_group.setVisible(mode_id == 0)
        self.isopleth_group.setVisible(mode_id == 1)

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

        for combo in (self.el1_combo, self.el2_combo, self.el3_combo,
                      self.fixed_el_combo, self.varied_el_combo):
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(elements)
            combo.blockSignals(False)

        if len(elements) >= 3:
            self.el2_combo.setCurrentIndex(1)
            self.el3_combo.setCurrentIndex(2)
            self.fixed_el_combo.setCurrentIndex(2)
            self.varied_el_combo.setCurrentIndex(1)
            self.calc_btn.setEnabled(True)
            self.calc_btn.setToolTip("Calculate a ternary phase diagram with the selected elements")

    def set_temp_unit(self, unit: str) -> None:
        if unit == self._temp_unit:
            return
        old_unit = self._temp_unit
        self._temp_unit = unit

        # Convert isothermal temp
        old_iso = self.iso_temp_spin.value()
        old_tmin = self.t_min_spin.value()
        old_tmax = self.t_max_spin.value()

        if old_unit == "K" and unit == "C":
            self.iso_temp_spin.setRange(-273, 4727)
            self.iso_temp_spin.setValue(k_to_c(old_iso))
            self.t_min_spin.setRange(-273, 4727)
            self.t_max_spin.setRange(-273, 4727)
            self.t_min_spin.setValue(k_to_c(old_tmin))
            self.t_max_spin.setValue(k_to_c(old_tmax))
        elif old_unit == "C" and unit == "K":
            self.iso_temp_spin.setRange(100, 5000)
            self.iso_temp_spin.setValue(c_to_k(old_iso))
            self.t_min_spin.setRange(100, 5000)
            self.t_max_spin.setRange(100, 5000)
            self.t_min_spin.setValue(c_to_k(old_tmin))
            self.t_max_spin.setValue(c_to_k(old_tmax))

    def set_comp_unit(self, unit: str) -> None:
        self._comp_unit = unit

    def _calculate(self):
        if not self.db:
            return
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(self, "Busy", "Calculation already in progress.")
            return

        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()
        el3 = self.el3_combo.currentText()

        if len({el1, el2, el3}) < 3:
            QMessageBox.warning(self, "Input Error", "Please select three different elements.")
            return

        self.calc_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.summary_label.setVisible(False)

        if self.iso_radio.isChecked():
            temp = self.iso_temp_spin.value()
            if self._temp_unit == "C":
                temp = c_to_k(temp)
            self.status_label.setText(f"Calculating isothermal section at {temp:.0f} K...")
            self.status_label.setStyleSheet("color: #FFB74D;")
            self._worker = TernaryIsothermalWorker(self.db, el1, el2, el3, temp)
            self._worker.finished.connect(self._on_isothermal_done)
            self._worker.start()
        else:
            fixed_el = self.fixed_el_combo.currentText()
            fixed_comp = self.fixed_comp_spin.value()
            varied_el = self.varied_el_combo.currentText()
            t_min = self.t_min_spin.value()
            t_max = self.t_max_spin.value()
            if self._temp_unit == "C":
                t_min = c_to_k(t_min)
                t_max = c_to_k(t_max)
            elements = [el1, el2, el3]
            self.status_label.setText(f"Calculating isopleth ({fixed_el}={fixed_comp:.2f})...")
            self.status_label.setStyleSheet("color: #FFB74D;")
            self._worker = IsoplethWorker(
                self.db, elements, fixed_el, fixed_comp, varied_el, t_min, t_max,
            )
            self._worker.finished.connect(self._on_isopleth_done)
            self._worker.start()

    def _on_isothermal_done(self, strategy, error: str):
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(True)

        if error:
            self.status_label.setText("Calculation failed")
            self.status_label.setStyleSheet("color: #E57373;")
            el1 = self.el1_combo.currentText()
            el2 = self.el2_combo.currentText()
            el3 = self.el3_combo.currentText()
            temp = self.iso_temp_spin.value()
            if self._temp_unit == "C":
                temp = c_to_k(temp)
            friendly, technical = build_error_message(
                raw_error=error, db=self.db,
                calc_type="ternary isothermal section",
                elements_used=[el1, el2, el3],
                temperature=temp,
            )
            QMessageBox.warning(
                self, "Calculation Did Not Succeed",
                f"{friendly}\n\n{technical}",
            )
            return

        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()
        el3 = self.el3_combo.currentText()
        temp = self.iso_temp_spin.value()
        if self._temp_unit == "C":
            temp = c_to_k(temp)

        plot_ternary_isothermal(self.canvas.figure, strategy, el1, el2, el3, temp)
        self.canvas.draw()
        self.export_png_btn.setEnabled(True)
        self.status_label.setText(f"Isothermal section: {el1}-{el2}-{el3} at {format_temp(temp)}")
        self.status_label.setStyleSheet("color: #81C784;")

        self.summary_label.setText(
            f"Ternary isothermal section for {el1}-{el2}-{el3} at {format_temp(temp)}. "
            f"This diagram shows which phases are stable at every possible "
            f"composition of these three elements at this temperature."
        )
        self.summary_label.setVisible(True)

        self.calculation_done.emit(
            [el1, el2, el3],
            {"T": temp, "mode": "isothermal"},
            f"Isothermal {el1}-{el2}-{el3} at {temp:.0f} K",
        )

    def _on_isopleth_done(self, strategy, error: str):
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(True)

        if error:
            self.status_label.setText("Calculation failed")
            self.status_label.setStyleSheet("color: #E57373;")
            el1 = self.el1_combo.currentText()
            el2 = self.el2_combo.currentText()
            el3 = self.el3_combo.currentText()
            friendly, technical = build_error_message(
                raw_error=error, db=self.db,
                calc_type="isopleth",
                elements_used=[el1, el2, el3],
            )
            QMessageBox.warning(
                self, "Calculation Did Not Succeed",
                f"{friendly}\n\n{technical}",
            )
            return

        fixed_el = self.fixed_el_combo.currentText()
        fixed_comp = self.fixed_comp_spin.value()
        varied_el = self.varied_el_combo.currentText()
        t_min = self.t_min_spin.value()
        t_max = self.t_max_spin.value()
        if self._temp_unit == "C":
            t_min = c_to_k(t_min)
            t_max = c_to_k(t_max)

        plot_isopleth(self.canvas.figure, strategy, varied_el, fixed_el, fixed_comp, t_min, t_max)
        self.canvas.draw()
        self.export_png_btn.setEnabled(True)

        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()
        el3 = self.el3_combo.currentText()
        self.status_label.setText(
            f"Isopleth: {el1}-{el2}-{el3}, {fixed_el}={fixed_comp:.2f}"
        )
        self.status_label.setStyleSheet("color: #81C784;")

        self.summary_label.setText(
            f"Isopleth (pseudo-binary) for {el1}-{el2}-{el3} with "
            f"{fixed_el} fixed at {fixed_comp:.2f} mole fraction. "
            f"The X-axis shows {varied_el} composition, Y-axis shows temperature. "
            f"This is like a binary phase diagram, but within a ternary system."
        )
        self.summary_label.setVisible(True)

        self.calculation_done.emit(
            [el1, el2, el3],
            {"fixed_el": fixed_el, "fixed_comp": fixed_comp, "mode": "isopleth",
             "T_min": t_min, "T_max": t_max},
            f"Isopleth {el1}-{el2}-{el3}, {fixed_el}={fixed_comp:.2f}",
        )

    def _export_png(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Ternary Diagram", "ternary.png",
            "PNG Files (*.png);;All Files (*)",
        )
        if path:
            self.canvas.figure.savefig(path, dpi=150, facecolor="#1e1e2e")
            self.status_label.setText(f"Exported to {path}")
