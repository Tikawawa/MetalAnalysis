"""Educational content for CalcPHAD learning mode.

Centralized module containing all educational text: tab explanations,
tooltips, glossary terms, phase descriptions, and fun facts.
"""

# ---------------------------------------------------------------------------
# Centralized tooltips -- import and use across all panels
# ---------------------------------------------------------------------------

TOOLTIPS = {
    # --- Equilibrium panel ---
    "eq_temperature": (
        "Temperature for the equilibrium calculation.\n\n"
        "Reference points:\n"
        "  Room temperature: 298 K (25 C)\n"
        "  Aluminum melts:   933 K (660 C)\n"
        "  Copper melts:    1358 K (1085 C)\n"
        "  Iron/steel melts: ~1811 K (1538 C)\n\n"
        "Higher temperatures favor liquid and disordered phases."
    ),
    "eq_temperature_c": (
        "Temperature in Celsius for the equilibrium calculation.\n\n"
        "Reference points:\n"
        "  Room temperature:  25 C (298 K)\n"
        "  Aluminum melts:   660 C (933 K)\n"
        "  Copper melts:    1085 C (1358 K)\n"
        "  Iron/steel melts: 1538 C (1811 K)\n\n"
        "Higher temperatures favor liquid and disordered phases."
    ),
    "eq_pressure": (
        "Pressure in Pascals.\n\n"
        "101325 Pa = 1 atmosphere -- this is normal air pressure at sea level.\n"
        "Most metallurgical processes happen at 1 atm, so you rarely need to\n"
        "change this unless you are modeling vacuum processing or high-pressure\n"
        "experiments."
    ),
    "eq_calculate": (
        "Click to run the equilibrium calculation.\n\n"
        "The solver will find which phases are stable at your chosen temperature,\n"
        "pressure, and composition, and how much of each phase is present.\n"
        "Results appear in the table and bar chart below."
    ),
    "eq_export_csv": (
        "Save the results as a spreadsheet-friendly CSV file.\n\n"
        "You can open this in Excel, Google Sheets, or any data tool.\n"
        "The file includes your calculation conditions as comment lines\n"
        "at the top so you remember what you calculated."
    ),
    "eq_export_png": (
        "Save the bar chart as a PNG image file.\n\n"
        "Great for reports, presentations, or sharing with colleagues.\n"
        "The image automatically includes your calculation conditions\n"
        "as a subtitle so it is self-documenting."
    ),
    "eq_composition": (
        "How much of this element is in your alloy.\n\n"
        "Think of it like a recipe: if you are making an aluminum-copper alloy\n"
        "and set copper to 0.05 (mole fraction), that means 5 out of every\n"
        "100 atoms are copper and 95 are aluminum.\n\n"
        "In weight percent mode, 5 wt% copper means 5 grams of copper\n"
        "per 100 grams of alloy."
    ),
    "eq_element_combo": (
        "Choose which element to set the amount for.\n\n"
        "The 'base metal' (or 'balance' element) is the one you do NOT\n"
        "list here -- its amount is calculated automatically so everything\n"
        "adds up to 100%. For example, in an Al-Cu alloy you would select\n"
        "CU here and aluminum becomes the balance element."
    ),
    "eq_add_element": (
        "Add another alloying element to your recipe.\n\n"
        "Real-world alloys often contain multiple elements. For example,\n"
        "a 7075 aluminum alloy has zinc, magnesium, copper, and chromium.\n"
        "Each element you add changes the alloy's properties and which\n"
        "phases form."
    ),
    "eq_balance": (
        "This shows the live composition breakdown of your alloy.\n\n"
        "The 'balance' element is the base metal -- it makes up whatever\n"
        "is left over after you specify the other elements. For example,\n"
        "if you set 5% copper in an Al-Cu alloy, the balance shows\n"
        "aluminum at 95%.\n\n"
        "If this line turns red, your total exceeds 100% -- reduce\n"
        "one of the element amounts."
    ),

    # --- Stepping panel ---
    "step_el1": (
        "Primary element -- the base metal of your alloy.\n\n"
        "This is the 'solvent' element that makes up the majority\n"
        "of the alloy. For example, AL for aluminum alloys, FE for\n"
        "steels, or TI for titanium alloys."
    ),
    "step_el2": (
        "The alloying element you are adding to the base metal.\n\n"
        "This is the 'solute' whose composition you set with the\n"
        "spinner to the right. The x-axis of the phase diagram\n"
        "shows the amount of this element."
    ),
    "step_composition": (
        "How much of Element 2 is in your alloy.\n\n"
        "Think of it like a recipe: 0.10 mole fraction means 10 out\n"
        "of every 100 atoms are Element 2, and the remaining 90 are\n"
        "Element 1 (the base metal).\n\n"
        "In weight percent mode, 10 wt% means 10 grams of Element 2\n"
        "per 100 grams of total alloy."
    ),
    "step_t_min": (
        "The lowest temperature in the scan.\n\n"
        "Reference points:\n"
        "  Room temperature: 300 K (27 C)\n"
        "  Liquid nitrogen:   77 K (-196 C)\n\n"
        "300 K is a good default -- it shows what phases exist at\n"
        "room temperature."
    ),
    "step_t_max": (
        "The highest temperature in the scan.\n\n"
        "This should be above the melting point of your alloy so the\n"
        "plot captures the full transition from solid to liquid.\n\n"
        "Reference melting points:\n"
        "  Aluminum:  933 K (660 C)\n"
        "  Copper:   1358 K (1085 C)\n"
        "  Iron:     1811 K (1538 C)"
    ),
    "step_t_step": (
        "Temperature increment between each calculation point.\n\n"
        "Smaller step = smoother, more precise curve, but slower.\n"
        "Larger step  = faster, but may miss narrow phase regions.\n\n"
        "  5 K:  Good balance of speed and detail (default)\n"
        "  1 K:  High precision near phase boundaries\n"
        " 20 K:  Quick overview scan"
    ),
    "step_pressure": (
        "Total pressure in Pascals.\n\n"
        "101325 Pa = 1 atmosphere (standard sea-level air pressure).\n"
        "Most alloy calculations use 1 atm. You would only change this\n"
        "for vacuum heat treatment or high-pressure experiments."
    ),

    # --- Phase diagram panel ---
    "pd_el1": (
        "First element (base metal) of the binary system.\n\n"
        "For an Al-Cu phase diagram, select AL here. The left side\n"
        "of the diagram (X = 0) represents pure Element 1."
    ),
    "pd_el2": (
        "Second element of the binary system.\n\n"
        "For an Al-Cu phase diagram, select CU here. The right side\n"
        "of the diagram (X = 1) represents pure Element 2.\n"
        "The x-axis shows the mole fraction of this element."
    ),
    "pd_t_min": (
        "Lower bound of the temperature range for the diagram.\n\n"
        "A lower value reveals more low-temperature phases.\n"
        "Reference: 300 K (27 C) captures room-temperature phases."
    ),
    "pd_t_max": (
        "Upper bound of the temperature range for the diagram.\n\n"
        "Should be above the liquidus (highest melting point) of the\n"
        "system so the full liquid region is visible.\n"
        "Reference: Al-Cu liquidus is about 1358 K (1085 C)."
    ),
    "pd_calculate": (
        "Run the phase diagram calculation.\n\n"
        "This maps out every phase boundary across the full composition\n"
        "range using pycalphad's binary strategy mapper. It may take\n"
        "30 seconds to a few minutes depending on the system complexity."
    ),
    "pd_export_png": (
        "Save the phase diagram as a PNG image.\n\n"
        "The exported file includes a subtitle with your calculation\n"
        "conditions (elements, temperature range, pressure)."
    ),
    "pd_compare": (
        "Enter compare mode to view two phase diagrams side by side.\n\n"
        "The current diagram is copied to the left panel, and you can\n"
        "run a new calculation for the right panel. This is useful for\n"
        "comparing different element pairs or temperature ranges.\n"
        "Click again to exit compare mode."
    ),
    "pd_canvas": (
        "Interactive phase diagram plot.\n\n"
        "Click anywhere to inspect the composition and temperature\n"
        "at that point. Move the mouse to see live coordinates\n"
        "in the status bar."
    ),

    # --- Scheil panel ---
    "scheil_start_temp": (
        "Temperature at which to begin the Scheil solidification simulation.\n\n"
        "This must be above the liquidus (fully liquid temperature) of your\n"
        "alloy -- otherwise the simulation has nothing to solidify!\n\n"
        "Reference starting points:\n"
        "  Aluminum alloys: 900-1000 K (627-727 C)\n"
        "  Steels:         1600-1800 K (1327-1527 C)\n"
        "  Copper alloys:  1300-1400 K (1027-1127 C)"
    ),
    "scheil_start_temp_c": (
        "Start temperature in Celsius for the Scheil simulation.\n\n"
        "This must be above the liquidus (fully liquid temperature) of your\n"
        "alloy -- otherwise the simulation has nothing to solidify!\n\n"
        "Reference starting points:\n"
        "  Aluminum alloys: 627-727 C\n"
        "  Steels:         1327-1527 C\n"
        "  Copper alloys:  1027-1127 C"
    ),
    "scheil_step_size": (
        "How much the temperature drops between each Scheil step.\n\n"
        "Smaller values give a smoother, more detailed solidification\n"
        "curve but take longer to compute.\n\n"
        "  1 K:   Good default -- detailed and reasonably fast\n"
        "  0.5 K: High resolution near eutectic reactions\n"
        "  5 K:   Quick overview (may miss fine details)"
    ),

    # --- Single-phase panel ---
    "sp_phase_list": (
        "Check the phases you want to compare.\n\n"
        "Common phases you will encounter:\n"
        "  LIQUID    -- the molten metal\n"
        "  FCC_A1    -- face-centered cubic (aluminum, copper, austenite)\n"
        "  BCC_A2    -- body-centered cubic (iron/ferrite, tungsten)\n"
        "  HCP_A3    -- hexagonal close-packed (titanium, magnesium)\n"
        "  CEMENTITE -- iron carbide (Fe3C), found in steels\n\n"
        "Each checked phase produces one curve on the plot. The phase\n"
        "with the lowest Gibbs energy at a given temperature is the\n"
        "most thermodynamically stable."
    ),
}

