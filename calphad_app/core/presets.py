"""Alloy presets, phase name translations, and system-specific defaults."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BinarySystemPreset:
    """Temperature and composition defaults for a binary system."""
    el1: str
    el2: str
    t_min_k: float
    t_max_k: float
    comp_min: float  # mole fraction of el2
    comp_max: float
    eutectic_t_k: float | None = None
    eutectic_comp: float | None = None  # mole fraction of el2
    description: str = ""


@dataclass
class AlloyPreset:
    """A named commercial alloy with known composition."""
    name: str
    designation: str
    elements: list[str]
    composition_wt: dict[str, float]  # weight percent (balance element excluded)
    t_min_k: float = 300.0
    t_max_k: float = 1200.0
    application: str = ""
    category: str = ""


# --- Binary system defaults (used for auto-fill) ---

BINARY_SYSTEMS: dict[tuple[str, str], BinarySystemPreset] = {
    ("AL", "CU"): BinarySystemPreset("AL", "CU", 300, 1400, 0, 0.55, 821, 0.172,
                                      "Basis for 2xxx aerospace alloys"),
    ("AL", "SI"): BinarySystemPreset("AL", "SI", 300, 1300, 0, 0.30, 850, 0.126,
                                      "Basis for casting alloys (A356, A380)"),
    ("AL", "MG"): BinarySystemPreset("AL", "MG", 300, 1000, 0, 0.40, 723, 0.185,
                                      "Basis for 5xxx marine alloys"),
    ("AL", "ZN"): BinarySystemPreset("AL", "ZN", 200, 950, 0, 0.50, 654, 0.95,
                                      "Basis for 7xxx high-strength alloys"),
    ("AL", "MN"): BinarySystemPreset("AL", "MN", 300, 1000, 0, 0.10, None, None,
                                      "Basis for 3xxx general-purpose alloys"),
    ("AL", "FE"): BinarySystemPreset("AL", "FE", 300, 1600, 0, 0.50, 928, 0.02,
                                      "Fe is a common impurity in Al alloys"),
    ("AL", "NI"): BinarySystemPreset("AL", "NI", 300, 1950, 0, 1.0, None, None,
                                      "Basis for superalloy and intermetallic research"),
    ("MG", "AL"): BinarySystemPreset("MG", "AL", 300, 950, 0, 0.50, 710, 0.33,
                                      "Basis for AZ series Mg alloys"),
    ("MG", "ZN"): BinarySystemPreset("MG", "ZN", 200, 950, 0, 0.50, 613, 0.51,
                                      "Basis for ZK series Mg alloys"),
    ("CU", "ZN"): BinarySystemPreset("CU", "ZN", 200, 1400, 0, 0.50, None, None,
                                      "Brass alloys"),
    ("CU", "SN"): BinarySystemPreset("CU", "SN", 200, 1400, 0, 0.30, None, None,
                                      "Bronze alloys"),
    ("FE", "C"):  BinarySystemPreset("FE", "C", 500, 1900, 0, 0.10, 1420, 0.17,
                                      "Foundation of all steels"),
    ("FE", "CR"): BinarySystemPreset("FE", "CR", 500, 2200, 0, 1.0, None, None,
                                      "Stainless steel basis"),
    ("TI", "AL"): BinarySystemPreset("TI", "AL", 500, 2000, 0, 0.65, None, None,
                                      "Gamma-TiAl aerospace alloys"),
}


def get_binary_preset(el1: str, el2: str) -> BinarySystemPreset | None:
    """Look up binary system preset by element pair (order-independent)."""
    key1 = (el1.upper(), el2.upper())
    key2 = (el2.upper(), el1.upper())
    return BINARY_SYSTEMS.get(key1) or BINARY_SYSTEMS.get(key2)


# --- Commercial alloy presets ---

ALLOY_PRESETS: list[AlloyPreset] = [
    # Aluminum casting
    AlloyPreset("A356", "Al-7Si-0.3Mg", ["AL", "SI", "MG"],
                {"SI": 7.0, "MG": 0.35}, 400, 950,
                "Engine blocks, wheels, structural castings", "Al Casting"),
    AlloyPreset("A380", "Al-8.5Si-3.5Cu", ["AL", "SI", "CU"],
                {"SI": 8.5, "CU": 3.5}, 400, 950,
                "Die cast housings, brackets, covers", "Al Casting"),
    AlloyPreset("A319", "Al-6Si-3.5Cu", ["AL", "SI", "CU"],
                {"SI": 6.0, "CU": 3.5}, 400, 950,
                "Engine blocks, transmission cases", "Al Casting"),
    AlloyPreset("A413", "Al-12Si (Eutectic)", ["AL", "SI"],
                {"SI": 12.0}, 400, 950,
                "Hydraulic cylinders, high-fluidity castings", "Al Casting"),

    # Aluminum wrought
    AlloyPreset("2024", "Al-4.4Cu-1.5Mg", ["AL", "CU", "MG"],
                {"CU": 4.4, "MG": 1.5}, 300, 950,
                "Aircraft fuselage, wing structures", "Al Wrought"),
    AlloyPreset("6061", "Al-1Mg-0.6Si", ["AL", "MG", "SI"],
                {"MG": 1.0, "SI": 0.6}, 300, 950,
                "Bicycle frames, marine, general structural", "Al Wrought"),
    AlloyPreset("7075", "Al-5.6Zn-2.5Mg-1.6Cu", ["AL", "ZN", "MG", "CU"],
                {"ZN": 5.6, "MG": 2.5, "CU": 1.6}, 300, 950,
                "Aircraft wings, rock climbing gear", "Al Wrought"),
    AlloyPreset("5083", "Al-4.4Mg-0.7Mn", ["AL", "MG", "MN"],
                {"MG": 4.4, "MN": 0.7}, 300, 950,
                "Ship hulls, pressure vessels, cryogenic tanks", "Al Wrought"),

    # Magnesium
    AlloyPreset("AZ91D", "Mg-9Al-0.7Zn", ["MG", "AL", "ZN"],
                {"AL": 9.0, "ZN": 0.7}, 300, 950,
                "Laptop cases, power tool housings, die castings", "Mg"),
    AlloyPreset("AZ31B", "Mg-3Al-1Zn", ["MG", "AL", "ZN"],
                {"AL": 3.0, "ZN": 1.0}, 300, 950,
                "Sheet metal, extrusions, electronics enclosures", "Mg"),
    AlloyPreset("AM60B", "Mg-6Al-0.3Mn", ["MG", "AL", "MN"],
                {"AL": 6.0, "MN": 0.3}, 300, 950,
                "Automotive steering wheels, seat frames", "Mg"),

    # Copper
    AlloyPreset("C26000 Brass", "Cu-30Zn", ["CU", "ZN"],
                {"ZN": 30.0}, 300, 1350,
                "Cartridge cases, radiator fins, lamp fixtures", "Cu"),
    AlloyPreset("C51000 Bronze", "Cu-5Sn", ["CU", "SN"],
                {"SN": 5.0}, 300, 1350,
                "Springs, electrical connectors, bellows", "Cu"),
]


def get_alloy_presets_by_category() -> dict[str, list[AlloyPreset]]:
    """Return alloy presets grouped by category."""
    result: dict[str, list[AlloyPreset]] = {}
    for preset in ALLOY_PRESETS:
        result.setdefault(preset.category, []).append(preset)
    return result


# --- Phase name translations ---

PHASE_NAMES: dict[str, str] = {
    # Generic CALPHAD phase models
    "LIQUID": "Liquid (molten metal)",
    "FCC_A1": "FCC solid solution (e.g. aluminum, copper, austenite)",
    "BCC_A2": "BCC solid solution (e.g. ferrite, chromium, tungsten)",
    "BCC_B2": "BCC ordered (e.g. NiAl intermetallic)",
    "HCP_A3": "HCP solid solution (e.g. magnesium, titanium-alpha, zinc)",
    "HCP_ZN": "HCP zinc-type",
    "DIAMOND_A4": "Diamond cubic (e.g. silicon, germanium)",
    "CBCC_A12": "Complex BCC (e.g. alpha-manganese)",
    "CUB_A13": "Complex cubic (e.g. beta-manganese)",
    "RHOMBO_A7": "Rhombohedral (e.g. antimony, bismuth)",
    "BCT_A5": "Body-centered tetragonal (e.g. beta-tin)",
    "TETRAGONAL": "Tetragonal crystal structure",
    "ORTHORHOMBIC": "Orthorhombic crystal structure",

    # Aluminum intermetallics
    "AL2CU": "Theta phase (Al2Cu) - main strengthening precipitate in 2xxx Al",
    "AL2CU_C16": "Theta phase (Al2Cu) - strengthening precipitate",
    "ALMG_BETA": "Beta phase (Al3Mg2) - forms in 5xxx Al alloys",
    "ALMG_GAMMA": "Gamma phase (Al12Mg17)",
    "AL3MG2": "Beta phase (Al3Mg2) - grain boundary precipitate",
    "AL12MG17": "Gamma phase (Al12Mg17) - eutectic phase in Mg-Al",
    "AL3NI": "Al3Ni - brittle intermetallic",
    "AL3NI2": "Al3Ni2 intermetallic",
    "AL7CU2FE": "Al7Cu2Fe - iron-containing intermetallic (impurity phase)",
    "AL2CULI": "T1 phase - key precipitate in Al-Li alloys",
    "MG2SI": "Mg2Si - strengthening precipitate in 6xxx Al alloys",
    "MGZN2": "Eta phase (MgZn2) - main strengthening precipitate in 7xxx Al",
    "AL3TI": "Al3Ti - grain refiner compound",
    "AL3ZR": "Al3Zr - dispersoid for recrystallization control",
    "AL3SC": "Al3Sc - potent strengthening dispersoid",

    # Iron/Steel phases
    "CEMENTITE": "Cementite (Fe3C) - hard carbide phase in steel",
    "FE3C": "Cementite (Fe3C) - hard carbide phase in steel",
    "GRAPHITE": "Graphite - stable carbon phase (cast iron, not steel)",
    "SIGMA": "Sigma phase - brittle intermetallic (unwanted in stainless steel)",
    "CHI": "Chi phase - intermetallic (unwanted in stainless steel)",
    "LAVES": "Laves phase - intermetallic compound",
    "M23C6": "M23C6 carbide - common in stainless steels",
    "M7C3": "M7C3 carbide - found in high-Cr steels",

    # Titanium
    "TI3AL": "Alpha-2 (Ti3Al) - ordered titanium aluminide",
    "TIAL": "Gamma-TiAl - lightweight high-temp intermetallic",
    "TI2AL": "Ti2Al phase",

    # Magnesium
    "MG17AL12": "Beta phase (Mg17Al12) - main precipitate in AZ Mg alloys",
    "AL12MG17_GAMMA": "Gamma-Mg17Al12",

    # Copper
    "CU5ZN8": "Gamma brass (Cu5Zn8)",
    "CUZN_BCC": "Beta brass (CuZn ordered)",
}


def translate_phase_name(phase: str) -> str:
    """Get human-readable name for a CALPHAD phase, or return original if unknown."""
    return PHASE_NAMES.get(phase.upper(), phase)


def translate_phase_short(phase: str) -> str:
    """Get a short translated name for display in legends/tables."""
    full = PHASE_NAMES.get(phase.upper())
    if full is None:
        return phase
    # Strip example lists "(e.g. ...)" to keep labels compact
    if " (e.g." in full:
        return full.split(" (e.g.")[0]
    # Keep formula parentheticals like "Theta phase (Al2Cu)"
    if "(" in full:
        return full.split(")")[0] + ")"
    return full.split(" - ")[0] if " - " in full else full


# --- Element data for unit conversion ---

ATOMIC_WEIGHTS: dict[str, float] = {
    "AL": 26.982, "MG": 24.305, "SI": 28.086, "CU": 63.546,
    "ZN": 65.38, "FE": 55.845, "C": 12.011, "MN": 54.938,
    "CR": 51.996, "NI": 58.693, "TI": 47.867, "SN": 118.71,
    "ZR": 91.224, "V": 50.942, "CO": 58.933, "MO": 95.95,
    "W": 183.84, "NB": 92.906, "LI": 6.941, "SC": 44.956,
    "AG": 107.868, "PB": 207.2, "BI": 208.98, "SB": 121.76,
    "BE": 9.012, "CA": 40.078, "CE": 140.12, "LA": 138.91,
    "ND": 144.24, "Y": 88.906, "GD": 157.25, "P": 30.974,
    "S": 32.06, "N": 14.007, "O": 15.999, "H": 1.008,
    "B": 10.81, "IN": 114.82, "GA": 69.723, "GE": 72.63,
    "VA": 0.0,  # vacancy
}

# --- Melting points for sanity checks ---

MELTING_POINTS_K: dict[str, float] = {
    "AL": 933.5, "MG": 923.0, "SI": 1687.0, "CU": 1358.0,
    "ZN": 692.7, "FE": 1811.0, "C": 3823.0, "MN": 1519.0,
    "CR": 2180.0, "NI": 1728.0, "TI": 1941.0, "SN": 505.1,
    "ZR": 2128.0, "V": 2183.0, "CO": 1768.0, "MO": 2896.0,
    "W": 3695.0, "NB": 2750.0, "LI": 453.7, "SC": 1814.0,
    "AG": 1234.9, "PB": 600.6, "BI": 544.4, "SB": 903.8,
}


def estimate_temp_range(elements: list[str]) -> tuple[float, float]:
    """Estimate a reasonable temperature range for a set of elements."""
    mps = [MELTING_POINTS_K.get(e.upper(), 1500.0) for e in elements if e.upper() != "VA"]
    if not mps:
        return 300.0, 2000.0
    max_mp = max(mps)
    return 300.0, min(max_mp * 1.15, 5000.0)
