"""Smart error messages that reference the loaded database contents.

Every calculation panel should use build_error_message() instead of
showing raw tracebacks or generic advice. This module inspects the
currently-loaded Database to tell the user exactly what elements,
phases, and conditions are available.
"""

from __future__ import annotations

from pycalphad import Database

from core.presets import (
    MELTING_POINTS_K, get_binary_preset, BINARY_SYSTEMS,
    translate_phase_short, ALLOY_PRESETS,
)
from core.units import k_to_c


def _db_elements(db: Database | None) -> list[str]:
    """Return sorted list of real elements in the database (no VA, /-)."""
    if db is None:
        return []
    return sorted(
        str(el) for el in db.elements
        if str(el) not in ("/-", "VA", "", "*", "%")
    )


def _db_phases(db: Database | None) -> list[str]:
    """Return sorted list of phases in the database."""
    if db is None:
        return []
    return sorted(db.phases.keys())


def _suggest_systems(elements: list[str]) -> str:
    """Suggest known binary systems from the available elements."""
    suggestions = []
    for (e1, e2), preset in BINARY_SYSTEMS.items():
        if e1 in elements and e2 in elements:
            suggestions.append(f"{e1}-{e2}")
    if suggestions:
        return ", ".join(suggestions[:8])
    return "Al-Cu, Al-Si, Al-Mg (load a database with these elements)"


def _suggest_alloys(elements: list[str]) -> str:
    """Suggest real alloy presets that match the available elements."""
    matches = []
    el_set = set(e.upper() for e in elements)
    for preset in ALLOY_PRESETS:
        if all(e.upper() in el_set for e in preset.elements):
            matches.append(f"{preset.name} ({preset.designation})")
    if matches:
        return ", ".join(matches[:5])
    return ""


def _temp_hint(elements: list[str]) -> str:
    """Suggest a temperature range based on melting points."""
    mps = []
    for el in elements:
        mp = MELTING_POINTS_K.get(el.upper())
        if mp:
            mps.append((el.upper(), mp))
    if not mps:
        return "Try 300–1500 K (room temperature to typical melting range)."
    parts = [f"{el}: {mp:.0f} K ({k_to_c(mp):.0f} °C)" for el, mp in mps]
    lowest = min(mp for _, mp in mps)
    highest = max(mp for _, mp in mps)
    safe_min = max(200, lowest * 0.3)
    safe_max = min(highest * 1.15, 5000)
    return (
        f"Melting points: {', '.join(parts)}. "
        f"Suggested range: {safe_min:.0f}–{safe_max:.0f} K "
        f"({k_to_c(safe_min):.0f}–{k_to_c(safe_max):.0f} °C)."
    )


def build_error_message(
    raw_error: str,
    db: Database | None = None,
    calc_type: str = "calculation",
    elements_used: list[str] | None = None,
    temperature: float | None = None,
    composition: dict[str, float] | None = None,
) -> tuple[str, str]:
    """Build a user-friendly error message with database-aware suggestions.

    Returns (friendly_message, technical_details).
    """
    error_lower = raw_error.lower()
    db_elements = _db_elements(db)

    # ---- Diagnose the specific error ----

    if "degrees of freedom" in error_lower or "number of degrees" in error_lower:
        title = "The equilibrium calculation could not find a valid starting point."
        reason = (
            "This usually means the conditions you specified don't match "
            "what the database can calculate — either an element isn't in "
            "the database, the composition is outside the valid range, "
            "or the temperature is unrealistic for this system."
        )
    elif "no valid tieline" in error_lower or "zpf" in error_lower:
        title = "The phase boundary mapper could not find stable boundaries."
        reason = (
            "The database may not have enough interaction parameters for "
            "this element combination, or the temperature range may be "
            "too wide or too narrow."
        )
    elif "singular" in error_lower or "convergence" in error_lower or "did not converge" in error_lower:
        title = "The numerical solver could not converge."
        reason = (
            "This sometimes happens near phase boundaries or at extreme "
            "compositions. Small adjustments to temperature or composition "
            "often fix it."
        )
    elif "memory" in error_lower or "killed" in error_lower:
        title = "The calculation ran out of memory."
        reason = "Try a narrower temperature range or larger step size."
    elif "database" in error_lower or "key" in error_lower and "phase" in error_lower:
        title = "The database does not support this element or phase combination."
        reason = "The loaded TDB file may not contain interaction parameters for these elements together."
    elif "composition" in error_lower or "out of range" in error_lower:
        title = "A composition value is outside the valid range."
        reason = "Mole fractions must be between 0 and 1 (total ≤ 1). Weight percent must total ≤ 100%."
    else:
        title = f"The {calc_type} did not succeed."
        reason = (
            "This can happen when the thermodynamic database does not "
            "cover the requested conditions."
        )

    # ---- Build suggestions section ----

    suggestions = ["\nSuggestions:"]

    # 1. Check if elements are in the database
    if elements_used and db_elements:
        missing = [e for e in elements_used if e.upper() not in [d.upper() for d in db_elements]]
        if missing:
            suggestions.append(
                f"  ✗ Element(s) {', '.join(missing)} are NOT in this database."
            )
            suggestions.append(
                f"    Available elements: {', '.join(db_elements)}"
            )
        else:
            suggestions.append(
                f"  ✓ All selected elements ({', '.join(elements_used)}) are in the database."
            )

    # 2. Available elements
    if db_elements:
        suggestions.append(
            f"  • This database contains {len(db_elements)} elements: "
            f"{', '.join(db_elements[:15])}"
            f"{'...' if len(db_elements) > 15 else ''}"
        )

    # 3. Known alloy systems
    if db_elements:
        systems = _suggest_systems(db_elements)
        if systems:
            suggestions.append(f"  • Known alloy systems in this database: {systems}")

    # 4. Real alloy suggestions
    if db_elements:
        alloys = _suggest_alloys(db_elements)
        if alloys:
            suggestions.append(f"  • Try a real alloy preset: {alloys}")

    # 5. Temperature hint
    if elements_used:
        temp_hint = _temp_hint(elements_used)
        suggestions.append(f"  • {temp_hint}")

    # 6. Current temperature feedback
    if temperature is not None and elements_used:
        mps = [MELTING_POINTS_K.get(e.upper()) for e in elements_used]
        mps = [m for m in mps if m is not None]
        if mps:
            max_mp = max(mps)
            if temperature > max_mp * 1.5:
                suggestions.append(
                    f"  ⚠ Your temperature ({temperature:.0f} K) is much higher than "
                    f"the highest melting point ({max_mp:.0f} K). Try a lower value."
                )
            elif temperature < 100:
                suggestions.append(
                    f"  ⚠ Your temperature ({temperature:.0f} K) is very low. "
                    f"Most metallurgical calculations use 300+ K."
                )

    # 7. Composition feedback
    if composition:
        total = sum(composition.values())
        if total > 1.01:
            suggestions.append(
                f"  ⚠ Compositions sum to {total:.3f} — this exceeds 1.0. "
                f"Reduce values so they total ≤ 1.0 (the balance element makes up the rest)."
            )

    # 8. General tips
    suggestions.append("")
    suggestions.append("General tips:")
    suggestions.append("  • Start with a preset alloy from the Database tab")
    suggestions.append("  • Use the Phase Diagram tab first to see what phases exist")
    suggestions.append("  • Smaller temperature ranges calculate faster and more reliably")

    friendly = f"{title}\n\n{reason}\n" + "\n".join(suggestions)

    # Technical details (collapsed in UI)
    last_lines = raw_error.strip().split("\n")[-5:]
    technical = "\n".join(last_lines)

    return friendly, technical