DID_YOU_KNOW = [
    "Steel is an alloy of iron and carbon, typically containing less than 2 wt% carbon.",
    "The CALPHAD method was pioneered by Larry Kaufman in the 1970s.",
    "A eutectic point is where a liquid transforms directly into two solid phases simultaneously.",
    "Gibbs free energy determines whether a phase transformation is thermodynamically favorable.",
    "The lever rule lets you calculate phase fractions from a phase diagram.",
    "Scheil solidification assumes no diffusion in the solid and perfect mixing in the liquid.",
    "The T-zero temperature is where two phases have equal Gibbs energy at the same composition.",
    "Driving force calculations help predict which phase transformations are most likely to occur.",
    "Most commercial alloys contain 5-15 alloying elements to achieve desired properties.",
    "The solvus line on a phase diagram marks the limit of solid solubility.",
    "Ternary phase diagrams use an equilateral triangle to represent three-component systems.",
    "Thermodynamic databases (TDB files) contain assessed interaction parameters for alloy systems.",
    "The liquidus temperature is the highest temperature at which solid crystals can coexist with the melt.",
    "The solidus temperature is the highest temperature at which a material is completely solid.",
    "Metastable phases can persist for long times if the kinetic barrier to transformation is high.",
    "The Gibbs phase rule: F = C - P + 2, where F is degrees of freedom, C is components, P is phases.",
    "Weight percent and mole fraction are the two most common ways to express alloy composition.",
    "An intermetallic compound has an ordered crystal structure and a fixed or narrow composition range.",
    "The miscibility gap is a region where a single phase separates into two phases of different composition.",
    "Enthalpy of mixing tells you whether alloying elements prefer to mix or segregate.",
]

