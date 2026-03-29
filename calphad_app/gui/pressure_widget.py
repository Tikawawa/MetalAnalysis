"""Reusable pressure input widget with unit selection.

Internally stores and emits the value in Pascals.  Supports Pa, bar, atm,
and GPa display units with automatic range adjustment and live conversion
when the user switches units.
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QWidget,
)


class PressureInput(QWidget):
    """Pressure input with unit selection (Pa, bar, atm, GPa).

    Internally stores value in Pa.  Emits *valueChanged* whenever the
    effective pressure changes.
    """

    valueChanged = pyqtSignal(float)  # emits value in Pa

    UNITS: dict[str, float] = {
        "Pa": 1.0,
        "bar": 1e5,
        "atm": 101325.0,
        "GPa": 1e9,
    }

    # Per-unit spinbox limits (in display units)
    _RANGES: dict[str, tuple[float, float]] = {
        "Pa": (1.0, 1e12),
        "bar": (1e-5, 1e7),
        "atm": (1e-5, 1e4),
        "GPa": (1e-9, 1000.0),
    }

    # Per-unit decimal precision
    _DECIMALS: dict[str, int] = {
        "Pa": 0,
        "bar": 5,
        "atm": 5,
        "GPa": 9,
    }

    def __init__(
        self,
        default_pa: float = 101325.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._internal_pa: float = default_pa
        self._updating: bool = False  # guard against re-entrant signals

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Pressure:"))

        self._spin = QDoubleSpinBox()
        self._spin.setToolTip(
            "Pressure for the calculation.  101325 Pa = 1 atm (standard)."
        )
        layout.addWidget(self._spin)

        self._unit_combo = QComboBox()
        self._unit_combo.addItems(list(self.UNITS.keys()))
        self._unit_combo.setCurrentText("Pa")
        self._unit_combo.setToolTip("Display unit for the pressure value.")
        layout.addWidget(self._unit_combo)

        # Initialise the spinbox to match the default unit and value
        self._apply_unit_settings("Pa")
        self._spin.setValue(default_pa)

        # Connections
        self._spin.valueChanged.connect(self._on_spin_changed)
        self._unit_combo.currentTextChanged.connect(self._on_unit_changed)

    # -- public API ----------------------------------------------------------

    def value_pa(self) -> float:
        """Return the current pressure in Pascals."""
        return self._internal_pa

    def set_value_pa(self, pa: float) -> None:
        """Set pressure value (input in Pa, displayed in current unit)."""
        self._internal_pa = pa
        unit = self._unit_combo.currentText()
        factor = self.UNITS[unit]
        self._updating = True
        self._spin.setValue(pa / factor)
        self._updating = False

    # -- internals -----------------------------------------------------------

    def _apply_unit_settings(self, unit: str) -> None:
        lo, hi = self._RANGES[unit]
        decimals = self._DECIMALS[unit]
        self._spin.setDecimals(decimals)
        self._spin.setRange(lo, hi)
        # Choose a reasonable step size based on the unit
        if unit == "Pa":
            self._spin.setSingleStep(1000.0)
        elif unit == "bar":
            self._spin.setSingleStep(0.1)
        elif unit == "atm":
            self._spin.setSingleStep(0.1)
        else:  # GPa
            self._spin.setSingleStep(0.001)

    def _on_spin_changed(self, display_value: float) -> None:
        if self._updating:
            return
        unit = self._unit_combo.currentText()
        self._internal_pa = display_value * self.UNITS[unit]
        self.valueChanged.emit(self._internal_pa)

    def _on_unit_changed(self, new_unit: str) -> None:
        """Convert the displayed value when the unit selection changes."""
        if new_unit not in self.UNITS:
            return
        self._updating = True
        self._apply_unit_settings(new_unit)
        new_display = self._internal_pa / self.UNITS[new_unit]
        self._spin.setValue(new_display)
        self._updating = False
