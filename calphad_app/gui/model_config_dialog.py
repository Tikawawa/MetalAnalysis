"""Custom Model Contributions dialog.

Lets the user enable or disable individual energy contributions
(reference, ideal mixing, excess mixing, magnetic, etc.) used by
pycalphad's Model class.  A factory function creates a custom Model
subclass with the selected contributions.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QGroupBox,
    QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)
from pycalphad import Model


# ---------------------------------------------------------------------------
# All known contributions (key, method_name, display_label, tooltip, locked)
# ---------------------------------------------------------------------------

_CONTRIBUTIONS = [
    (
        "ref", "reference_energy", "Reference Energy",
        "Pure-element lattice stability (GHSER). This is the baseline "
        "Gibbs energy of each element in its reference state and cannot "
        "be disabled.",
        True,  # always enabled, checkbox disabled
    ),
    (
        "idmix", "ideal_mixing_energy", "Ideal Mixing",
        "Configurational entropy of mixing (RT * x * ln(x)). This "
        "captures the entropy gain from randomly distributing atoms "
        "on sublattice sites and cannot be disabled.",
        True,  # always enabled, checkbox disabled
    ),
    (
        "xsmix", "excess_mixing_energy", "Excess Mixing",
        "Redlich-Kister polynomial interaction parameters (L parameters). "
        "These describe non-ideal interactions between species beyond "
        "what ideal mixing predicts.",
        False,
    ),
    (
        "mag", "magnetic_energy", "Magnetic",
        "Inden-Hillert-Jarl magnetic contribution. Accounts for the "
        "Gibbs energy change associated with magnetic ordering "
        "(ferromagnetic or antiferromagnetic transitions).",
        False,
    ),
    (
        "2st", "twostate_energy", "Two-State",
        "Two-state model for liquid/amorphous phases. Describes the "
        "energy difference between crystalline-like and amorphous-like "
        "atomic configurations in the liquid.",
        False,
    ),
    (
        "ein", "einstein_energy", "Einstein",
        "Einstein model for heat capacity. Provides a quantum-mechanical "
        "correction to the classical Dulong-Petit heat capacity using "
        "a characteristic Einstein temperature.",
        False,
    ),
    (
        "vol", "volume_energy", "Volume",
        "Pressure-volume contribution to Gibbs energy. Required for "
        "calculating molar volume and density. Only meaningful if the "
        "database contains volume parameters (V0, VA).",
        False,
    ),
    (
        "ord", "atomic_ordering_energy", "Atomic Ordering",
        "Contribution from atomic ordering (e.g., B2/L12 ordering in "
        "intermetallic phases). Accounts for the energy difference "
        "between ordered and disordered sublattice configurations.",
        False,
    ),
]


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

def make_custom_model(
    enabled_contributions: list[tuple[str, str]],
) -> type[Model]:
    """Create a Model subclass using only the given contributions.

    Args:
        enabled_contributions: List of (key, method_name) tuples,
            e.g. [('ref', 'reference_energy'), ('idmix', 'ideal_mixing_energy')].

    Returns:
        A Model subclass whose ``contributions`` attribute contains
        exactly the specified entries.
    """

    class CustomModel(Model):
        contributions = list(enabled_contributions)

    return CustomModel


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

class ModelConfigDialog(QDialog):
    """Dialog for selecting which energy contributions to include in the
    pycalphad Model used for calculations."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Energy Model Configuration")
        self.setMinimumWidth(480)
        self.setMinimumHeight(520)
        self.setStyleSheet(
            "QDialog { background-color: #1a1a2e; }"
        )

        self._checkboxes: list[QCheckBox] = []
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Energy Model Configuration")
        title.setObjectName("heading")
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "Select which energy contributions are included when "
            "pycalphad builds the Gibbs energy model for each phase. "
            "Disabling a contribution removes its terms from the "
            "total Gibbs energy expression. Reference Energy and "
            "Ideal Mixing are always required and cannot be turned off."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(
            "color: #aaaacc; font-size: 12px; padding: 4px 0 8px 0;"
        )
        layout.addWidget(desc)

        # Contributions group
        group = QGroupBox("Energy Contributions")
        group_layout = QVBoxLayout()
        group_layout.setSpacing(6)

        for key, method, label, tooltip, locked in _CONTRIBUTIONS:
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setToolTip(tooltip)
            cb.setStyleSheet(
                "QCheckBox { color: #e0e0e0; font-size: 13px; "
                "padding: 4px 0; }"
                "QCheckBox::indicator { width: 18px; height: 18px; }"
                "QCheckBox::indicator:unchecked { "
                "    border: 2px solid #555577; border-radius: 3px; "
                "    background-color: #16213e; }"
                "QCheckBox::indicator:checked { "
                "    border: 2px solid #4FC3F7; border-radius: 3px; "
                "    background-color: #0f3460; "
                "    image: none; }"
                "QCheckBox:disabled { color: #777799; }"
            )

            if locked:
                cb.setEnabled(False)
                cb.setToolTip(
                    tooltip + "\n\nThis contribution is mandatory "
                    "and cannot be disabled."
                )

            self._checkboxes.append(cb)
            group_layout.addWidget(cb)

        group.setLayout(group_layout)
        layout.addWidget(group)

        layout.addStretch()

        # --- Bottom buttons ---
        bottom_layout = QHBoxLayout()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setToolTip(
            "Re-enable all contributions to their default state."
        )
        reset_btn.clicked.connect(self._reset_defaults)
        bottom_layout.addWidget(reset_btn)

        bottom_layout.addStretch()

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        bottom_layout.addWidget(button_box)

        layout.addLayout(bottom_layout)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_enabled_contributions(self) -> list[tuple[str, str]]:
        """Return list of (key, method_name) for enabled contributions."""
        all_contributions = [
            (key, method) for key, method, _label, _tip, _locked
            in _CONTRIBUTIONS
        ]
        return [
            (k, m)
            for (k, m), cb in zip(all_contributions, self._checkboxes)
            if cb.isChecked()
        ]

    def set_contributions(
        self, enabled_keys: list[str] | None = None
    ) -> None:
        """Pre-set which contributions are checked.

        Args:
            enabled_keys: List of contribution keys to enable,
                e.g. ['ref', 'idmix', 'xsmix', 'mag'].
                If None, all contributions are enabled.
        """
        if enabled_keys is None:
            self._reset_defaults()
            return

        for i, (key, _method, _label, _tip, locked) in enumerate(
            _CONTRIBUTIONS
        ):
            if locked:
                self._checkboxes[i].setChecked(True)
            else:
                self._checkboxes[i].setChecked(key in enabled_keys)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _reset_defaults(self):
        """Enable all checkboxes (restore defaults)."""
        for cb in self._checkboxes:
            cb.setChecked(True)