# ---------------------------------------------------------------------------
# Glossary: term -> {"definition": str, "see_also": list[str]}
# ---------------------------------------------------------------------------

GLOSSARY: dict[str, dict] = {
    "CALPHAD": {
        "definition": (
            "CALculation of PHAse Diagrams. A method for computational thermodynamics "
            "that uses assessed thermodynamic models to predict phase equilibria in "
            "multicomponent systems."
        ),
        "see_also": ["Phase Diagram", "Gibbs Free Energy"],
    },
    "Phase": {
        "definition": (
            "A physically and chemically homogeneous region of a material with a "
            "distinct crystal structure. Examples: liquid, FCC (face-centered cubic), "
            "BCC (body-centered cubic), HCP (hexagonal close-packed)."
        ),
        "see_also": ["Phase Diagram", "Equilibrium"],
    },
    "Phase Diagram": {
        "definition": (
            "A graphical representation showing the stable phases as a function of "
            "temperature, composition, and/or pressure. Binary phase diagrams have "
            "composition on the x-axis and temperature on the y-axis."
        ),
        "see_also": ["Liquidus", "Solidus", "Solvus"],
    },
    "Gibbs Free Energy": {
        "definition": (
            "G = H - TS. The thermodynamic potential that determines phase stability. "
            "At equilibrium, the system minimizes its total Gibbs energy."
        ),
        "see_also": ["Enthalpy", "Entropy", "Equilibrium"],
    },
    "Equilibrium": {
        "definition": (
            "The state where the Gibbs energy of the system is minimized. No net "
            "driving force exists for any phase transformation."
        ),
        "see_also": ["Gibbs Free Energy", "Driving Force"],
    },
    "Liquidus": {
        "definition": (
            "The temperature above which a material is completely liquid. On a phase "
            "diagram, the line separating the liquid region from the two-phase region."
        ),
        "see_also": ["Solidus", "Phase Diagram"],
    },
    "Solidus": {
        "definition": (
            "The temperature below which a material is completely solid. On a phase "
            "diagram, the line separating the solid region from the two-phase region."
        ),
        "see_also": ["Liquidus", "Phase Diagram"],
    },
    "Eutectic": {
        "definition": (
            "A reaction where a liquid phase transforms into two (or more) solid phases "
            "simultaneously at a fixed temperature and composition. The eutectic "
            "temperature is the lowest melting point in the system."
        ),
        "see_also": ["Phase Diagram", "Liquidus"],
    },
    "Solvus": {
        "definition": (
            "The phase boundary that separates a single solid phase region from a "
            "two-phase solid region. Indicates the limit of solid solubility."
        ),
        "see_also": ["Phase Diagram", "Miscibility Gap"],
    },
    "Scheil Solidification": {
        "definition": (
            "A solidification model assuming perfect mixing in the liquid and no "
            "diffusion in the solid. Predicts microsegregation during casting and "
            "is widely used in foundry applications."
        ),
        "see_also": ["Liquidus", "Solidus"],
    },
    "TDB File": {
        "definition": (
            "Thermodynamic DataBase file. A text file containing assessed thermodynamic "
            "parameters (Gibbs energy models) for an alloy system. The standard "
            "exchange format for CALPHAD data."
        ),
        "see_also": ["CALPHAD"],
    },
    "Mole Fraction": {
        "definition": (
            "The ratio of moles of a component to total moles in the system. "
            "Dimensionless, ranges from 0 to 1. Preferred in thermodynamic calculations."
        ),
        "see_also": ["Weight Percent"],
    },
    "Weight Percent": {
        "definition": (
            "The mass of a component divided by the total mass, multiplied by 100. "
            "Common in industrial alloy specifications and standards."
        ),
        "see_also": ["Mole Fraction"],
    },
    "Driving Force": {
        "definition": (
            "The Gibbs energy difference that provides the thermodynamic incentive "
            "for a phase transformation to occur. Larger driving forces lead to "
            "faster transformation kinetics."
        ),
        "see_also": ["Gibbs Free Energy", "Equilibrium"],
    },
    "T-Zero (T0)": {
        "definition": (
            "The temperature at which two phases have equal Gibbs energy at the same "
            "composition. Important for diffusionless (martensitic) transformations."
        ),
        "see_also": ["Gibbs Free Energy", "Driving Force"],
    },
    "Enthalpy": {
        "definition": (
            "H = U + PV. A thermodynamic quantity representing the total heat content "
            "of a system at constant pressure. Enthalpy of mixing indicates whether "
            "alloying is exothermic or endothermic."
        ),
        "see_also": ["Gibbs Free Energy", "Entropy"],
    },
    "Entropy": {
        "definition": (
            "A measure of the disorder or randomness in a system. Higher entropy "
            "favors disordered phases (e.g., liquid, solid solution) at high temperatures."
        ),
        "see_also": ["Gibbs Free Energy", "Enthalpy"],
    },
    "Miscibility Gap": {
        "definition": (
            "A composition-temperature region where a single phase is unstable and "
            "separates (unmixes) into two phases of different compositions."
        ),
        "see_also": ["Solvus", "Phase Diagram"],
    },
    "Intermetallic": {
        "definition": (
            "A compound formed between two or more metals with an ordered crystal "
            "structure and a specific (or narrow range of) stoichiometry. Often "
            "hard and brittle."
        ),
        "see_also": ["Phase"],
    },
    "Lever Rule": {
        "definition": (
            "A method to calculate the fraction of each phase present in a two-phase "
            "region using the tie-line on a phase diagram."
        ),
        "see_also": ["Phase Diagram", "Equilibrium"],
    },
}


