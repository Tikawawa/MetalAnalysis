"""Database loading panel with TDB file browser, fixer, drag-and-drop, and preset library."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal, QMimeData
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QMessageBox, QPushButton, QProgressBar,
    QVBoxLayout, QWidget,
)

from pycalphad import Database

from core.tdb_fixer import extract_elements, extract_phases, fix_tdb_content
from core.presets import translate_phase_short, ALLOY_PRESETS, get_alloy_presets_by_category


# ---------------------------------------------------------------------------
# Friendly error message mapping
# ---------------------------------------------------------------------------

_ERROR_PATTERNS: list[tuple[str, str]] = [
    ("UnicodeDecodeError", "The file contains invalid characters. It may be corrupted or not a valid TDB file."),
    ("FileNotFoundError", "The selected file could not be found. It may have been moved or deleted."),
    ("PermissionError", "Permission denied. You do not have access to read this file."),
    ("IsADirectoryError", "The selected path is a directory, not a file. Please select a .tdb file."),
    ("SyntaxError", "The TDB file has syntax errors that could not be automatically repaired."),
    ("No valid", "The file does not appear to contain valid thermodynamic data."),
    ("ELEMENT", "The TDB file is missing element definitions. It may be incomplete."),
    ("PHASE", "The TDB file has phase definition errors. It may need manual editing."),
    ("pycalphad", "The thermodynamic database engine could not parse this file. "
                  "Try opening it in a text editor to check for formatting problems."),
]


def _friendly_error(raw_error: str) -> str:
    """Convert a raw Python exception string into a user-friendly message."""
    for pattern, friendly in _ERROR_PATTERNS:
        if pattern.lower() in raw_error.lower():
            return friendly
    # Fallback: strip the exception class prefix if present
    if ":" in raw_error and raw_error[0].isupper():
        return raw_error.split(":", 1)[-1].strip()
    return raw_error


# ---------------------------------------------------------------------------
# Background worker (unchanged)
# ---------------------------------------------------------------------------

class DatabaseLoadWorker(QThread):
    """Worker thread for loading and fixing TDB files."""
    finished = pyqtSignal(object, str, str)  # (Database, fixed_text, error)
    progress = pyqtSignal(str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            ext = Path(self.file_path).suffix.lower()

            if ext == ".dat":
                self.progress.emit("Reading ChemSage DAT file...")
                db = Database(self.file_path)
                fixed_text = ""  # DAT files don't use the TDB fixer
                self.finished.emit(db, fixed_text, "")
                return

            self.progress.emit("Reading TDB file...")
            raw = Path(self.file_path).read_bytes()

            self.progress.emit("Fixing TDB format issues...")
            fixed_text = fix_tdb_content(raw)

            self.progress.emit("Parsing database with pycalphad...")
            # Write fixed content to temp file for pycalphad
            with tempfile.NamedTemporaryFile(mode="w", suffix=".tdb", delete=False, encoding="utf-8") as f:
                f.write(fixed_text)
                tmp_path = f.name

            db = Database(tmp_path)
            Path(tmp_path).unlink(missing_ok=True)

            self.finished.emit(db, fixed_text, "")
        except Exception as e:
            self.finished.emit(None, "", str(e))


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

class DatabasePanel(QWidget):
    """Panel for loading TDB database files with drag-and-drop and preset support."""

    database_loaded = pyqtSignal(object, list, list)  # (Database, elements, phases)
    preset_applied = pyqtSignal(object)  # AlloyPreset that was selected

    def __init__(self):
        super().__init__()
        self.db: Database | None = None
        self.elements: list[str] = []
        self.phases: list[str] = []
        self._worker: DatabaseLoadWorker | None = None
        self._pending_preset = None  # preset to apply after DB loads
        self.setAcceptDrops(True)
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Title
        title = QLabel("Database Loader")
        title.setObjectName("heading")
        title.setToolTip("Load a thermodynamic database (.tdb) file to begin calculations")
        layout.addWidget(title)

        # --- Alloy preset library ---
        preset_group = QGroupBox("Quick Load Preset")
        preset_group.setToolTip("Select a common alloy to auto-fill elements and temperature ranges")
        preset_layout = QVBoxLayout()

        self.preset_combo = QComboBox()
        self.preset_combo.setToolTip(
            "Choose a pre-configured alloy system. This will display its "
            "elements and typical temperature range after a database is loaded."
        )
        self._populate_preset_combo()
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        preset_layout.addWidget(self.preset_combo)

        self.apply_preset_btn = QPushButton("Load Database & Apply Preset")
        self.apply_preset_btn.setObjectName("primary")
        self.apply_preset_btn.setEnabled(False)
        self.apply_preset_btn.setToolTip(
            "Loads the bundled COST507 database and auto-fills "
            "the selected alloy's composition and temperature into the calculation tabs"
        )
        self.apply_preset_btn.clicked.connect(self._apply_preset)
        preset_layout.addWidget(self.apply_preset_btn)

        self.preset_info_label = QLabel("")
        self.preset_info_label.setObjectName("status")
        self.preset_info_label.setWordWrap(True)
        self.preset_info_label.setToolTip("Details about the selected alloy preset")
        preset_layout.addWidget(self.preset_info_label)

        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)

        # --- File selection ---
        file_group = QGroupBox("TDB File")
        file_group.setToolTip("Select or drag-and-drop a .tdb thermodynamic database file")
        file_layout = QHBoxLayout()

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select a .tdb or .dat database file or drag one here...")
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setToolTip(
            "Path to the currently selected TDB file. "
            "Use Browse or drag-and-drop a file onto this panel."
        )
        file_layout.addWidget(self.file_path_edit)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setToolTip("Open a file dialog to choose a .tdb database file")
        self.browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(self.browse_btn)

        self.load_btn = QPushButton("Load Database")
        self.load_btn.setObjectName("primary")
        self.load_btn.setEnabled(False)
        self.load_btn.setToolTip("Select a .tdb file first using Browse or drag-and-drop")
        self.load_btn.clicked.connect(self._load_database)
        file_layout.addWidget(self.load_btn)

        self.save_btn = QPushButton("Save As TDB")
        self.save_btn.setObjectName("success")
        self.save_btn.setEnabled(False)
        self.save_btn.setToolTip(
            "Save the currently loaded database as a TDB file"
        )
        self.save_btn.clicked.connect(self._save_database)
        file_layout.addWidget(self.save_btn)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # --- Progress ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(False)
        self.progress_bar.setToolTip("Database loading progress")
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setObjectName("status")
        self.status_label.setToolTip("Current status of the database loading process")
        layout.addWidget(self.status_label)

        # --- Results section ---
        results_layout = QHBoxLayout()

        # Elements list
        elements_group = QGroupBox("Elements Found")
        elements_group.setToolTip("Chemical elements defined in the loaded database")
        el_layout = QVBoxLayout()
        self.elements_list = QListWidget()
        self.elements_list.setToolTip("List of elements extracted from the TDB file")
        el_layout.addWidget(self.elements_list)
        self.elements_count_label = QLabel("0 elements")
        self.elements_count_label.setToolTip("Total number of elements in the database")
        el_layout.addWidget(self.elements_count_label)
        elements_group.setLayout(el_layout)
        results_layout.addWidget(elements_group)

        # Phases list
        phases_group = QGroupBox("Phases Found")
        phases_group.setToolTip("Thermodynamic phases defined in the loaded database")
        ph_layout = QVBoxLayout()
        self.phases_list = QListWidget()
        self.phases_list.setToolTip(
            "List of phases from the TDB file with translated names. "
            "Format: PHASE_CODE (Human-readable name)"
        )
        ph_layout.addWidget(self.phases_list)
        self.phases_count_label = QLabel("0 phases")
        self.phases_count_label.setToolTip("Total number of phases in the database")
        ph_layout.addWidget(self.phases_count_label)
        phases_group.setLayout(ph_layout)
        results_layout.addWidget(phases_group)

        layout.addLayout(results_layout)
        layout.addStretch()

    # ------------------------------------------------------------------
    # Preset combo helpers
    # ------------------------------------------------------------------

    def _populate_preset_combo(self):
        """Fill the preset combo box with alloy presets grouped by category."""
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("-- Select an alloy preset --", None)

        by_category = get_alloy_presets_by_category()
        for category, presets in sorted(by_category.items()):
            # Category separator (disabled item)
            self.preset_combo.addItem(f"--- {category} ---", None)
            idx = self.preset_combo.count() - 1
            model = self.preset_combo.model()
            if model is not None:
                item = model.item(idx)
                if item is not None:
                    item.setEnabled(False)

            for preset in presets:
                label = f"{preset.name}  ({preset.designation})"
                self.preset_combo.addItem(label, preset)

        self.preset_combo.blockSignals(False)

    def _on_preset_selected(self, index: int):
        """Show info about the selected alloy preset."""
        preset = self.preset_combo.currentData()
        if preset is None:
            self.preset_info_label.setText("")
            self.apply_preset_btn.setEnabled(False)
            return
        comp_parts = [f"{el} {wt}%" for el, wt in preset.composition_wt.items()]
        comp_str = ", ".join(comp_parts)
        self.preset_info_label.setText(
            f"Elements: {', '.join(preset.elements)}  |  "
            f"Composition (wt%): {comp_str}\n"
            f"Temp range: {preset.t_min_k:.0f} - {preset.t_max_k:.0f} K  |  "
            f"Application: {preset.application}"
        )
        self.apply_preset_btn.setEnabled(True)

    def _apply_preset(self):
        """Load the bundled database and apply the selected preset."""
        preset = self.preset_combo.currentData()
        if preset is None:
            return

        self._pending_preset = preset

        # If database already loaded, just emit the preset signal
        if self.db is not None:
            self.preset_applied.emit(preset)
            self.status_label.setText(f"Preset applied: {preset.name} ({preset.designation})")
            self.status_label.setStyleSheet("color: #81C784;")
            return

        # Otherwise, load the bundled COST507.tdb first
        app_dir = os.path.dirname(os.path.abspath(__file__))
        sample_path = os.path.join(os.path.dirname(app_dir), "COST507.tdb")
        if os.path.isfile(sample_path):
            self.load_file(sample_path)
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self, "Database Not Found",
                "Could not find the bundled COST507.tdb database.\n"
                "Please load a TDB file manually first, then select a preset."
            )

    # ------------------------------------------------------------------
    # Drag-and-drop support
    # ------------------------------------------------------------------

    def dragEnterEvent(self, event):
        """Accept drag events that contain file URLs ending in .tdb."""
        if event.mimeData() and event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith((".tdb", ".dat")):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragMoveEvent(self, event):
        """Keep accepting while dragging over the panel."""
        if event.mimeData() and event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handle dropped database files by loading the first valid one."""
        if event.mimeData() and event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith((".tdb", ".dat")):
                    event.acceptProposedAction()
                    self.load_file(path)
                    return
        event.ignore()

    # ------------------------------------------------------------------
    # Unit-setting stubs (required by panel interface)
    # ------------------------------------------------------------------

    def set_temp_unit(self, unit: str) -> None:
        """Set the temperature unit for display. No-op for this panel."""
        pass

    def set_comp_unit(self, unit: str) -> None:
        """Set the composition unit for display. No-op for this panel."""
        pass

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------

    def load_file(self, path: str):
        """Programmatically load a TDB file by path."""
        self.file_path_edit.setText(path)
        self.load_btn.setEnabled(True)
        self.load_btn.setToolTip("Parse and load the selected TDB file into the application")
        self._load_database()

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Thermodynamic Database", "",
            "Thermodynamic Databases (*.tdb *.TDB *.dat *.DAT);;TDB Files (*.tdb *.TDB);;ChemSage DAT Files (*.dat *.DAT);;All Files (*)"
        )
        if path:
            if not path.lower().endswith((".tdb", ".dat")):
                reply = QMessageBox.warning(
                    self, "Non-TDB File Selected",
                    "Selected file does not appear to be a TDB file. Are you sure?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
            self.file_path_edit.setText(path)
            self.load_btn.setEnabled(True)
            self.load_btn.setToolTip("Parse and load the selected TDB file into the application")

    def _load_database(self):
        # BUG 3 fix: prevent double-loading if worker is already running
        if self._worker is not None and self._worker.isRunning():
            return

        path = self.file_path_edit.text()
        if not path:
            return

        # Validate file exists before starting worker
        if not Path(path).is_file():
            self.status_label.setText("File not found")
            self.status_label.setObjectName("error")
            self.status_label.setStyleSheet("color: #E57373;")
            QMessageBox.warning(
                self, "File Not Found",
                f"The file could not be found:\n\n{path}\n\n"
                "Please check that the file exists and try again."
            )
            return

        self.load_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Loading...")
        self.status_label.setObjectName("status")
        self.status_label.setStyleSheet("")

        self._worker = DatabaseLoadWorker(path)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_loaded)
        self._worker.finished.connect(self._cancel_load_timeout)
        self._worker.destroyed.connect(self._on_worker_destroyed)
        self._worker.start()

        # BUG 11 fix: timeout safety - hide progress bar after 60s if still loading
        self._load_timer = QTimer(self)
        self._load_timer.setSingleShot(True)
        self._load_timer.timeout.connect(self._on_load_timeout)
        self._load_timer.start(60000)

    def _on_load_timeout(self):
        """Safety timeout: re-enable UI if worker is stuck."""
        if self._worker is not None and self._worker.isRunning():
            self.progress_bar.setVisible(False)
            self.browse_btn.setEnabled(True)
            self.load_btn.setEnabled(True)
            self.status_label.setText("Loading timed out. Please try again.")
            self.status_label.setStyleSheet("color: #E57373;")

    def _cancel_load_timeout(self):
        """Cancel the load timeout timer when worker finishes normally."""
        if hasattr(self, "_load_timer") and self._load_timer is not None:
            self._load_timer.stop()

    def _on_worker_destroyed(self):
        """Hide progress bar if the worker object is unexpectedly destroyed."""
        self.progress_bar.setVisible(False)
        self.browse_btn.setEnabled(True)
        self.load_btn.setEnabled(True)

    def _on_progress(self, msg: str):
        self.status_label.setText(msg)

    def _on_loaded(self, db: Database | None, fixed_text: str, error: str):
        self.progress_bar.setVisible(False)
        self.browse_btn.setEnabled(True)
        self.load_btn.setEnabled(True)

        if error:
            self._pending_preset = None  # BUG 4 fix: clear pending preset on error
            friendly = _friendly_error(error)
            self.status_label.setText(f"Error: {friendly}")
            self.status_label.setObjectName("error")
            self.status_label.setStyleSheet("color: #E57373;")
            QMessageBox.critical(
                self, "Database Error",
                f"Failed to load the database.\n\n{friendly}\n\n"
                "If the problem persists, try opening the .tdb file in a text "
                "editor to check for obvious formatting issues."
            )
            return

        self.db = db
        ext = Path(self.file_path_edit.text()).suffix.lower()
        if ext == ".dat" or not fixed_text:
            # For DAT files or empty fixed_text, extract from Database object
            self.elements = sorted([str(el) for el in db.elements
                                    if str(el) not in ("/-", "VA", "")])
            self.phases = sorted(list(db.phases.keys()))
        else:
            self.elements = extract_elements(fixed_text)
            self.phases = extract_phases(fixed_text)

        # Also get phases from pycalphad's parsed result
        if db and db.phases:
            pycalphad_phases = list(db.phases.keys())
            for p in pycalphad_phases:
                if p not in self.phases:
                    self.phases.append(p)

        # Update UI - elements
        self.elements_list.clear()
        self.elements_list.addItems(self.elements)
        self.elements_count_label.setText(f"{len(self.elements)} elements")

        # Update UI - phases with translated names
        self.phases_list.clear()
        for phase in self.phases:
            translated = translate_phase_short(phase)
            if translated != phase:
                display = f"{phase} ({translated})"
            else:
                display = phase
            self.phases_list.addItem(display)
        self.phases_count_label.setText(f"{len(self.phases)} phases")

        self.status_label.setText(f"Loaded: {Path(self.file_path_edit.text()).name}")
        self.status_label.setObjectName("status")
        self.status_label.setStyleSheet("color: #81C784;")

        # BUG 14 fix: update button tooltips now that database is loaded
        self.load_btn.setToolTip("Reload the current TDB file")

        self.save_btn.setEnabled(True)

        ext = Path(self.file_path_edit.text()).suffix.lower()
        fmt_name = "ChemSage DAT" if ext == ".dat" else "TDB"
        self.status_label.setText(f"Loaded ({fmt_name}): {Path(self.file_path_edit.text()).name}")

        self.database_loaded.emit(db, self.elements, self.phases)

        # If a preset was pending, apply it now that the DB is loaded
        if self._pending_preset is not None:
            preset = self._pending_preset
            self._pending_preset = None
            self.preset_applied.emit(preset)
            self.status_label.setText(f"Loaded & applied preset: {preset.name} ({preset.designation})")
            self.status_label.setStyleSheet("color: #81C784;")

    # ------------------------------------------------------------------
    # Database export
    # ------------------------------------------------------------------

    def _save_database(self):
        """Save the currently loaded database as a TDB file."""
        if not self.db:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Database As", "database.tdb",
            "TDB Files (*.tdb);;All Files (*)"
        )
        if path:
            try:
                self.db.to_file(path, if_exists="overwrite")
                self.status_label.setText(f"Database saved to {path}")
                self.status_label.setStyleSheet("color: #81C784;")
            except Exception as e:
                QMessageBox.critical(self, "Save Failed", str(e))
