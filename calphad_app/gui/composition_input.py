"""Reusable composition input widgets for multi-element alloy specification.

Provides CompositionRow (single element input) and CompositionInputGroup
(dynamic multi-row container with balance indicator).  Used by Equilibrium,
Scheil, Thermo Properties, and Driving Force panels.
"""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QVBoxLayout, QWidget,
)

from core.presets import ATOMIC_WEIGHTS
from core.units import mole_to_weight, weight_to_mole


# ---------------------------------------------------------------------------
# Single element-composition row
# ---------------------------------------------------------------------------

class CompositionRow(QWidget):
    """A single element-composition input row."""

    def __init__(self, elements: list[str], comp_unit: str = "mole_fraction",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._comp_unit = comp_unit
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.element_combo = QComboBox()
        self.element_combo.addItems(elements)
        self.element_combo.setToolTip(
            "Select the alloying element.  The balance element is "
            "determined automatically."
        )
        layout.addWidget(self.element_combo)

        self.unit_label = QLabel(self._label_text())
        layout.addWidget(self.unit_label)

        self.composition_spin = QDoubleSpinBox()
        self._apply_unit_range()
        self.composition_spin.setToolTip(
            "Composition of this element.  The balance element makes up "
            "the remainder."
        )
        layout.addWidget(self.composition_spin)

    def _label_text(self) -> str:
        return "wt% =" if self._comp_unit == "weight_percent" else "X ="

    def _apply_unit_range(self) -> None:
        if self._comp_unit == "weight_percent":
            self.composition_spin.setRange(0.0, 100.0)
            self.composition_spin.setDecimals(2)
            self.composition_spin.setSingleStep(0.5)
            self.composition_spin.setValue(5.0)
        else:
            self.composition_spin.setRange(0.0, 1.0)
            self.composition_spin.setDecimals(4)
            self.composition_spin.setSingleStep(0.01)
            self.composition_spin.setValue(0.05)

    def set_comp_unit(self, unit: str) -> None:
        """Switch between 'mole_fraction' and 'weight_percent'."""
        if unit == self._comp_unit:
            return
        self._comp_unit = unit
        self.unit_label.setText(self._label_text())
        self._apply_unit_range()


# ---------------------------------------------------------------------------
# Multi-row composition group with balance indicator
# ---------------------------------------------------------------------------

class CompositionInputGroup(QGroupBox):
    """Reusable multi-element composition input with balance indicator.

    Used by: Equilibrium, Scheil, Thermo Properties, Driving Force panels.
    """

    composition_changed = pyqtSignal()

    def __init__(self, title: str = "Alloy Composition",
                 parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        self._elements: list[str] = []
        self._comp_unit: str = "mole_fraction"
        self._rows: list[CompositionRow] = []
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        btn_layout = QHBoxLayout()
        self._add_btn = QPushButton("+ Add Element")
        self._add_btn.setToolTip("Add another alloying element row.")
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(lambda: self.add_row())
        btn_layout.addWidget(self._add_btn)

        self._remove_btn = QPushButton("- Remove Last")
        self._remove_btn.setToolTip("Remove the last composition row.")
        self._remove_btn.setEnabled(False)
        self._remove_btn.clicked.connect(self._remove_last_row)
        btn_layout.addWidget(self._remove_btn)
        btn_layout.addStretch()
        root.addLayout(btn_layout)

        self._rows_layout = QVBoxLayout()
        root.addLayout(self._rows_layout)

        self._balance_label = QLabel("")
        self._balance_label.setToolTip(
            "Live composition balance.  Turns red if total exceeds limit."
        )
        self._balance_label.setStyleSheet("padding: 4px; font-weight: bold;")
        root.addWidget(self._balance_label)

    # -- public API ----------------------------------------------------------

    def set_elements(self, elements: list[str]) -> None:
        """Set available elements (called when database loads)."""
        self._elements = list(elements)
        self.clear_rows()
        self._add_btn.setEnabled(bool(elements))

    def set_comp_unit(self, unit: str) -> None:
        """Switch between 'mole_fraction' and 'weight_percent'."""
        if unit not in ("mole_fraction", "weight_percent") or unit == self._comp_unit:
            return
        old_unit = self._comp_unit
        self._comp_unit = unit
        if unit == "weight_percent":
            self.setTitle(self.title().replace("mole fractions", "weight percent"))
        else:
            self.setTitle(self.title().replace("weight percent", "mole fractions"))

        if self._rows:
            current_vals = self._current_element_values()
            balance_el = self.get_balance_element(self._elements)
            if balance_el is not None:
                limit = 100.0 if old_unit == "weight_percent" else 1.0
                full_comp = dict(current_vals)
                full_comp[balance_el] = max(0.0, limit - sum(current_vals.values()))
                converted = (mole_to_weight(full_comp) if old_unit == "mole_fraction"
                             else weight_to_mole(full_comp))
                for row in self._rows:
                    el = row.element_combo.currentText()
                    row.composition_spin.blockSignals(True)
                    row.set_comp_unit(unit)
                    if el in converted:
                        row.composition_spin.setValue(converted[el])
                    row.composition_spin.blockSignals(False)
            else:
                for row in self._rows:
                    row.set_comp_unit(unit)
        self._update_balance()

    def get_compositions(self) -> dict[str, float]:
        """Return {element: value} dict of current compositions."""
        return self._current_element_values()

    def get_elements_used(self) -> list[str]:
        """Return list of elements with composition rows."""
        return [row.element_combo.currentText() for row in self._rows]

    def get_balance_element(self, all_elements: list[str]) -> str | None:
        """Return the first element not used in any row (the balance element)."""
        used = set(self.get_elements_used())
        for el in all_elements:
            if el not in used:
                return el
        return None

    def get_compositions_as_mole_fraction(
        self, all_elements: list[str],
    ) -> dict[str, float]:
        """Return compositions converted to mole fraction, handling wt% conversion.

        Adds balance element to make complete composition before converting.
        """
        current = self._current_element_values()
        balance_el = self.get_balance_element(all_elements)
        if self._comp_unit == "weight_percent":
            full_wt = dict(current)
            if balance_el is not None:
                full_wt[balance_el] = max(0.0, 100.0 - sum(current.values()))
            mole_frac = weight_to_mole(full_wt)
            return {el: mole_frac[el] for el in current}
        return dict(current)

    def clear_rows(self) -> None:
        """Remove all composition rows."""
        for row in self._rows:
            row.deleteLater()
        self._rows.clear()
        self._remove_btn.setEnabled(False)
        self._balance_label.setText("")
        self.composition_changed.emit()

    def add_row(self, element: str | None = None,
                value: float | None = None) -> None:
        """Add a composition row, optionally pre-setting element and value."""
        if not self._elements:
            return
        row = CompositionRow(self._elements, comp_unit=self._comp_unit)
        if element is not None:
            row.element_combo.setCurrentText(element)
        else:
            used = {r.element_combo.currentText() for r in self._rows}
            for el in self._elements:
                if el not in used:
                    row.element_combo.setCurrentText(el)
                    break
        if value is not None:
            row.composition_spin.setValue(value)
        row.composition_spin.valueChanged.connect(self._on_value_changed)
        row.element_combo.currentTextChanged.connect(self._on_value_changed)
        self._rows.append(row)
        self._rows_layout.addWidget(row)
        self._remove_btn.setEnabled(True)
        self._update_balance()
        self.composition_changed.emit()

    # -- internals -----------------------------------------------------------

    def _current_element_values(self) -> dict[str, float]:
        return {row.element_combo.currentText(): row.composition_spin.value()
                for row in self._rows}

    def _remove_last_row(self) -> None:
        if self._rows:
            self._rows.pop().deleteLater()
        self._remove_btn.setEnabled(bool(self._rows))
        self._update_balance()
        self.composition_changed.emit()

    def _on_value_changed(self) -> None:
        self._update_balance()
        self.composition_changed.emit()

    def _update_balance(self) -> None:
        """Recalculate and display the composition balance indicator."""
        if not self._rows:
            self._balance_label.setText("")
            return
        is_wt = self._comp_unit == "weight_percent"
        limit = 100.0 if is_wt else 1.0
        unit_str = "%" if is_wt else ""
        fmt = ".2f" if is_wt else ".4f"

        parts: list[str] = []
        total = 0.0
        used_elements: set[str] = set()
        for row in self._rows:
            el = row.element_combo.currentText()
            val = row.composition_spin.value()
            total += val
            used_elements.add(el)
            parts.append(f"{el}: {val:{fmt}}{unit_str}")

        balance_el = self.get_balance_element(self._elements)
        if balance_el is not None:
            parts.insert(0, f"{balance_el}: balance")

        text = " | ".join(parts) + f"  |  Total: {total:{fmt}}{unit_str}"
        over = total > limit + (0.01 if is_wt else 0.0001)
        color = "#E57373" if over else "#81C784"
        self._balance_label.setStyleSheet(
            f"padding: 4px; font-weight: bold; color: {color};"
        )
        self._balance_label.setText(text)