# ---------------------------------------------------------------------------
# Phase explanations: phase_short_name -> educational details
# ---------------------------------------------------------------------------

PHASE_EXPLANATIONS: dict[str, dict] = {
    "FCC_A1": {
        "name": "FCC_A1 (Face-Centered Cubic)",
        "crystal": "Face-Centered Cubic (cF4, Fm-3m)",
        "description": (
            "Atoms sit at the corners and face centers of a cube. "
            "This structure is ductile and close-packed, allowing easy dislocation motion."
        ),
        "found_in": "Aluminum, Copper, Nickel, Austenitic steels (gamma-iron)",
        "significance": (
            "FCC metals are generally ductile and tough. Austenite in steel "
            "is FCC and is the basis for stainless steels and quench hardening."
        ),
    },
    "BCC_A2": {
        "name": "BCC_A2 (Body-Centered Cubic)",
        "crystal": "Body-Centered Cubic (cI2, Im-3m)",
        "description": (
            "Atoms at cube corners with one atom in the center. "
            "Less close-packed than FCC, which affects slip behavior."
        ),
        "found_in": "Iron (ferrite), Chromium, Tungsten, Molybdenum",
        "significance": (
            "Ferrite in steel is BCC. BCC metals are strong but can be brittle "
            "at low temperatures (ductile-to-brittle transition)."
        ),
    },
    "HCP_A3": {
        "name": "HCP_A3 (Hexagonal Close-Packed)",
        "crystal": "Hexagonal Close-Packed (hP2, P6_3/mmc)",
        "description": (
            "Close-packed layers stacked in an ABAB pattern. "
            "Limited slip systems make HCP metals less ductile."
        ),
        "found_in": "Titanium (alpha), Magnesium, Zinc, Zirconium",
        "significance": (
            "Alpha-titanium and magnesium alloys are HCP. Understanding "
            "the HCP-to-BCC transition is key for Ti alloy design."
        ),
    },
    "LIQUID": {
        "name": "Liquid",
        "crystal": "No long-range order (amorphous)",
        "description": (
            "The molten state where atoms have no fixed positions. "
            "All alloys pass through this phase during casting."
        ),
        "found_in": "All metals above their melting point",
        "significance": (
            "The liquid phase is the starting point for most metal processing. "
            "Its composition determines what solid phases form on cooling."
        ),
    },
    "BCC_B2": {
        "name": "BCC_B2 (Ordered BCC)",
        "crystal": "Ordered Body-Centered Cubic (cP2, Pm-3m)",
        "description": (
            "An ordered variant of BCC where two atom types alternate "
            "on the lattice sites, forming a CsCl-type structure."
        ),
        "found_in": "NiAl, FeAl, CuZn (beta-brass)",
        "significance": (
            "B2 ordering can dramatically change mechanical properties, "
            "often increasing strength but reducing ductility."
        ),
    },
    "DIAMOND_A4": {
        "name": "Diamond Cubic (A4)",
        "crystal": "Diamond Cubic (cF8, Fd-3m)",
        "description": (
            "Each atom is tetrahedrally bonded to four neighbors. "
            "This is the structure of silicon and germanium."
        ),
        "found_in": "Silicon, Germanium, Carbon (diamond)",
        "significance": (
            "Silicon in Al-Si alloys precipitates in this structure. "
            "It is very hard but brittle."
        ),
    },
    "AL3FE": {
        "name": "Al3Fe (Iron Aluminide)",
        "crystal": "Monoclinic",
        "description": "An intermetallic compound of aluminum and iron.",
        "found_in": "Al-Fe alloys and recycled aluminum with iron impurities",
        "significance": (
            "Generally undesirable -- forms brittle needles that reduce "
            "ductility in aluminum castings."
        ),
    },
    "AL2CU": {
        "name": "Al2Cu (Theta phase)",
        "crystal": "Tetragonal (tI12, I4/mcm)",
        "description": (
            "The theta phase that forms during age hardening of "
            "Al-Cu alloys. Precursor GP zones provide peak hardness."
        ),
        "found_in": "2xxx series aluminum alloys (e.g., 2024, 2014)",
        "significance": (
            "This is THE classic precipitation-hardening phase. "
            "Its formation sequence (GP zones -> theta'' -> theta' -> theta) "
            "is taught in every metallurgy course."
        ),
    },
    "MG2SI": {
        "name": "Mg2Si (Magnesium Silicide)",
        "crystal": "Cubic (cF12, Fm-3m, antifluorite)",
        "description": (
            "A strengthening precipitate in Al-Mg-Si (6xxx) alloys. "
            "Forms during artificial aging (T6 temper)."
        ),
        "found_in": "6xxx series aluminum alloys (e.g., 6061, 6063)",
        "significance": (
            "The primary hardening phase in the most widely used "
            "aluminum extrusion alloys."
        ),
    },
    "CEMENTITE": {
        "name": "Cementite (Fe3C)",
        "crystal": "Orthorhombic (oP16, Pnma)",
        "description": (
            "Iron carbide -- the hard, brittle phase in steel. "
            "Forms lamellar pearlite with ferrite."
        ),
        "found_in": "Carbon steels, cast irons",
        "significance": (
            "Controls the hardness and wear resistance of steel. "
            "Pearlite (ferrite + cementite) is the backbone of structural steel."
        ),
    },
}


