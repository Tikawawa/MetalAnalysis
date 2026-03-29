"""Unit conversion utilities for temperature and composition."""

from __future__ import annotations

from core.presets import ATOMIC_WEIGHTS


# --- Temperature conversion ---

def k_to_c(kelvin: float) -> float:
    """Convert Kelvin to Celsius."""
    return kelvin - 273.15


def c_to_k(celsius: float) -> float:
    """Convert Celsius to Kelvin."""
    return celsius + 273.15


def format_temp(kelvin: float, show_both: bool = True) -> str:
    """Format a temperature value showing both K and C."""
    if show_both:
        return f"{kelvin:.0f} K ({k_to_c(kelvin):.0f} \u00b0C)"
    return f"{kelvin:.0f} K"


# --- Composition conversion ---

def mole_to_weight(mole_fractions: dict[str, float]) -> dict[str, float]:
    """Convert mole fractions to weight percent.

    Args:
        mole_fractions: Dict of element -> mole fraction (must sum to ~1.0).

    Returns:
        Dict of element -> weight percent (sums to ~100).
    """
    total_mass = sum(
        x * ATOMIC_WEIGHTS.get(el.upper(), 1.0)
        for el, x in mole_fractions.items()
        if el.upper() != "VA"
    )
    if total_mass <= 0:
        return {el: 0.0 for el in mole_fractions}

    return {
        el: (x * ATOMIC_WEIGHTS.get(el.upper(), 1.0) / total_mass) * 100.0
        for el, x in mole_fractions.items()
        if el.upper() != "VA"
    }


def weight_to_mole(weight_percents: dict[str, float]) -> dict[str, float]:
    """Convert weight percent to mole fractions.

    Args:
        weight_percents: Dict of element -> weight percent (should sum to ~100).

    Returns:
        Dict of element -> mole fraction (sums to ~1.0).
    """
    moles = {}
    for el, wt in weight_percents.items():
        aw = ATOMIC_WEIGHTS.get(el.upper(), 1.0)
        if aw > 0:
            moles[el] = wt / aw

    total_moles = sum(moles.values())
    if total_moles <= 0:
        return {el: 0.0 for el in weight_percents}

    return {el: m / total_moles for el, m in moles.items()}


def format_composition(value: float, mode: str = "mole_fraction") -> str:
    """Format a composition value based on current mode."""
    if mode == "weight_percent":
        return f"{value:.2f} wt%"
    return f"{value:.4f}"


# --- Pressure conversion ---

PRESSURE_UNITS: dict[str, float] = {
    "Pa": 1.0,
    "bar": 1e5,
    "atm": 101325.0,
    "GPa": 1e9,
}


def convert_pressure(value: float, from_unit: str, to_unit: str) -> float:
    """Convert pressure between units."""
    pa = value * PRESSURE_UNITS[from_unit]
    return pa / PRESSURE_UNITS[to_unit]


def format_pressure(pa_value: float) -> str:
    """Format a pressure value in a human-readable way."""
    if pa_value >= 1e9:
        return f"{pa_value / 1e9:.2f} GPa"
    if pa_value >= 1e5:
        return f"{pa_value / 1e5:.2f} bar"
    return f"{pa_value:.0f} Pa"
