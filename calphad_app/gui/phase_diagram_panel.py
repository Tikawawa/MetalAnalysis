"""Phase diagram calculation and plotting panel."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QSplitter, QVBoxLayout, QWidget,
)
from gui.lazy_canvas import LazyCanvas
from pycalphad import Database

from core.calculations import calculate_binary_phase_diagram
from core.plotting import plot_binary_phase_diagram, build_phase_region_lookup
from core.presets import get_binary_preset, translate_phase_short
from core.units import k_to_c, c_to_k, format_temp
from core.error_helper import build_error_message
from gui.info_content import TAB_INFO, TOOLTIPS


class PhaseDiagramWorker(QThread):
    """Worker thread for phase diagram calculation."""
    finished = pyqtSignal(object, str)  # (strategy, error)

    def __init__(self, db, el1, el2, t_min, t_max):
        super().__init__()
        self.db = db
        self.el1 = el1
        self.el2 = el2
        self.t_min = t_min
        self.t_max = t_max

    def run(self):
        strategy, error = calculate_binary_phase_diagram(
            self.db, self.el1, self.el2, self.t_min, self.t_max
        )
        self.finished.emit(strategy, error or "")


class PhaseDiagramPanel(QWidget):
    """Panel for binary phase diagram calculations."""

    calculation_done = pyqtSignal(list, dict, str)  # (elements, conditions, summary)

    def __init__(self):
        super().__init__()
        self.db: Database | None = None
        self.elements: list[str] = []
        self._worker: PhaseDiagramWorker | None = None
        self._temp_unit: str = "K"
        self._comp_unit: str = "mole_fraction"
        self._last_strategy = None
        self._last_t_min_k = 300.0
        self._last_t_max_k = 2000.0
        self._compare_mode: bool = False
        self._phase_lookup: list[tuple[float, float, str]] = []
        self._hover_annotation = None
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
        layout.setSpacing(6)

        title = QLabel("Binary Phase Diagram")
        title.setObjectName("heading")
        layout.addWidget(title)

        # --- Educational info panel ---
        info_data = TAB_INFO.get("phase_diagram", {})
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

        # Controls
        controls_group = QGroupBox("Parameters")
        controls_layout = QHBoxLayout()

        # Element selectors
        el1_label = QLabel("Element 1:")
        el1_label.setToolTip(TOOLTIPS["pd_el1"])
        controls_layout.addWidget(el1_label)
        self.el1_combo = QComboBox()
        self.el1_combo.setToolTip(TOOLTIPS["pd_el1"])
        self.el1_combo.currentTextChanged.connect(self._on_element_changed)
        controls_layout.addWidget(self.el1_combo)

        el2_label = QLabel("Element 2:")
        el2_label.setToolTip(TOOLTIPS["pd_el2"])
        controls_layout.addWidget(el2_label)
        self.el2_combo = QComboBox()
        self.el2_combo.setToolTip(TOOLTIPS["pd_el2"])
        self.el2_combo.currentTextChanged.connect(self._on_element_changed)
        controls_layout.addWidget(self.el2_combo)

        # Temperature range
        self.t_min_label = QLabel("T min (K):")
        self.t_min_label.setToolTip(TOOLTIPS["pd_t_min"])
        controls_layout.addWidget(self.t_min_label)
        self.t_min_spin = QDoubleSpinBox()
        self.t_min_spin.setRange(100, 5000)
        self.t_min_spin.setValue(300)
        self.t_min_spin.setSingleStep(50)
        self.t_min_spin.setToolTip(TOOLTIPS["pd_t_min"])
        controls_layout.addWidget(self.t_min_spin)

        self.t_max_label = QLabel("T max (K):")
        self.t_max_label.setToolTip(TOOLTIPS["pd_t_max"])
        controls_layout.addWidget(self.t_max_label)
        self.t_max_spin = QDoubleSpinBox()
        self.t_max_spin.setRange(100, 5000)
        self.t_max_spin.setValue(2000)
        self.t_max_spin.setSingleStep(50)
        self.t_max_spin.setToolTip(TOOLTIPS["pd_t_max"])
        controls_layout.addWidget(self.t_max_spin)

        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)

        # Info label for system preset suggestions
        self.info_label = QLabel("")
        self.info_label.setObjectName("info")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet(
            "color: #64B5F6; font-style: italic; padding: 2px 8px;"
        )
        layout.addWidget(self.info_label)

        # Buttons
        btn_layout = QHBoxLayout()
        self.calc_btn = QPushButton("Calculate Phase Diagram")
        self.calc_btn.setObjectName("primary")
        self.calc_btn.setEnabled(False)
        self.calc_btn.setToolTip(TOOLTIPS["pd_calculate"])
        self.calc_btn.clicked.connect(self._calculate)
        btn_layout.addWidget(self.calc_btn)

        self.export_png_btn = QPushButton("Export PNG")
        self.export_png_btn.setObjectName("success")
        self.export_png_btn.setEnabled(False)
        self.export_png_btn.setToolTip(TOOLTIPS["pd_export_png"])
        self.export_png_btn.clicked.connect(self._export_png)
        btn_layout.addWidget(self.export_png_btn)

        self.compare_btn = QPushButton("Compare")
        self.compare_btn.setEnabled(False)
        self.compare_btn.setToolTip(TOOLTIPS["pd_compare"])
        self.compare_btn.setStyleSheet(
            "QPushButton { background-color: #0f3460; color: #CE93D8; "
            "border: 1px solid #CE93D8; border-radius: 5px; padding: 8px 18px; "
            "font-weight: bold; min-height: 28px; }"
            "QPushButton:hover { background-color: #1a4a7a; }"
            "QPushButton:disabled { background-color: #222244; color: #555577; "
            "border-color: #333355; }"
        )
        self.compare_btn.clicked.connect(self._toggle_compare)
        btn_layout.addWidget(self.compare_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setToolTip("Calculation is running in the background.")
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)

        # Summary label for post-calculation results
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("summary")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(
            "color: #AED581; padding: 4px 8px; font-size: 13px;"
        )
        layout.addWidget(self.summary_label)

        # Plot area with compare splitter
        self.plot_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Main (right-side / only) canvas
        self.canvas = LazyCanvas(figsize=(8, 6), dpi=100)
        self.canvas.setMinimumHeight(400)
        self.canvas.setToolTip("")

        # Compare (left-side) canvas -- hidden by default
        self.compare_canvas = LazyCanvas(figsize=(8, 6), dpi=100)
        self.compare_canvas.setMinimumHeight(400)
        self.compare_canvas.setVisible(False)

        self.plot_splitter.addWidget(self.compare_canvas)
        self.plot_splitter.addWidget(self.canvas)
        layout.addWidget(self.plot_splitter, stretch=1)

        # Connect canvas mouse events
        self.canvas.mpl_connect("button_press_event", self._on_canvas_click)
        self.canvas.mpl_connect("motion_notify_event", self._on_canvas_move)

        scroll.setWidget(container)
        outer.addWidget(scroll)

    # ------------------------------------------------------------------
    # Temperature unit support
    # ------------------------------------------------------------------

    def set_temp_unit(self, unit: str) -> None:
        """Set the display temperature unit ('K' or 'C'), convert spinbox
        values, and update labels."""
        old_unit = self._temp_unit
        self._temp_unit = unit.upper().strip()
        if self._temp_unit not in ("K", "C"):
            self._temp_unit = "K"

        # Convert spinbox values when the unit actually changes
        if old_unit != self._temp_unit:
            old_min = self.t_min_spin.value()
            old_max = self.t_max_spin.value()
            if self._temp_unit == "C":
                # Switching from K to C
                self.t_min_spin.setRange(-273, 4727)
                self.t_max_spin.setRange(-273, 4727)
                self.t_min_spin.setValue(k_to_c(old_min))
                self.t_max_spin.setValue(k_to_c(old_max))
            else:
                # Switching from C to K
                self.t_min_spin.setRange(100, 5000)
                self.t_max_spin.setRange(100, 5000)
                self.t_min_spin.setValue(c_to_k(old_min))
                self.t_max_spin.setValue(c_to_k(old_max))

        self._update_temp_labels()

    def set_comp_unit(self, unit: str) -> None:
        """Set the composition display unit for the X-axis."""
        self._comp_unit = unit

    def _update_temp_labels(self) -> None:
        """Refresh the T-min / T-max labels to reflect the current unit."""
        if self._temp_unit == "C":
            self.t_min_label.setText("T min (\u00b0C):")
            self.t_max_label.setText("T max (\u00b0C):")
        else:
            t_min_c = k_to_c(self.t_min_spin.value())
            t_max_c = k_to_c(self.t_max_spin.value())
            self.t_min_label.setText(f"T min (K / {t_min_c:.0f} \u00b0C):")
            self.t_max_label.setText(f"T max (K / {t_max_c:.0f} \u00b0C):")

    # ------------------------------------------------------------------
    # Element change handler -- auto-fill temperature range
    # ------------------------------------------------------------------

    def _on_element_changed(self) -> None:
        """Called when either element combo changes. Auto-fills temperature range
        from binary presets and shows an info label."""
        el1 = self.el1_combo.currentText().strip()
        el2 = self.el2_combo.currentText().strip()
        if not el1 or not el2 or el1 == el2:
            self.info_label.setText("")
            return

        preset = get_binary_preset(el1, el2)
        if preset is not None:
            self.t_min_spin.setValue(preset.t_min_k)
            self.t_max_spin.setValue(preset.t_max_k)

            info_parts = [
                f"Suggested for {el1}-{el2}: "
                f"{format_temp(preset.t_min_k)}\u2013{format_temp(preset.t_max_k)}."
            ]
            if preset.eutectic_t_k is not None:
                info_parts.append(
                    f"Eutectic at {format_temp(preset.eutectic_t_k)}."
                )
            if preset.description:
                info_parts.append(preset.description + ".")
            self.info_label.setText("  ".join(info_parts))
            self.info_label.setStyleSheet("color: #4FC3F7;")
        else:
            known = "Al-Cu, Al-Si, Al-Mg, Al-Zn, Mg-Al, Mg-Zn, Cu-Zn, Cu-Sn, Fe-C, Fe-Cr, Ti-Al"
            self.info_label.setText(
                f"No common alloys use {el1}-{el2}. "
                f"Known systems: {known}."
            )
            self.info_label.setStyleSheet("color: #FFB74D;")

        self._update_temp_labels()

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

        # Block signals while populating to avoid repeated _on_element_changed
        self.el1_combo.blockSignals(True)
        self.el2_combo.blockSignals(True)

        self.el1_combo.clear()
        self.el2_combo.clear()
        self.el1_combo.addItems(elements)
        self.el2_combo.addItems(elements)

        if len(elements) >= 2:
            self.el2_combo.setCurrentIndex(1)
            self.calc_btn.setEnabled(True)

        self.el1_combo.blockSignals(False)
        self.el2_combo.blockSignals(False)

        # Trigger preset lookup now that both combos are populated
        self._on_element_changed()

    # ------------------------------------------------------------------
    # Calculation
    # ------------------------------------------------------------------

    def _calculate(self):
        if not self.db:
            return

        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()

        if el1 == el2:
            QMessageBox.warning(self, "Input Error", "Please select two different elements.")
            return

        t_min = self.t_min_spin.value()
        t_max = self.t_max_spin.value()

        # The calculation always needs Kelvin
        if self._temp_unit == "C":
            t_min = c_to_k(t_min)
            t_max = c_to_k(t_max)

        self._last_t_min_k = t_min  # t_min is already in K at this point
        self._last_t_max_k = t_max

        if t_min >= t_max:
            QMessageBox.warning(self, "Input Error", "T min must be less than T max.")
            return

        self.calc_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.summary_label.setText("")
        self.status_label.setText("Calculating phase diagram... This may take a minute.")
        self.status_label.setStyleSheet("color: #FFB74D;")

        self._worker = PhaseDiagramWorker(self.db, el1, el2, t_min, t_max)
        self._worker.finished.connect(self._on_calculated)
        self._worker.start()

    # ------------------------------------------------------------------
    # Calculation result handler
    # ------------------------------------------------------------------

    def _on_calculated(self, strategy, error: str):
        self.progress_bar.setVisible(False)
        self.calc_btn.setEnabled(True)

        if error:
            self.status_label.setText("Calculation failed.")
            self.status_label.setStyleSheet("color: #E57373;")
            self.summary_label.setText("")

            el1 = self.el1_combo.currentText()
            el2 = self.el2_combo.currentText()
            friendly, technical = build_error_message(
                raw_error=error, db=self.db,
                calc_type="phase diagram",
                elements_used=[el1, el2],
                temperature=self._last_t_max_k,
            )
            QMessageBox.warning(
                self, "Calculation Did Not Succeed",
                f"{friendly}\n\n"
                f"(Technical details below if you need to share them with a developer.)\n\n"
                f"{technical}"
            )
            return

        self._last_strategy = strategy

        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()
        t_min = self._last_t_min_k
        t_max = self._last_t_max_k

        # Clear and plot with translated phase names in legend
        self.canvas.figure.clear()
        self._hover_annotation = None  # old annotation destroyed by clear()
        plot_binary_phase_diagram(self.canvas.figure, strategy, el1, el2, t_min, t_max,
                                  comp_unit=self._comp_unit)
        self._apply_phase_name_translations()
        self.canvas.draw()

        # Build phase region lookup for hover tooltips
        self._phase_lookup = build_phase_region_lookup(strategy, t_min, t_max)

        self.export_png_btn.setEnabled(True)
        self.compare_btn.setEnabled(True)
        self.status_label.setText(f"Phase diagram calculated: {el1}-{el2}")
        self.status_label.setStyleSheet("color: #81C784;")

        # Plain-English result summary
        self._update_summary(strategy, el1, el2, t_min, t_max)

        # Emit signal for history logging
        conditions = {"T_min": t_min, "T_max": t_max}
        summary_text = self.summary_label.text()
        self.calculation_done.emit([el1, el2], conditions, summary_text)

    # ------------------------------------------------------------------
    # Phase name translation for legend labels
    # ------------------------------------------------------------------

    def _apply_phase_name_translations(self) -> None:
        """Replace raw CALPHAD phase names in the plot legend with
        human-readable short names from translate_phase_short()."""
        for ax in self.canvas.figure.get_axes():
            legend = ax.get_legend()
            if legend is None:
                continue
            for text in legend.get_texts():
                original = text.get_text()
                translated = translate_phase_short(original)
                if translated != original:
                    text.set_text(translated)

    # ------------------------------------------------------------------
    # Plain-English result summary
    # ------------------------------------------------------------------

    def _update_summary(self, strategy, el1: str, el2: str,
                        t_min: float, t_max: float) -> None:
        """Build a plain-English summary of the computed phase diagram."""
        # Collect unique phase names from the strategy
        phase_names: set[str] = set()
        try:
            for zpf_line in strategy.zpf_lines:
                for point in zpf_line.points:
                    for cs in point.stable_composition_sets:
                        phase_names.add(cs.phase_record.phase_name)
        except Exception:
            pass

        n_phases = len(phase_names)
        translated = [translate_phase_short(p) for p in sorted(phase_names)]

        parts = [
            f"Phase diagram shows {n_phases} distinct phase"
            f"{'s' if n_phases != 1 else ''}: {', '.join(translated)}."
        ]

        # Add eutectic info from presets if available
        preset = get_binary_preset(el1, el2)
        if preset and preset.eutectic_t_k is not None:
            parts.append(
                f"Key feature: eutectic at {format_temp(preset.eutectic_t_k)}."
            )

        parts.append(
            f"Temperature range: {format_temp(t_min)} to {format_temp(t_max)}."
        )

        self.summary_label.setText("  ".join(parts))

    # ------------------------------------------------------------------
    # Friendly error messages
    # ------------------------------------------------------------------

    @staticmethod
    def _friendly_error(raw_error: str) -> str:
        """Convert a raw traceback into a user-friendly message."""
        lower = raw_error.lower()

        if "no valid tieline" in lower or "zpf" in lower:
            return (
                "The phase diagram mapper could not find stable phase boundaries "
                "for this system. Try adjusting the temperature range or checking "
                "that the database contains appropriate phases for both elements."
            )
        if "database" in lower and ("key" in lower or "phase" in lower):
            return (
                "The thermodynamic database does not contain the required phase "
                "models for this element pair. Make sure the TDB file covers the "
                "selected elements."
            )
        if "memory" in lower or "memoryerror" in lower:
            return (
                "The calculation ran out of memory. Try using a narrower temperature "
                "range or a coarser grid."
            )
        if "singular" in lower or "convergence" in lower:
            return (
                "The solver did not converge. This sometimes happens with complex "
                "phase diagrams. Try a smaller temperature range or different elements."
            )
        if "timeout" in lower or "timed out" in lower:
            return (
                "The calculation timed out. Try reducing the temperature range."
            )

        # Fall back to last line of the traceback (the actual exception message)
        lines = [ln.strip() for ln in raw_error.strip().splitlines() if ln.strip()]
        last_line = lines[-1] if lines else raw_error
        return f"Unexpected error: {last_line}"

    # ------------------------------------------------------------------
    # Canvas interaction -- click and move
    # ------------------------------------------------------------------

    def _on_canvas_click(self, event) -> None:
        """Handle a mouse click on the phase diagram canvas."""
        if event.inaxes is None or event.xdata is None or event.ydata is None:
            return
        x_comp = event.xdata
        t_k = event.ydata
        el2 = self.el2_combo.currentText()
        self.status_label.setText(
            f"Clicked: X({el2}) = {x_comp:.4f}, T = {format_temp(t_k)}"
        )
        self.status_label.setStyleSheet("color: #CE93D8;")

    def _on_canvas_move(self, event) -> None:
        """Handle mouse motion for live crosshair coordinates and phase hover label."""
        if event.inaxes is None or event.xdata is None or event.ydata is None:
            self._hide_hover()
            return
        x_comp = event.xdata
        t_k = event.ydata
        el2 = self.el2_combo.currentText()

        # Find nearest phase region
        phase_text = self._find_phase_at(x_comp, t_k)
        if phase_text:
            self._show_hover_label(x_comp, t_k, phase_text)
            self.status_label.setText(
                f"X({el2}) = {x_comp:.4f}   T = {format_temp(t_k)}   |   {phase_text}"
            )
        else:
            self._hide_hover()
            self.status_label.setText(
                f"X({el2}) = {x_comp:.4f}   T = {format_temp(t_k)}"
            )
        self.status_label.setStyleSheet("color: #B0BEC5;")

    def _hide_hover(self):
        """Hide the hover annotation if it exists."""
        if self._hover_annotation is not None:
            self._hover_annotation.set_visible(False)
            self.canvas.draw_idle()

    def _show_hover_label(self, x, t, text):
        """Show or update a hover annotation on the plot at (x, t)."""
        # Get the primary axes (first one, not the secondary Celsius axis)
        axes = self.canvas.figure.get_axes()
        if not axes:
            return
        ax = axes[0]

        if self._hover_annotation is None or self._hover_annotation.axes is not ax:
            # Create new annotation (or recreate if axes changed after recalc)
            if self._hover_annotation is not None:
                try:
                    self._hover_annotation.remove()
                except Exception:
                    pass
            self._hover_annotation = ax.annotate(
                text,
                xy=(x, t),
                xytext=(15, 15),
                textcoords="offset points",
                fontsize=9,
                color="white",
                bbox=dict(
                    boxstyle="round,pad=0.4",
                    facecolor="#2d2d3e",
                    edgecolor="#888888",
                    alpha=0.95,
                ),
                zorder=50,
            )
        else:
            self._hover_annotation.xy = (x, t)
            self._hover_annotation.set_text(text)
            self._hover_annotation.set_visible(True)
        self.canvas.draw_idle()

    def _find_phase_at(self, x: float, t: float) -> str | None:
        """Find the phase region label nearest to (x, T) using the lookup table."""
        if not self._phase_lookup:
            return None

        # Normalize x (0-1) and T to comparable scales
        t_range = self._last_t_max_k - self._last_t_min_k
        if t_range <= 0:
            return None

        best_dist = float("inf")
        best_label = None
        for px, pt, label in self._phase_lookup:
            # Scale x by temperature range so distances are comparable
            dx = (x - px) * t_range
            dt = t - pt
            dist = dx * dx + dt * dt
            if dist < best_dist:
                best_dist = dist
                best_label = label

        return best_label

    # ------------------------------------------------------------------
    # Export PNG with metadata subtitle
    # ------------------------------------------------------------------

    def _export_png(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Phase Diagram", "phase_diagram.png",
            "PNG Files (*.png);;All Files (*)"
        )
        if not path:
            return

        el1 = self.el1_combo.currentText()
        el2 = self.el2_combo.currentText()
        t_min = self.t_min_spin.value()
        t_max = self.t_max_spin.value()

        # Add a metadata subtitle with the conditions
        subtitle = (
            f"{el1}-{el2} | T: {format_temp(t_min)} to {format_temp(t_max)} | P = 1 atm"
        )
        axes = self.canvas.figure.get_axes()
        subtitle_text = None
        if axes:
            subtitle_text = self.canvas.figure.text(
                0.5, 0.01, subtitle,
                ha="center", va="bottom",
                fontsize=8, color="#90A4AE",
                fontstyle="italic",
            )
            self.canvas.figure.subplots_adjust(bottom=0.12)

        self.canvas.figure.savefig(path, dpi=150, facecolor="#1e1e2e")

        # Remove the subtitle so it doesn't persist on the interactive canvas
        if subtitle_text is not None:
            subtitle_text.remove()
            self.canvas.draw()

        self.status_label.setText(f"Exported to {path}")
        self.status_label.setStyleSheet("color: #81C784;")

    # ------------------------------------------------------------------
    # Compare mode
    # ------------------------------------------------------------------

    def _toggle_compare(self):
        """Toggle side-by-side comparison mode.

        When entering compare mode, the current plot is copied to the left
        canvas and the right canvas is cleared for a new calculation.
        When exiting, the compare canvas is hidden.
        """
        if self._compare_mode:
            # Exit compare mode
            self._compare_mode = False
            self.compare_canvas.setVisible(False)
            self.compare_btn.setText("Compare")
            self.compare_canvas.figure.clear()
            self.compare_canvas.draw()
            self.status_label.setText("Compare mode off.")
            self.status_label.setStyleSheet("color: #B0BEC5;")
        else:
            # Enter compare mode -- copy current plot to compare canvas
            self._compare_mode = True
            self.compare_canvas.setVisible(True)
            self.compare_btn.setText("Exit Compare")

            # Copy the current figure content to the compare figure
            self.compare_canvas.figure.clear()
            if self._last_strategy is not None:
                el1 = self.el1_combo.currentText()
                el2 = self.el2_combo.currentText()
                t_min = self._last_t_min_k
                t_max = self._last_t_max_k
                plot_binary_phase_diagram(
                    self.compare_canvas.figure, self._last_strategy,
                    el1, el2, t_min, t_max,
                    comp_unit=self._comp_unit,
                )
                # Apply phase name translations to the compare figure
                for ax in self.compare_canvas.figure.get_axes():
                    legend = ax.get_legend()
                    if legend is None:
                        continue
                    for text in legend.get_texts():
                        original = text.get_text()
                        translated = translate_phase_short(original)
                        if translated != original:
                            text.set_text(translated)
            self.compare_canvas.draw()

            self.status_label.setText(
                "Compare mode: previous diagram on the left. "
                "Run a new calculation for the right side."
            )
            self.status_label.setStyleSheet("color: #CE93D8;")