# ---------------------------------------------------------------------------
# Tab info: explanations for the "What Is This?" panel on each tab
# ---------------------------------------------------------------------------

TAB_INFO: dict[str, dict] = {
    "database": {
        "title": "Database Loader",
        "simple": "A thermodynamic database contains all the scientific data about how elements interact. Think of it as a cookbook that knows every recipe for mixing metals.",
        "analogy": "Loading a database is like opening a cookbook before cooking -- without it, the app has no recipes.",
        "tips": ["Start with the bundled COST507 database -- it covers 27 common elements.", "TDB files are the standard format. DAT (ChemSage) files also work.", "Try a preset alloy for sensible default settings."],
    },
    "phase_diagram": {
        "title": "Phase Diagram",
        "simple": "A phase diagram is a map showing which crystal structures exist at every temperature and composition. Each region represents a different atomic arrangement.",
        "analogy": "Like a weather map -- instead of rain/snow/sun zones, it shows liquid/solid/mixed zones for your alloy.",
        "tips": ["Start with Al-Cu or Fe-C (simple, well-known systems).", "X-axis = composition, Y-axis = temperature.", "Boundary lines show where the metal transforms.", "The eutectic point is the lowest melting temperature."],
    },
    "equilibrium": {
        "title": "Equilibrium Calculator",
        "simple": "This calculates what your alloy looks like if held at a specific temperature long enough. It answers: what phases exist, and how much of each?",
        "analogy": "Like asking: 'If I leave this metal at 500C forever, what would it become?'",
        "tips": ["Try different temperatures to see how phases change.", "The balance element is the base metal (e.g., aluminum).", "Phase fraction of 1.0 = 100% of that phase."],
    },
    "stepping": {
        "title": "Melting Simulator",
        "simple": "Shows how your alloy changes as temperature increases. See phases appear and disappear, find when melting begins (solidus) and ends (liquidus).",
        "analogy": "Like slowly heating an ice cube: fully solid, then slushy, then fully liquid. Metals do the same with crystal structures.",
        "tips": ["Solidus = melting BEGINS.", "Liquidus = FULLY liquid.", "The mushy zone between them is partially solid, partially liquid.", "Try composition sweep to see how adding more element changes things."],
    },
    "ternary": {
        "title": "Ternary Phase Diagram",
        "simple": "Shows phase stability for three-element systems using a triangle. Each corner = 100% of one element. Points inside are mixtures.",
        "analogy": "Like a color-mixing triangle where each corner is a pure color.",
        "tips": ["Advanced feature -- start with binary diagrams first!", "Isothermal sections show a snapshot at one temperature.", "Isopleths are vertical slices through the ternary space."],
    },
    "scheil": {
        "title": "Casting Simulator (Scheil)",
        "simple": "Real casting doesn't wait for equilibrium. Metal cools too fast. Scheil predicts what ACTUALLY happens: which phases form, in what order, and how much eutectic remains.",
        "analogy": "Like freezing a lake from top down -- ice locks in its composition, and remaining water gets progressively different.",
        "tips": ["Fraction solid curve shows solidification progress.", "Eutectic fraction = how much liquid solidifies all at once at the end.", "Compare to equilibrium stepping -- the difference shows why casting matters."],
    },
    "thermo_props": {
        "title": "Thermodynamic Properties",
        "simple": "Calculates fundamental energy quantities: Gibbs energy (stability), enthalpy (heat), entropy (disorder), heat capacity, and chemical potentials.",
        "analogy": "Gibbs energy is a comfort score -- atoms rearrange to minimize it, like a ball rolling downhill.",
        "tips": ["G determines which phases are stable -- lower G wins.", "Cp shows sharp peaks at phase transformations.", "H relates to heat released during transformations."],
    },
    "single_phase": {
        "title": "Single-Phase Calculator",
        "simple": "Evaluates energy of individual crystal structures. Compare G-curves to understand WHY one phase wins over another at each temperature.",
        "analogy": "Like comparing comfort levels of chairs -- the one with lowest discomfort score (Gibbs energy) is chosen by atoms.",
        "tips": ["Use 'Select Common' for important phases.", "Where G-curves cross = phase boundary.", "Lowest G at each temperature = stable phase."],
    },
    "driving_force": {
        "title": "Driving Force Analysis",
        "simple": "Shows how close non-stable phases are to forming. Small driving force = almost stable, might appear during processing.",
        "analogy": "Like checking how close a ball is to rolling over a hill into the next valley.",
        "tips": ["Red (< 500 J/mol) = dangerously close.", "Green (> 2000 J/mol) = safely far.", "Use sweep mode to see how it changes with temperature."],
    },
    "t_zero": {
        "title": "T-Zero Calculator",
        "simple": "T0 is where two crystal structures have exactly equal energy. The limit for diffusionless (martensitic) transformations.",
        "analogy": "The tie-breaking temperature where two competitors are exactly matched.",
        "tips": ["Most useful for steel: compare FCC_A1 (austenite) vs BCC_A2 (ferrite).", "T0 line shows where diffusionless transformation is possible."],
    },
    "volume": {
        "title": "Molar Volume & Density",
        "simple": "Calculates how much space atoms take up and alloy density. Important for casting shrinkage and weight estimation.",
        "analogy": "Like comparing how tightly different ball arrangements pack. FCC and HCP pack efficiently (dense), BCC is slightly less dense.",
        "tips": ["Requires V0/VA parameters in the database.", "Density changes during solidification cause casting shrinkage.", "If no volume data, shows phase fractions instead."],
    },
}


# ---------------------------------------------------------------------------
# Learning mode configuration
# ---------------------------------------------------------------------------

LEARNING_MODE_CONFIG: dict = {
    "visible_tabs": ["Database", "Phase Diagram", "Equilibrium", "Stepping", "Scheil",
                     "Alloy Analyzer", "Melting Sim", "Casting Sim"],
    "hidden_tabs": ["Thermo Props", "Phase Calc", "Driving Force", "T-Zero", "Volume"],
    "renamed_tabs": {"Stepping": "Melting Sim", "Scheil": "Casting Sim", "Equilibrium": "Alloy Analyzer"},
    "original_tabs": {"Melting Sim": "Stepping", "Casting Sim": "Scheil", "Alloy Analyzer": "Equilibrium"},
}
