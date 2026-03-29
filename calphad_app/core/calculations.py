"""CALPHAD calculation wrappers around pycalphad."""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from pycalphad import Database, equilibrium, variables as v
from pycalphad.mapping import BinaryStrategy, StepStrategy


# ---------------------------------------------------------------------------
# Data classes for results
# ---------------------------------------------------------------------------

@dataclass
class EquilibriumResult:
    """Holds results of a single equilibrium calculation."""
    phases: list[str] = field(default_factory=list)
    fractions: list[float] = field(default_factory=list)
    compositions: list[dict[str, float]] = field(default_factory=list)
    temperature: float = 0.0
    pressure: float = 101325.0
    error: str | None = None

    def to_dataframe(self) -> pd.DataFrame:
        rows = []
        for phase, frac, comp in zip(self.phases, self.fractions, self.compositions):
            row = {"Phase": phase, "Fraction": round(frac, 6)}
            for el, val in comp.items():
                row[f"X({el})"] = round(val, 6)
            rows.append(row)
        return pd.DataFrame(rows)


@dataclass
class SteppingResult:
    """Holds results of a stepping (1-D scan) calculation."""
    temperatures: np.ndarray = field(default_factory=lambda: np.array([]))
    phase_fractions: dict[str, np.ndarray] = field(default_factory=dict)
    solidus: float | None = None
    liquidus: float | None = None
    error: str | None = None

    def to_dataframe(self) -> pd.DataFrame:
        data: dict[str, list] = {"Temperature (K)": list(self.temperatures)}
        for phase, fracs in self.phase_fractions.items():
            data[f"NP({phase})"] = list(fracs)
        return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# Calculation functions
# ---------------------------------------------------------------------------

def calculate_binary_phase_diagram(
    db: Database,
    el1: str,
    el2: str,
    t_min: float = 300.0,
    t_max: float = 2000.0,
) -> tuple[object, str | None]:
    """Calculate a binary phase diagram using pycalphad mapping.

    Returns (strategy, error_string_or_None).
    """
    try:
        comps = sorted([el1.upper(), el2.upper()]) + ["VA"]
        phases = list(db.phases.keys())

        strategy = BinaryStrategy(
            db,
            comps,
            phases,
            conditions={
                v.T: (t_min, t_max, 10),
                v.X(el2.upper()): (0, 1, 0.01),
                v.P: 101325,
                v.N: 1,
            },
        )
        strategy.do_map()

        return strategy, None
    except Exception:
        return None, traceback.format_exc()


def calculate_equilibrium_point(
    db: Database,
    elements: list[str],
    compositions: dict[str, float],
    temperature: float,
    pressure: float = 101325.0,
) -> EquilibriumResult:
    """Calculate equilibrium at a single point."""
    result = EquilibriumResult(temperature=temperature, pressure=pressure)
    try:
        comps = sorted([e.upper() for e in elements]) + ["VA"]
        phases = list(db.phases.keys())

        conds = {v.T: temperature, v.P: pressure, v.N: 1}
        for el, x in compositions.items():
            conds[v.X(el.upper())] = x

        eq = equilibrium(db, comps, phases, conds)

        # Extract phase data from the xarray result
        phase_names = eq.Phase.values.squeeze()
        np_values = eq.NP.values.squeeze()

        if phase_names.ndim == 0:
            phase_names = np.array([phase_names])
            np_values = np.array([np_values])

        for i, (pname, frac) in enumerate(zip(phase_names, np_values)):
            pname_str = str(pname).strip()
            if pname_str == "" or frac <= 1e-10 or np.isnan(frac):
                continue
            result.phases.append(pname_str)
            result.fractions.append(float(frac))

            comp_dict = {}
            for el in elements:
                try:
                    x_val = float(eq.X.sel(component=el.upper()).values.squeeze()[i])
                    comp_dict[el.upper()] = x_val
                except Exception:
                    comp_dict[el.upper()] = float("nan")
            result.compositions.append(comp_dict)

    except Exception:
        result.error = traceback.format_exc()
    return result


