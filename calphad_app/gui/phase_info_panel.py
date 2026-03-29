"""Phase information dock widget."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QLabel, QLineEdit, QListWidget,
)

from core.presets import PHASE_NAMES


# Map of phase name prefixes to crystal structure types
_CRYSTAL_STRUCTURES: dict[str, str] = {
    "FCC": "Face-Centered Cubic (FCC)",
    "BCC": "Body-Centered Cubic (BCC)",
    "HCP": "Hexagonal Close-Packed (HCP)",
    "DIAMOND": "Diamond Cubic",
    "CBCC": "Complex Body-Centered Cubic",
    "CUB": "Complex Cubic",
    "RHOMBO": "Rhombohedral",
    "BCT": "Body-Centered Tetragonal",
    "TETRAGONAL": "Tetragonal",
    "ORTHORHOMBIC": "Orthorhombic",
    "LIQUID": "Liquid (no crystal structure)",
}

# Common aliases for well-known phases
_ALIASES: dict[str, list[str]] = {
    "LIQUID": ["L", "Liquid"],
    "FCC_A1": ["gamma", "austenite (in Fe)", "alpha-Al"],
    "BCC_A2": ["alpha (in Fe)", "ferrite"],
    "BCC_B2": ["beta (ordered BCC)"],
    "HCP_A3": ["alpha (in Ti/Mg)", "epsilon"],
    "DIAMOND_A4": ["Si-diamond", "Ge-diamond"],
    "AL2CU": ["theta", "Al2Cu"],
    "AL2CU_C16": ["theta", "Al2Cu"],
    "CEMENTITE": ["Fe3C", "cementite"],
    "FE3C": ["cementite", "Fe3C"],
    "SIGMA": ["sigma"],
    "MG2SI": ["beta-prime precursor"],
    "MGZN2": ["eta", "MgZn2"],
    "AL3NI": ["Al3Ni"],
    "GRAPHITE": ["C-graphite"],
    "MG17AL12": ["beta (Mg)", "Mg17Al12"],
}


class PhaseInfoPanel(QDockWidget):
    """Dock widget that shows detailed information about a selected phase."""

    def __init__(self, parent=None):
        super().__init__("Phase Info", parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.setFixedWidth(320)
        self._setup_ui()

    def _setup_ui(self):
        container = QWidget()
        container.setStyleSheet(
            "background-color: #1a1a2e; color: #e0e0e0;"
        )
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QLabel("Phase Information")
        header.setStyleSheet(
            "color: #4FC3F7; font-size: 14px; font-weight: bold; padding: 2px;"
        )
        layout.addWidget(header)

        # Search box for phase lookup
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Type a phase name (e.g. FCC_A1)...")
        self.search_box.setStyleSheet(
            "QLineEdit { background-color: #16213e; color: #e0e0e0; "
            "border: 1px solid #333355; border-radius: 4px; padding: 6px; "
            "font-size: 12px; }"
        )
        self.search_box.returnPressed.connect(self._on_search)
        self.search_box.textChanged.connect(self._on_search)
        layout.addWidget(self.search_box)

        # List of all known phase names
        self.phase_list = QListWidget()
        self.phase_list.setStyleSheet(
            "QListWidget { background-color: #16213e; color: #e0e0e0; "
            "border: 1px solid #333355; border-radius: 4px; font-size: 12px; }"
            "QListWidget::item { padding: 3px 6px; }"
            "QListWidget::item:selected { background-color: #0f3460; color: #4FC3F7; }"
        )
        self.phase_list.setMaximumHeight(150)
        for name in sorted(PHASE_NAMES.keys()):
            self.phase_list.addItem(name)
        self.phase_list.currentTextChanged.connect(self._on_phase_selected)
        layout.addWidget(self.phase_list)

        self.info_label = QLabel("Select or look up a phase to see details.")
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.info_label.setStyleSheet(
            "background-color: #16213e; color: #ccccdd; border: 1px solid #333355; "
            "border-radius: 4px; padding: 12px; font-size: 13px; line-height: 1.5;"
        )
        self.info_label.setMinimumHeight(200)
        layout.addWidget(self.info_label, stretch=1)

        self.setWidget(container)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_phase(self, phase_name: str):
        """Display detailed information about the given phase.

        Parameters
        ----------
        phase_name : str
            The CALPHAD phase model name, e.g. "FCC_A1" or "AL2CU".
        """
        upper = phase_name.upper().strip()
        description = PHASE_NAMES.get(upper)

        if description is None:
            self.info_label.setText(
                f"Phase: {upper}\n\n"
                f"No additional information available for this phase."
            )
            return

        # Determine crystal structure
        crystal = self._get_crystal_structure(upper)

        # Get aliases
        aliases = _ALIASES.get(upper, [])
        alias_str = ", ".join(aliases) if aliases else "None known"

        text = (
            f"Phase: {upper}\n\n"
            f"Crystal Structure: {crystal}\n\n"
            f"Description: {description}\n\n"
            f"Common Aliases: {alias_str}"
        )
        self.info_label.setText(text)

    def _on_search(self):
        """Handle search box input: look up the typed phase name."""
        text = self.search_box.text().strip()
        if text:
            self.show_phase(text)

        # Filter the list to show matching items
        search_text = self.search_box.text().strip().upper()
        for i in range(self.phase_list.count()):
            item = self.phase_list.item(i)
            if search_text == "" or search_text in item.text().upper():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def _on_phase_selected(self, phase_name: str):
        """Handle click on a phase in the list widget."""
        if phase_name:
            self.show_phase(phase_name)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _get_crystal_structure(phase_upper: str) -> str:
        """Parse the crystal structure type from the phase model name."""
        # Direct match first
        if phase_upper in _CRYSTAL_STRUCTURES:
            return _CRYSTAL_STRUCTURES[phase_upper]

        # Prefix match (e.g. FCC_A1 -> FCC)
        for prefix, structure in _CRYSTAL_STRUCTURES.items():
            if phase_upper.startswith(prefix):
                return structure

        return "Unknown / compound"
