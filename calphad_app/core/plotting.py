"""Plotting utilities for CALPHAD results using matplotlib."""

from __future__ import annotations

import numpy as np
from matplotlib.figure import Figure
from pycalphad.mapping import BinaryStrategy

from core.presets import translate_phase_short, ATOMIC_WEIGHTS
from core.units import k_to_c


# Consistent color palette for phases
PHASE_COLORS = [
    "#4FC3F7", "#81C784", "#FFB74D", "#E57373", "#BA68C8",
    "#4DB6AC", "#FFD54F", "#7986CB", "#A1887F", "#90A4AE",
    "#F06292", "#AED581", "#64B5F6", "#FF8A65", "#CE93D8",
]


def get_phase_color(index: int) -> str:
    return PHASE_COLORS[index % len(PHASE_COLORS)]


def _add_celsius_secondary_axis(ax, axis: str = "y") -> None:
    """Add a secondary axis showing temperature in Celsius alongside Kelvin.

    Parameters
    ----------
    ax : matplotlib Axes
        The primary axes whose *axis* is in Kelvin.
    axis : str
        ``'y'`` or ``'x'`` -- which axis carries the temperature.
    """
    if axis == "y":
        sec = ax.secondary_yaxis(
            "right",
            functions=(k_to_c, lambda c: c + 273.15),
        )
        sec.set_ylabel("Temperature (\u00b0C)", color="#aaaacc", fontsize=11)
    else:
        sec = ax.secondary_xaxis(
            "top",
            functions=(k_to_c, lambda c: c + 273.15),
        )
        sec.set_xlabel("Temperature (\u00b0C)", color="#aaaacc", fontsize=11)

    sec.tick_params(colors="#aaaacc")
    return sec