def calculate_stepping(
    db: Database,
    elements: list[str],
    compositions: dict[str, float],
    t_min: float = 300.0,
    t_max: float = 2000.0,
    t_step: float = 5.0,
    pressure: float = 101325.0,
) -> SteppingResult:
    """Step through temperature at fixed composition using StepStrategy."""
    result = SteppingResult()
    try:
        comps = sorted([e.upper() for e in elements]) + ["VA"]
        phases = list(db.phases.keys())

        conds = {v.P: pressure, v.N: 1}
        for el, x in compositions.items():
            conds[v.X(el.upper())] = x

        conds[v.T] = (t_min, t_max, t_step)

        strategy = StepStrategy(
            db,
            comps,
            phases,
            conditions=conds,
        )
        strategy.do_map()

        temps = []
        phase_frac_data: dict[str, list[float]] = {}

        for node in strategy.node_queue.nodes:
            T = float(node.global_conditions.get(v.T, np.nan))
            if np.isnan(T):
                continue
            temps.append(T)
            node_phases = {}
            for stable_comp in node.stable_composition_sets:
                pname = stable_comp.phase_record.phase_name
                npval = float(stable_comp.NP)
                node_phases[pname] = node_phases.get(pname, 0.0) + npval
            for pname in node_phases:
                if pname not in phase_frac_data:
                    phase_frac_data[pname] = [0.0] * (len(temps) - 1)
                phase_frac_data[pname].append(node_phases[pname])
            for pname in phase_frac_data:
                if pname not in node_phases:
                    phase_frac_data[pname].append(0.0)

        if temps:
            result.temperatures = np.array(temps)
            result.phase_fractions = {k: np.array(v_arr) for k, v_arr in phase_frac_data.items()}

            # Find solidus/liquidus
            if "LIQUID" in phase_frac_data:
                liq = np.array(phase_frac_data["LIQUID"])
                t_arr = np.array(temps)
                liq_indices = np.where(liq > 0.01)[0]
                if len(liq_indices) > 0:
                    result.solidus = float(t_arr[liq_indices[0]])
                    result.liquidus = float(t_arr[liq_indices[-1]])
                    # Solidus is where liquid first appears, liquidus where it's 100%
                    full_liq = np.where(liq > 0.99)[0]
                    if len(full_liq) > 0:
                        result.liquidus = float(t_arr[full_liq[0]])
        else:
            # Fallback: use direct equilibrium calls
            result = _stepping_fallback(db, comps, phases, compositions, t_min, t_max, t_step, pressure)

    except Exception:
        # Fallback to direct equilibrium
        try:
            comps = sorted([e.upper() for e in elements]) + ["VA"]
            phases = list(db.phases.keys())
            result = _stepping_fallback(db, comps, phases, compositions, t_min, t_max, t_step, pressure)
        except Exception:
            result.error = traceback.format_exc()
    return result


def calculate_ternary_isothermal(
    db: Database,
    el1: str,
    el2: str,
    el3: str,
    temperature: float,
    pressure: float = 101325.0,
) -> tuple[object, str | None]:
    """Calculate a ternary isothermal section at fixed temperature."""
    try:
        from pycalphad.mapping import TernaryStrategy
        comps = sorted([el1.upper(), el2.upper(), el3.upper()]) + ["VA"]
        phases = list(db.phases.keys())
        strategy = TernaryStrategy(
            db, comps, phases,
            conditions={
                v.T: temperature,
                v.X(el2.upper()): (0, 1, 0.015),
                v.X(el3.upper()): (0, 1, 0.015),
                v.P: pressure, v.N: 1,
            },
        )
        strategy.do_map()
        return strategy, None
    except Exception:
        return None, traceback.format_exc()


def calculate_isopleth(
    db: Database,
    elements: list[str],
    fixed_el: str,
    fixed_comp: float,
    varied_el: str,
    t_min: float = 300.0,
    t_max: float = 2000.0,
    pressure: float = 101325.0,
) -> tuple[object, str | None]:
    """Calculate an isopleth (pseudo-binary section) through multicomponent space."""
    try:
        from pycalphad.mapping import IsoplethStrategy
        comps = sorted([e.upper() for e in elements]) + ["VA"]
        phases = list(db.phases.keys())
        strategy = IsoplethStrategy(
            db, comps, phases,
            conditions={
                v.T: (t_min, t_max, 10),
                v.X(fixed_el.upper()): fixed_comp,
                v.X(varied_el.upper()): (0, 1, 0.01),
                v.P: pressure, v.N: 1,
            },
        )
        strategy.do_map()
        return strategy, None
    except Exception:
        return None, traceback.format_exc()


def _stepping_fallback(
    db: Database,
    comps: list[str],
    phases: list[str],
    compositions: dict[str, float],
    t_min: float,
    t_max: float,
    t_step: float,
    pressure: float,
) -> SteppingResult:
    """Fallback stepping using point-by-point equilibrium calls."""
    result = SteppingResult()
    temps = np.arange(t_min, t_max + t_step / 2, t_step)
    phase_frac_data: dict[str, list[float]] = {}

    for T in temps:
        conds = {v.T: float(T), v.P: pressure, v.N: 1}
        for el, x in compositions.items():
            conds[v.X(el.upper())] = x

        try:
            eq = equilibrium(db, comps, phases, conds)
            phase_names = eq.Phase.values.squeeze()
            np_values = eq.NP.values.squeeze()

            if phase_names.ndim == 0:
                phase_names = np.array([phase_names])
                np_values = np.array([np_values])

            current_phases = {}
            for pname, frac in zip(phase_names, np_values):
                pname_str = str(pname).strip()
                if pname_str and not np.isnan(frac) and frac > 1e-10:
                    current_phases[pname_str] = current_phases.get(pname_str, 0.0) + float(frac)

            for pname in current_phases:
                if pname not in phase_frac_data:
                    phase_frac_data[pname] = [0.0] * len(result.temperatures) if len(result.temperatures) else []

            for pname in phase_frac_data:
                phase_frac_data[pname].append(current_phases.get(pname, 0.0))

        except Exception:
            for pname in phase_frac_data:
                phase_frac_data[pname].append(0.0)

    result.temperatures = temps
    result.phase_fractions = {k: np.array(v_arr) for k, v_arr in phase_frac_data.items()}

    # Find solidus/liquidus
    if "LIQUID" in phase_frac_data:
        liq = np.array(phase_frac_data["LIQUID"])
        liq_indices = np.where(liq > 0.01)[0]
        if len(liq_indices) > 0:
            result.solidus = float(temps[liq_indices[0]])
            full_liq = np.where(liq > 0.99)[0]
            if len(full_liq) > 0:
                result.liquidus = float(temps[full_liq[0]])
            else:
                result.liquidus = float(temps[liq_indices[-1]])

    return result