def plot_binary_phase_diagram(
    fig: Figure,
    strategy: BinaryStrategy,
    el1: str,
    el2: str,
    t_min: float = 300.0,
    t_max: float = 2000.0,
    subtitle: str | None = None,
    comp_unit: str = "mole_fraction",
) -> None:
    """Plot a binary phase diagram onto a matplotlib Figure.

    Parameters
    ----------
    subtitle : str, optional
        Additional line shown below the title (e.g. calculation conditions).
    """
    fig.clear()
    ax = fig.add_subplot(111)

    ax.set_facecolor("#1e1e2e")
    fig.patch.set_facecolor("#1e1e2e")

    try:
        _plot_binary_solid_fills(ax, strategy)
    except Exception:
        # Manual fallback: extract data from strategy nodes
        _plot_binary_manual(ax, strategy, el2)

    ax.set_xlabel(f"Mole fraction {el2}", color="white", fontsize=12)
    ax.set_ylabel("Temperature (K)", color="white", fontsize=12)

    # Title with optional subtitle for metadata / conditions
    title_text = f"{el1}-{el2} Phase Diagram"
    if subtitle:
        title_text += f"\n{subtitle}"
    ax.set_title(title_text, color="white", fontsize=14, fontweight="bold")

    ax.set_xlim(0, 1)
    ax.set_ylim(t_min, t_max)

    # Weight percent X-axis: relabel ticks to show wt% at correct mole frac positions
    if comp_unit == "weight_percent":
        ax.set_xlabel(f"Weight percent {el2}", color="white", fontsize=12)
        aw1 = ATOMIC_WEIGHTS.get(el1.upper(), 1.0)
        aw2 = ATOMIC_WEIGHTS.get(el2.upper(), 1.0)
        wt_ticks = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        mole_positions = []
        for wt in wt_ticks:
            if wt <= 0:
                mole_positions.append(0.0)
            elif wt >= 100:
                mole_positions.append(1.0)
            else:
                mole_positions.append((wt / aw2) / (wt / aw2 + (100 - wt) / aw1))
        ax.set_xticks(mole_positions)
        ax.set_xticklabels([f"{w:.0f}" for w in wt_ticks])

    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#555555")
    ax.grid(True, alpha=0.2, color="#555555")

    # Translate legend labels to friendly phase names and reposition
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        short_labels = [translate_phase_short(l) for l in labels]
        leg = ax.legend(
            handles, short_labels,
            fontsize=8, loc="upper left",
            frameon=True, framealpha=0.9,
            ncol=2, handlelength=1.5, borderaxespad=0.5,
        )
        leg.get_frame().set_facecolor("#2d2d3e")
        for text in leg.get_texts():
            text.set_color("white")

    # Secondary Celsius axis on the right-hand side
    try:
        _add_celsius_secondary_axis(ax, axis="y")
    except Exception:
        pass  # Primary axis still works; skip secondary if it fails

    # --- Labeled phase regions (#14) ---
    _label_phase_regions(ax, strategy, el2, t_min, t_max)

    # Educational annotation (Improvement 20)
    edu_text = (
        "Reading this diagram:\n"
        "- X-axis: composition (how much of each element)\n"
        "- Y-axis: temperature\n"
        "- Each colored region is a different phase (crystal structure)\n"
        "- Boundary lines show where phases change"
    )
    ax.text(0.98, 0.02, edu_text, transform=ax.transAxes,
            fontsize=7, color="#888888", ha="right", va="bottom",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#1e1e2e", alpha=0.9))

    fig.tight_layout(rect=[0, 0, 0.88, 1])


def _plot_binary_solid_fills(ax, strategy) -> None:
    """Render a binary phase diagram with solid semi-transparent fills.

    Uses pycalphad's strategy data API directly to draw:
    - Semi-transparent solid fills for two-phase regions
    - Solid phase boundary lines
    - Invariant (three-phase) horizontal lines
    """
    from matplotlib.colors import to_rgba
    import pycalphad.mapping.utils as map_utils
    from pycalphad import variables as v
    from pycalphad.plot.utils import phase_legend

    sorted_axis_var = map_utils._sort_axis_by_state_vars(strategy.axis_vars)
    x_var = sorted_axis_var[1]  # composition
    y_var = sorted_axis_var[0]  # temperature

    phases = sorted(strategy.get_all_phases())
    handles, phase_colors = phase_legend(phases)

    # --- Tone down bright colors and build a muted mapping ---
    # phase_legend keys are UPPER-cased; store both cases for robust lookup
    _FILL_ALPHA = 0.30
    _LINE_ALPHA = 0.90
    _muted_colors = {}
    for phase_name, rgba in phase_colors.items():
        r, g, b, a = to_rgba(rgba)
        # Desaturate slightly: blend toward grey to avoid neon greens/blues
        grey = 0.45
        blend = 0.25  # 25% toward grey
        r = r * (1 - blend) + grey * blend
        g = g * (1 - blend) + grey * blend
        b = b * (1 - blend) + grey * blend
        _muted_colors[phase_name] = (r, g, b)
        _muted_colors[phase_name.upper()] = (r, g, b)

    # --- Draw filled two-phase regions and boundary lines ---
    tieline_data = strategy.get_tieline_data(x_var, y_var)
    region_index = 0
    for region in tieline_data:
        # Each region has boundary curves for 2+ coexisting phases
        # For binary diagrams, typically 2 phases per region
        phase_data_list = region.data
        if len(phase_data_list) >= 2:
            # Fill between the two boundary curves
            # Sort each curve by y (temperature) so fill_betweenx works
            x_arrays = []
            y_arrays = []
            for pd in phase_data_list:
                xi = np.asarray(pd.x, dtype=float)
                yi = np.asarray(pd.y, dtype=float)
                # Remove NaN values
                valid = ~(np.isnan(xi) | np.isnan(yi))
                x_arrays.append(xi[valid])
                y_arrays.append(yi[valid])

            if len(x_arrays) >= 2 and len(x_arrays[0]) > 1 and len(x_arrays[1]) > 1:
                # Interpolate both curves onto a common temperature grid
                y_all = np.concatenate(y_arrays)
                y_min_r, y_max_r = np.nanmin(y_all), np.nanmax(y_all)
                if y_max_r > y_min_r:
                    y_common = np.linspace(y_min_r, y_max_r, 300)

                    # Sort each curve by temperature for interpolation
                    order0 = np.argsort(y_arrays[0])
                    order1 = np.argsort(y_arrays[1])
                    x0_interp = np.interp(y_common, y_arrays[0][order0], x_arrays[0][order0])
                    x1_interp = np.interp(y_common, y_arrays[1][order1], x_arrays[1][order1])

                    # Pick a fill color from the first phase in the region
                    fill_phase = phase_data_list[0].phase
                    fc = _muted_colors.get(fill_phase,
                         _muted_colors.get(fill_phase.upper(), (0.5, 0.5, 0.5)))
                    ax.fill_betweenx(
                        y_common,
                        x0_interp, x1_interp,
                        color=(*fc, _FILL_ALPHA),
                        edgecolor="none",
                        zorder=1,
                    )

        # Draw boundary lines for every phase in the region
        for pd in phase_data_list:
            xi = np.asarray(pd.x, dtype=float)
            yi = np.asarray(pd.y, dtype=float)
            valid = ~(np.isnan(xi) | np.isnan(yi))
            if np.any(valid):
                lc = _muted_colors.get(pd.phase,
                     _muted_colors.get(pd.phase.upper(), (0.7, 0.7, 0.7)))
                ax.plot(
                    xi[valid], yi[valid],
                    color=(*lc, _LINE_ALPHA),
                    linewidth=1.2,
                    solid_capstyle="butt",
                    zorder=3,
                )
        region_index += 1

    # --- Draw invariant (three-phase) lines ---
    invariant_data = strategy.get_invariant_data(x_var, y_var)
    for inv in invariant_data:
        inv_x = np.array([d.x for d in inv.data], dtype=float)
        inv_y = np.array([d.y for d in inv.data], dtype=float)
        # Close the triangle / connect endpoints
        inv_x_closed = np.concatenate([inv_x, [inv_x[0]]])
        inv_y_closed = np.concatenate([inv_y, [inv_y[0]]])
        ax.plot(
            inv_x_closed, inv_y_closed,
            color=(0.85, 0.25, 0.25, 0.9),
            linewidth=1.0,
            solid_capstyle="butt",
            zorder=4,
        )

    # --- Build a legend from the phase boundaries ---
    seen_phases = {}
    for region in tieline_data:
        for pd in region.data:
            if pd.phase not in seen_phases:
                lc = _muted_colors.get(pd.phase,
                     _muted_colors.get(pd.phase.upper(), (0.7, 0.7, 0.7)))
                friendly = translate_phase_short(pd.phase)
                seen_phases[pd.phase] = ax.plot(
                    [], [],
                    color=(*lc, _LINE_ALPHA),
                    linewidth=2,
                    label=friendly,
                )[0]
    # Legend is built and positioned by plot_binary_phase_diagram


def _label_phase_regions(ax, strategy, comp_element: str,
                         t_min: float, t_max: float) -> None:
    """Attempt to label phase regions at their approximate centres.

    This scans the strategy data to build bounding boxes for each unique
    set of coexisting phases and places a text annotation at the centroid.
    """
    from collections import defaultdict

    region_points: dict[str, list[tuple[float, float]]] = defaultdict(list)

    for zpf_line in getattr(strategy, "zpf_lines", []):
        for point in zpf_line.points:
            try:
                T = float(point.global_conditions.get("T", np.nan))
                if np.isnan(T) or T < t_min or T > t_max:
                    continue
                phase_names = sorted(
                    cs.phase_record.phase_name
                    for cs in point.stable_composition_sets
                )
                region_key = " + ".join(
                    translate_phase_short(p) for p in phase_names
                )
                xs = [
                    float(cs.X[1]) if len(cs.X) > 1 else 0.0
                    for cs in point.stable_composition_sets
                ]
                x_mid = float(np.mean(xs))
                region_points[region_key].append((x_mid, T))
            except Exception:
                continue

    import matplotlib.patheffects as pe

    placed: list[tuple[float, float]] = []
    for label, pts in region_points.items():
        if len(pts) < 3:
            continue
        xs, ts = zip(*pts)
        cx, ct = float(np.mean(xs)), float(np.mean(ts))
        # Avoid overlapping labels (simple distance check)
        too_close = any(
            abs(cx - px) < 0.08 and abs(ct - pt) < (t_max - t_min) * 0.06
            for px, pt in placed
        )
        if too_close:
            continue
        placed.append((cx, ct))
        ax.text(
            cx, ct, label,
            color="#ffffff",
            fontsize=10,
            fontweight="bold",
            ha="center", va="center",
            bbox=dict(
                boxstyle="round,pad=0.35",
                facecolor="#1e1e2eee",
                edgecolor="#888888",
                linewidth=1,
                alpha=0.95,
            ),
            path_effects=[
                pe.withStroke(linewidth=3, foreground="#000000"),
            ],
            zorder=25,
        )


def _plot_binary_manual(ax, strategy, el2: str) -> None:
    """Fallback manual plotting from strategy node data."""
    phase_points: dict[str, list[tuple[float, float]]] = {}

    for zpf_line in strategy.zpf_lines:
        for point in zpf_line.points:
            try:
                T = float(point.global_conditions.get("T", np.nan))
                if np.isnan(T):
                    continue
                for comp_set in point.stable_composition_sets:
                    pname = comp_set.phase_record.phase_name
                    x_val = float(comp_set.X[1]) if len(comp_set.X) > 1 else 0.0
                    if pname not in phase_points:
                        phase_points[pname] = []
                    phase_points[pname].append((x_val, T))
            except Exception:
                continue

    for i, (phase, pts) in enumerate(phase_points.items()):
        if pts:
            xs, ts = zip(*pts)
            friendly = translate_phase_short(phase)
            ax.scatter(xs, ts, s=2, color=get_phase_color(i),
                       label=friendly, alpha=0.7)

    ax.legend(fontsize=8, loc="best")


def plot_stepping_result(
    fig: Figure,
    temperatures: np.ndarray,
    phase_fractions: dict[str, np.ndarray],
    solidus: float | None = None,
    liquidus: float | None = None,
    title: str = "Phase Fractions vs Temperature",
    subtitle: str | None = None,
) -> None:
    """Plot phase fractions vs temperature.

    Parameters
    ----------
    subtitle : str, optional
        Additional line shown below the title (e.g. calculation conditions).
    """
    fig.clear()
    ax = fig.add_subplot(111)

    ax.set_facecolor("#1e1e2e")
    fig.patch.set_facecolor("#1e1e2e")

    for i, (phase, fracs) in enumerate(phase_fractions.items()):
        n = min(len(temperatures), len(fracs))
        friendly = translate_phase_short(phase)
        ax.plot(
            temperatures[:n], fracs[:n],
            color=get_phase_color(i),
            label=friendly,
            linewidth=2,
        )

    # Solidus / liquidus markers with dual K / C display
    if solidus is not None:
        sol_c = k_to_c(solidus)
        ax.axvline(solidus, color="#FF5252", linestyle="--", alpha=0.7,
                   label=f"Solidus ({solidus:.0f} K / {sol_c:.0f} \u00b0C)")
    if liquidus is not None:
        liq_c = k_to_c(liquidus)
        ax.axvline(liquidus, color="#FFAB40", linestyle="--", alpha=0.7,
                   label=f"Liquidus ({liquidus:.0f} K / {liq_c:.0f} \u00b0C)")

    ax.set_xlabel("Temperature (K)", color="white", fontsize=12)
    ax.set_ylabel("Phase Fraction", color="white", fontsize=12)

    title_text = title
    if subtitle:
        title_text += f"\n{subtitle}"
    ax.set_title(title_text, color="white", fontsize=14, fontweight="bold")
    ax.set_ylim(-0.05, 1.05)

    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#555555")
    ax.grid(True, alpha=0.2, color="#555555")

    legend = ax.legend(fontsize=9, loc="best")
    legend.get_frame().set_facecolor("#2d2d3e")
    for text in legend.get_texts():
        text.set_color("white")

    # Secondary Celsius axis on the top
    try:
        _add_celsius_secondary_axis(ax, axis="x")
    except Exception:
        pass  # Primary axis still works; skip secondary if it fails

    fig.tight_layout()


def plot_equilibrium_bar(
    fig: Figure,
    phases: list[str],
    fractions: list[float],
    temperature: float,
    subtitle: str | None = None,
) -> None:
    """Plot equilibrium phase fractions as a horizontal bar chart.

    Parameters
    ----------
    subtitle : str, optional
        Additional line shown below the title (e.g. calculation conditions).
    """
    fig.clear()
    ax = fig.add_subplot(111)

    ax.set_facecolor("#1e1e2e")
    fig.patch.set_facecolor("#1e1e2e")

    if not phases:
        ax.text(0.5, 0.5, "No stable phases found", ha="center", va="center",
                color="white", fontsize=14, transform=ax.transAxes)
        fig.tight_layout()
        return

    # Translate phase names for display
    friendly_phases = [translate_phase_short(p) for p in phases]

    colors = [get_phase_color(i) for i in range(len(phases))]
    y_pos = np.arange(len(phases))

    bars = ax.barh(y_pos, fractions, color=colors, edgecolor="#333333", height=0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(friendly_phases, color="white", fontsize=11)
    ax.set_xlabel("Phase Fraction", color="white", fontsize=12)

    # Title with temperature in both K and C
    temp_c = k_to_c(temperature)
    title_text = f"Equilibrium at {temperature:.0f} K ({temp_c:.0f} \u00b0C)"
    if subtitle:
        title_text += f"\n{subtitle}"
    ax.set_title(title_text, color="white", fontsize=14, fontweight="bold")
    ax.set_xlim(0, 1.05)

    for bar, frac in zip(bars, fractions):
        ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height() / 2,
                f"{frac:.4f}", va="center", color="white", fontsize=10)

    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#555555")
    ax.grid(True, alpha=0.2, color="#555555", axis="x")

    fig.tight_layout()


def plot_ternary_isothermal(
    fig: Figure,
    strategy,
    el1: str,
    el2: str,
    el3: str,
    temperature: float,
    subtitle: str | None = None,
) -> None:
    """Plot a ternary isothermal section."""
    fig.clear()
    ax = fig.add_subplot(111)
    ax.set_facecolor("#1e1e2e")
    fig.patch.set_facecolor("#1e1e2e")

    try:
        from pycalphad.mapping.plotting import plot_ternary
        plot_ternary(strategy, ax=ax)
    except Exception:
        ax.text(0.5, 0.5,
                "Could not render ternary diagram.\nTry a different temperature.",
                ha="center", va="center", color="#E57373", fontsize=12,
                transform=ax.transAxes)

    ax.set_title(
        f"{el1}-{el2}-{el3} at {temperature:.0f} K ({k_to_c(temperature):.0f} \u00b0C)",
        color="white", fontsize=14, fontweight="bold",
    )
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#555555")

    if ax.get_legend():
        ax.get_legend().get_frame().set_facecolor("#2d2d3e")
        for text in ax.get_legend().get_texts():
            text.set_color("white")

    if subtitle:
        fig.text(0.5, 0.01, subtitle, ha="center", color="#888888", fontsize=9)
    fig.tight_layout()


def plot_composition_stepping(
    fig: Figure,
    compositions: np.ndarray,
    phase_fractions: dict[str, np.ndarray],
    varied_el: str,
    temperature: float,
    subtitle: str | None = None,
    comp_unit: str = "mole_fraction",
) -> None:
    """Plot phase fractions vs composition at fixed temperature."""
    fig.clear()
    ax = fig.add_subplot(111)

    ax.set_facecolor("#1e1e2e")
    fig.patch.set_facecolor("#1e1e2e")

    for i, (phase, fracs) in enumerate(phase_fractions.items()):
        n = min(len(compositions), len(fracs))
        friendly = translate_phase_short(phase)
        ax.plot(
            compositions[:n], fracs[:n],
            color=get_phase_color(i),
            label=friendly,
            linewidth=2,
        )

    x_label = f"Weight percent {varied_el}" if comp_unit == "weight_percent" else f"Mole fraction {varied_el}"
    ax.set_xlabel(x_label, color="white", fontsize=12)
    ax.set_ylabel("Phase Fraction", color="white", fontsize=12)

    temp_c = k_to_c(temperature)
    title_text = f"Phase Fractions vs Composition at {temperature:.0f} K ({temp_c:.0f} \u00b0C)"
    if subtitle:
        title_text += f"\n{subtitle}"
    ax.set_title(title_text, color="white", fontsize=14, fontweight="bold")
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlim(compositions[0], compositions[-1])

    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#555555")
    ax.grid(True, alpha=0.2, color="#555555")

    legend = ax.legend(fontsize=9, loc="best")
    legend.get_frame().set_facecolor("#2d2d3e")
    for text in legend.get_texts():
        text.set_color("white")

    fig.tight_layout()


def plot_isopleth(
    fig: Figure,
    strategy,
    varied_el: str,
    fixed_el: str,
    fixed_comp: float,
    t_min: float = 300.0,
    t_max: float = 2000.0,
    subtitle: str | None = None,
) -> None:
    """Plot an isopleth (pseudo-binary section)."""
    fig.clear()
    ax = fig.add_subplot(111)
    ax.set_facecolor("#1e1e2e")
    fig.patch.set_facecolor("#1e1e2e")

    try:
        from pycalphad.mapping.plotting import plot_isopleth as _plot_iso
        _plot_iso(strategy, ax=ax)
    except Exception:
        ax.text(0.5, 0.5,
                "Could not render isopleth.\nTry different conditions.",
                ha="center", va="center", color="#E57373", fontsize=12,
                transform=ax.transAxes)

    ax.set_xlabel(f"Mole fraction {varied_el}", color="white", fontsize=12)
    ax.set_ylabel("Temperature (K)", color="white", fontsize=12)
    ax.set_title(
        f"Isopleth: {fixed_el} fixed at {fixed_comp:.2f}",
        color="white", fontsize=14, fontweight="bold",
    )
    ax.set_ylim(t_min, t_max)
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#555555")
    ax.grid(True, alpha=0.2, color="#555555")

    try:
        _add_celsius_secondary_axis(ax, axis="y")
    except Exception:
        pass

    if ax.get_legend():
        ax.get_legend().get_frame().set_facecolor("#2d2d3e")
        for text in ax.get_legend().get_texts():
            text.set_color("white")

    if subtitle:
        fig.text(0.5, 0.01, subtitle, ha="center", color="#888888", fontsize=9)
    fig.tight_layout()
