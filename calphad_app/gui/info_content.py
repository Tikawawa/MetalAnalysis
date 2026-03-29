"""Centralized educational content for the CALPHAD teaching application.

This module is the **single source of truth** for all educational text,
tooltips, glossary terms, "Did You Know?" facts, tab explanations, phase
descriptions, result templates, and learning-mode configuration.

The target audience is NOT a metallurgist.  Every explanation should be
approachable, use analogies, and build understanding from first principles.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# 1. TAB_INFO -- explanations shown in "What Is This?" panels for each tab
# ---------------------------------------------------------------------------

TAB_INFO: dict[str, dict[str, Any]] = {
    "database": {
        "title": "Database Explorer",
        "simple": (
            "A thermodynamic database is a digital encyclopedia of how "
            "elements and phases behave. It contains carefully measured "
            "and modeled data about the energy of every possible "
            "arrangement of atoms. Without a database loaded, no "
            "calculations can run."
        ),
        "analogy": (
            "Think of the database like a cookbook. The cookbook itself "
            "does not make any food -- it just holds all the recipes. "
            "Each recipe describes how ingredients (elements) combine "
            "and what happens at different temperatures. You need to "
            "open the cookbook before you can start cooking."
        ),
        "learn": [
            "Which elements are available in your database",
            "Which phases (crystal structures) the database knows about",
            "What alloy systems have been modeled",
            "The difference between common database formats (TDB, PDB)",
        ],
        "tips": [
            "Start by loading one of the built-in example databases.",
            "The database file extension is usually .TDB or .tdb.",
            "Larger databases cover more element combinations but take "
            "longer to load.",
            "If a calculation gives strange results, the database may "
            "not cover that composition range well.",
        ],
    },
    "phase_diagram": {
        "title": "Phase Diagram",
        "simple": (
            "A phase diagram is a map that shows which crystal structures "
            "exist inside a metal at every combination of temperature and "
            "composition. It tells you what happens as you heat, cool, or "
            "change the mix of elements in an alloy."
        ),
        "analogy": (
            "Think of it like a weather map, but for metals. A weather "
            "map shows where it is rainy, snowy, or sunny depending on "
            "location and time of year. A phase diagram shows where the "
            "metal is liquid, a specific crystal, or a mixture -- "
            "depending on temperature and how much of each element is "
            "present."
        ),
        "learn": [
            "Which crystal structures exist at different temperatures",
            "At what temperature the alloy starts to melt (solidus)",
            "At what temperature it is fully liquid (liquidus)",
            "Where special reactions occur (eutectics, peritectics)",
            "How changing composition affects which phases are stable",
        ],
        "tips": [
            "Start with a simple binary system like Al-Cu or Fe-C.",
            "The x-axis is composition (how much of the second element).",
            "The y-axis is temperature.",
            "Regions on the map represent stable phase combinations.",
            "Lines between regions are phase boundaries -- important "
            "temperatures where transformations occur.",
        ],
    },
    "equilibrium": {
        "title": "Equilibrium Calculator (Alloy Analyzer)",
        "simple": (
            "An equilibrium calculation answers the question: 'If I hold "
            "this alloy at this exact temperature for a very long time, "
            "what phases will form and how much of each?' It finds the "
            "most stable arrangement of atoms -- the lowest-energy state."
        ),
        "analogy": (
            "Imagine dropping a ball into a hilly landscape. It will "
            "eventually roll to the lowest valley and stop. That valley "
            "is the equilibrium state. The equilibrium calculator finds "
            "that lowest-energy valley for the atoms in your alloy."
        ),
        "learn": [
            "What phases are stable at a specific temperature and composition",
            "How much of each phase is present (phase fractions)",
            "The composition of each phase (what elements are in each crystal)",
            "Whether the alloy is fully solid, fully liquid, or in between",
        ],
        "tips": [
            "Try calculating at room temperature (298 K) first, then at "
            "high temperature to see the difference.",
            "If the result shows 100% LIQUID, you are above the melting "
            "point.",
            "If you see multiple solid phases, the alloy contains "
            "different crystal structures living side by side.",
            "Compare results at different temperatures to understand how "
            "the alloy changes as it heats or cools.",
        ],
    },
    "stepping": {
        "title": "Stepping Calculator (Melting Simulator)",
        "simple": (
            "The stepping calculator performs many equilibrium "
            "calculations in a row, stepping through a range of "
            "temperatures (or compositions). This builds a complete "
            "picture of how the alloy evolves as conditions change. "
            "It is like watching a time-lapse of an alloy heating up "
            "or cooling down."
        ),
        "analogy": (
            "If a single equilibrium calculation is like taking one "
            "photograph, stepping is like recording a video. You see "
            "the entire story: which phases appear, grow, shrink, and "
            "disappear as the temperature changes."
        ),
        "learn": [
            "How phase fractions change with temperature",
            "At what temperature each phase appears or disappears",
            "The melting range (solidus to liquidus) of your alloy",
            "How composition within each phase shifts during heating/cooling",
        ],
        "tips": [
            "A temperature step of 5 K is a good starting point.",
            "Make sure your temperature range spans from below solidus "
            "to above liquidus for a complete melting picture.",
            "The plot will show phase fraction vs. temperature -- watch "
            "for sudden jumps that indicate phase transformations.",
            "Smaller steps give smoother curves but take longer.",
        ],
    },
    "ternary": {
        "title": "Ternary Phase Diagram",
        "simple": (
            "A ternary phase diagram is like a regular phase diagram "
            "but for three elements instead of two. Because you need "
            "three axes for three compositions, the diagram uses a "
            "triangle where each corner represents a pure element."
        ),
        "analogy": (
            "Picture a triangular table where each corner is a "
            "different flavor of ice cream. As you move toward a "
            "corner, you get more of that flavor. In the middle, you "
            "have equal parts of all three. A ternary phase diagram "
            "does the same thing with elements and shows which crystal "
            "structures form at each mix."
        ),
        "learn": [
            "How three elements interact together",
            "Which phases are stable in three-component alloys",
            "How to read a triangular composition diagram",
            "Where important three-element reactions occur",
        ],
        "tips": [
            "The three corners of the triangle are the pure elements.",
            "The sides of the triangle are the binary (two-element) "
            "systems.",
            "Reading composition: pick a point, then draw lines "
            "parallel to each side to find the amount of each element.",
            "Start by understanding the three binary edges before "
            "diving into the interior of the triangle.",
        ],
    },
    "scheil": {
        "title": "Scheil Solidification (Casting Simulator)",
        "simple": (
            "The Scheil simulation predicts what actually happens when "
            "liquid metal freezes during casting. Unlike equilibrium "
            "(which assumes infinite time), Scheil assumes that atoms "
            "in the solid cannot move -- only the liquid can change "
            "composition. This is closer to real-world casting, where "
            "cooling happens fast."
        ),
        "analogy": (
            "Imagine freezing a pot of salty water. The first ice "
            "crystals that form are nearly pure water, pushing salt "
            "into the remaining liquid. As more ice forms, the liquid "
            "gets saltier and saltier, and it freezes at a lower "
            "temperature. Scheil simulates this exact process for metals."
        ),
        "learn": [
            "The solidification path of your alloy during casting",
            "How much liquid remains at each temperature during freezing",
            "Whether a eutectic reaction occurs at the end of solidification",
            "How segregation (uneven composition) develops in the solid",
            "The actual freezing range vs. the equilibrium freezing range",
        ],
        "tips": [
            "Set the start temperature above the liquidus line.",
            "A step size of 1 K gives good resolution.",
            "Watch for the last bit of liquid -- if it reaches a "
            "eutectic, you will see a flat region at the end.",
            "Compare Scheil results with equilibrium stepping to see "
            "how much non-equilibrium effects matter for your alloy.",
        ],
    },
    "thermo_props": {
        "title": "Thermodynamic Properties",
        "simple": (
            "This tab lets you plot fundamental thermodynamic "
            "properties like Gibbs energy, enthalpy, entropy, and "
            "heat capacity as a function of temperature or "
            "composition. These are the numbers that drive all phase "
            "transformations."
        ),
        "analogy": (
            "If the phase diagram is a map, thermodynamic properties "
            "are the terrain data that defines the hills and valleys. "
            "Gibbs energy is the 'height' -- phases always want to "
            "roll downhill to the lowest energy. This tab lets you "
            "see the actual landscape."
        ),
        "learn": [
            "How Gibbs energy of different phases compares",
            "Where phase transformations occur (energy curve crossings)",
            "The heat capacity of your alloy (important for heating/cooling)",
            "Enthalpy changes during melting (latent heat)",
        ],
        "tips": [
            "Gibbs energy vs. composition plots show which phase "
            "'wins' at each composition -- the lowest curve is stable.",
            "Heat capacity peaks often indicate phase transformations.",
            "Enthalpy jumps at melting tell you how much energy is "
            "needed to melt the alloy.",
            "This is an advanced tab -- start with Phase Diagram and "
            "Equilibrium first.",
        ],
    },
    "single_phase": {
        "title": "Single-Phase Properties",
        "simple": (
            "This tab examines one specific phase in detail -- its "
            "composition, energy, and properties -- even at conditions "
            "where it is not the most stable phase. This is useful for "
            "understanding metastable states."
        ),
        "analogy": (
            "Imagine examining one contestant on a cooking show in "
            "detail, even if they did not win the round. You can learn "
            "a lot about their recipe (energy, composition) regardless "
            "of whether the judges picked them as the winner."
        ),
        "learn": [
            "The properties of a specific crystal structure at any condition",
            "How a phase's composition changes with temperature",
            "The energy of metastable (not-quite-stable) phases",
            "Site fractions and sublattice occupancies",
        ],
        "tips": [
            "Select the phase you want to examine from the dropdown.",
            "This is useful when you want to understand why a phase is "
            "or is not stable at certain conditions.",
            "Compare the Gibbs energy of different phases to see which "
            "one wins at a given temperature.",
        ],
    },
    "driving_force": {
        "title": "Driving Force",
        "simple": (
            "Driving force measures how strongly nature 'wants' to "
            "form a particular phase. A large driving force means the "
            "phase is very eager to appear. A zero driving force means "
            "it is already stable. A negative driving force means it "
            "wants to dissolve."
        ),
        "analogy": (
            "Think of a ball sitting on a slope. The steepness of the "
            "slope is the driving force. A ball on a steep slope will "
            "roll quickly (high driving force for change). A ball in a "
            "flat valley has zero driving force -- it is already where "
            "it wants to be."
        ),
        "learn": [
            "Which phases are close to forming but have not yet appeared",
            "How much energy would be released if a phase did form",
            "Which phases are the most thermodynamically 'eager' to appear",
            "The relative stability of competing phases",
        ],
        "tips": [
            "Driving force is reported in J/mol -- larger values mean "
            "a stronger push to form.",
            "Phases with small positive driving force are 'almost "
            "stable' and might form during processing.",
            "This is critical for predicting unwanted precipitates.",
            "Use this to understand which impurity phases might cause "
            "problems during heat treatment.",
        ],
    },
    "t_zero": {
        "title": "T-Zero (T0) Temperature",
        "simple": (
            "The T-zero temperature is where two crystal structures "
            "have exactly the same Gibbs energy at the same "
            "composition. Below T0, one phase is more stable; above "
            "T0, the other wins. This is important for understanding "
            "diffusionless transformations."
        ),
        "analogy": (
            "Imagine two runners on a see-saw. At the T0 temperature, "
            "the see-saw is perfectly balanced. Tip the temperature one "
            "way and runner A is higher (less stable); tip it the other "
            "way and runner B is higher. The balance point is T0."
        ),
        "learn": [
            "The temperature where two phases have equal energy",
            "The maximum composition for diffusionless transformations",
            "The theoretical limit for martensite formation in steels",
            "How alloying elements shift the T0 temperature",
        ],
        "tips": [
            "For steels, compare FCC_A1 (austenite) with BCC_A2 (ferrite).",
            "The T0 line sets the composition limit for massive and "
            "martensitic transformations.",
            "This is an advanced concept -- make sure you understand "
            "equilibrium phase diagrams first.",
            "T0 is always between the phase boundaries of the two phases.",
        ],
    },
    "volume": {
        "title": "Molar Volume and Density",
        "simple": (
            "This tab calculates how much space the atoms in your "
            "alloy occupy (molar volume) and how heavy a given volume "
            "of the alloy is (density). These properties matter for "
            "designing real parts with specific weight and size "
            "requirements."
        ),
        "analogy": (
            "If you have a bag of oranges vs. a bag of grapes, even "
            "if the bag is the same size, one weighs more. That is "
            "density. Molar volume is like asking how big a box you "
            "need to hold a specific number of atoms."
        ),
        "learn": [
            "The density of your alloy at different temperatures",
            "How density changes as the alloy melts or transforms",
            "The volume change during solidification (important for casting)",
            "How alloying additions affect weight",
        ],
        "tips": [
            "Density is reported in kg/m3 or g/cm3.",
            "Most metals expand when they melt (volume increases, "
            "density decreases).",
            "Volume changes during solidification can cause shrinkage "
            "porosity in castings.",
            "Aluminum alloys: ~2.7 g/cm3. Steels: ~7.8 g/cm3.",
        ],
    },
}


# ---------------------------------------------------------------------------
# 2. TOOLTIPS -- rich educational tooltips for all interactive widgets
# ---------------------------------------------------------------------------

TOOLTIPS: dict[str, str] = {
    # ===== General / shared controls =====
    "temperature": (
        "The temperature of the metal in Kelvin.\n\n"
        "For reference:\n"
        "- Room temp: 298 K (25 C)\n"
        "- Boiling water: 373 K (100 C)\n"
        "- Aluminum melts: 933 K (660 C)\n"
        "- Iron melts: 1811 K (1538 C)\n"
        "- Steel melts: ~1800 K (~1527 C)\n\n"
        "Higher temperature = more energy = atoms move more freely."
    ),
    "composition_mole": (
        "How much of this element is in the alloy, as a fraction of "
        "all atoms.\n\n"
        "Think of it like a recipe:\n"
        "- 0.10 means 10% of the atoms are this element\n"
        "- 0.01 means 1% (a trace amount)\n"
        "- The rest is the base metal (balance element)\n\n"
        "Mole fraction counts atoms. Weight percent counts mass."
    ),
    "composition_weight": (
        "How much of this element is in the alloy, by weight.\n\n"
        "Think of it like a recipe:\n"
        "- 5.0 wt% means 5 grams of this element per 100 grams of alloy\n"
        "- The rest is the base metal\n\n"
        "Weight percent is what you would measure on a scale."
    ),
    "pressure": (
        "Pressure in Pascals. 101,325 Pa = 1 atmosphere = normal air "
        "pressure.\n\n"
        "Most metallurgy happens at 1 atm. Only change this for:\n"
        "- High-pressure research\n"
        "- Vacuum processing\n"
        "- Deep-earth geology"
    ),
    "calculate_btn": (
        "Run the calculation!\n\n"
        "The computer will solve complex thermodynamic equations to "
        "find the most stable arrangement of atoms at your conditions. "
        "This may take a few seconds."
    ),
    "export_csv": (
        "Save the data as a spreadsheet file (.csv).\n\n"
        "You can open this in Excel, Google Sheets, or any data "
        "analysis tool."
    ),
    "export_png": (
        "Save the chart as an image file (.png).\n\n"
        "Great for reports, presentations, or comparing results later."
    ),

    # ===== Element selection =====
    "element_combo": (
        "Choose a chemical element.\n\n"
        "The base metal goes in Element 1 (e.g., AL for aluminum alloys).\n"
        "The alloying element goes in Element 2 (e.g., CU for copper).\n\n"
        "Together they define the alloy system you are studying."
    ),
    "element_1": (
        "The base element (solvent) of your alloy.\n\n"
        "This is the main ingredient -- the element present in the "
        "largest amount. For example:\n"
        "- AL for aluminum alloys\n"
        "- FE for steels and cast irons\n"
        "- CU for copper alloys (brass, bronze)\n"
        "- TI for titanium alloys"
    ),
    "element_2": (
        "The alloying element (solute).\n\n"
        "This is the element added to the base metal to change its "
        "properties. For example:\n"
        "- CU added to AL makes age-hardenable aluminum alloys\n"
        "- C added to FE makes steel\n"
        "- ZN added to CU makes brass"
    ),
    "element_3": (
        "The third element in a ternary (three-component) system.\n\n"
        "Adding a third element opens up a much richer space of "
        "possible phases and compositions. The diagram becomes a "
        "triangle instead of a line."
    ),

    # ===== Temperature range =====
    "t_min": (
        "The lowest temperature to calculate.\n\n"
        "A good starting point is room temperature (298 K / 25 C).\n"
        "Go lower if you need to study cold-weather behavior."
    ),
    "t_max": (
        "The highest temperature to calculate.\n\n"
        "Should be above the melting point of your alloy.\n"
        "For aluminum alloys: ~1000 K. For steels: ~2000 K."
    ),
    "t_step": (
        "The temperature gap between each calculation point.\n\n"
        "Smaller step = more precise but slower:\n"
        "- 1 K: Very precise (slow)\n"
        "- 5 K: Good balance\n"
        "- 20 K: Quick overview"
    ),

    # ===== Composition range =====
    "x_min": (
        "The lowest composition to calculate.\n\n"
        "Usually 0 (pure base metal). Set higher if you only care "
        "about a specific composition range."
    ),
    "x_max": (
        "The highest composition to calculate.\n\n"
        "Usually 1.0 for mole fraction or 100 for weight percent. "
        "But often the interesting region is at lower values (e.g., "
        "0 to 0.5 for most practical alloys)."
    ),
    "x_step": (
        "The composition gap between each calculation point.\n\n"
        "Smaller step = smoother diagram but slower:\n"
        "- 0.005: Very fine (slow)\n"
        "- 0.01: Good default\n"
        "- 0.05: Quick preview"
    ),

    # ===== Phase selection =====
    "phase_selection": (
        "Choose which crystal structures to analyze.\n\n"
        "Common phases:\n"
        "- LIQUID: Molten metal\n"
        "- FCC_A1: Face-centered cubic (aluminum, copper, gold)\n"
        "- BCC_A2: Body-centered cubic (iron at room temp, steel)\n"
        "- HCP_A3: Hexagonal close-packed (titanium, magnesium)\n\n"
        "Tip: Start with 'Select Common' to pick the most important ones."
    ),
    "select_all_phases": (
        "Select every phase in the database.\n\n"
        "This can make calculations slower but ensures you do not "
        "miss anything. Good for a first exploration."
    ),
    "select_common_phases": (
        "Select only the most commonly encountered phases.\n\n"
        "This speeds up calculations and keeps the results easier to "
        "read. Use this as your default starting point."
    ),
    "deselect_all_phases": (
        "Clear all phase selections.\n\n"
        "Useful when you want to hand-pick exactly which phases to "
        "include."
    ),

    # ===== Equilibrium panel =====
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
        "101325 Pa = 1 atmosphere -- this is normal air pressure at "
        "sea level.\n"
        "Most metallurgical processes happen at 1 atm, so you rarely "
        "need to change this unless you are modeling vacuum processing "
        "or high-pressure experiments."
    ),
    "eq_calculate": (
        "Click to run the equilibrium calculation.\n\n"
        "The solver will find which phases are stable at your chosen "
        "temperature, pressure, and composition, and how much of each "
        "phase is present.\n"
        "Results appear in the table and bar chart below."
    ),
    "eq_export_csv": (
        "Save the results as a spreadsheet-friendly CSV file.\n\n"
        "You can open this in Excel, Google Sheets, or any data tool.\n"
        "The file includes your calculation conditions as comment "
        "lines at the top so you remember what you calculated."
    ),
    "eq_export_png": (
        "Save the bar chart as a PNG image file.\n\n"
        "Great for reports, presentations, or sharing with colleagues.\n"
        "The image automatically includes your calculation conditions "
        "as a subtitle so it is self-documenting."
    ),
    "eq_composition": (
        "How much of this element is in your alloy.\n\n"
        "Think of it like a recipe: if you are making an aluminum-"
        "copper alloy and set copper to 0.05 (mole fraction), that "
        "means 5 out of every 100 atoms are copper and 95 are "
        "aluminum.\n\n"
        "In weight percent mode, 5 wt% copper means 5 grams of "
        "copper per 100 grams of alloy."
    ),
    "eq_element_combo": (
        "Choose which element to set the amount for.\n\n"
        "The 'base metal' (or 'balance' element) is the one you do "
        "NOT list here -- its amount is calculated automatically so "
        "everything adds up to 100%. For example, in an Al-Cu alloy "
        "you would select CU here and aluminum becomes the balance "
        "element."
    ),
    "eq_add_element": (
        "Add another alloying element to your recipe.\n\n"
        "Real-world alloys often contain multiple elements. For "
        "example, a 7075 aluminum alloy has zinc, magnesium, copper, "
        "and chromium. Each element you add changes the alloy's "
        "properties and which phases form."
    ),
    "eq_balance": (
        "This shows the live composition breakdown of your alloy.\n\n"
        "The 'balance' element is the base metal -- it makes up "
        "whatever is left over after you specify the other elements. "
        "For example, if you set 5% copper in an Al-Cu alloy, the "
        "balance shows aluminum at 95%.\n\n"
        "If this line turns red, your total exceeds 100% -- reduce "
        "one of the element amounts."
    ),

    # ===== Stepping panel =====
    "step_el1": (
        "Primary element -- the base metal of your alloy.\n\n"
        "This is the 'solvent' element that makes up the majority "
        "of the alloy. For example, AL for aluminum alloys, FE for "
        "steels, or TI for titanium alloys."
    ),
    "step_el2": (
        "The alloying element you are adding to the base metal.\n\n"
        "This is the 'solute' whose composition you set with the "
        "spinner to the right. The x-axis of the phase diagram "
        "shows the amount of this element."
    ),
    "step_composition": (
        "How much of Element 2 is in your alloy.\n\n"
        "Think of it like a recipe: 0.10 mole fraction means 10 "
        "out of every 100 atoms are Element 2, and the remaining 90 "
        "are Element 1 (the base metal).\n\n"
        "In weight percent mode, 10 wt% means 10 grams of Element 2 "
        "per 100 grams of total alloy."
    ),
    "step_t_min": (
        "The lowest temperature in the scan.\n\n"
        "Reference points:\n"
        "  Room temperature: 300 K (27 C)\n"
        "  Liquid nitrogen:   77 K (-196 C)\n\n"
        "300 K is a good default -- it shows what phases exist at "
        "room temperature."
    ),
    "step_t_max": (
        "The highest temperature in the scan.\n\n"
        "This should be above the melting point of your alloy so the "
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
        "Most alloy calculations use 1 atm. You would only change "
        "this for vacuum heat treatment or high-pressure experiments."
    ),

    # ===== Phase diagram panel =====
    "pd_el1": (
        "First element (base metal) of the binary system.\n\n"
        "For an Al-Cu phase diagram, select AL here. The left side "
        "of the diagram (X = 0) represents pure Element 1."
    ),
    "pd_el2": (
        "Second element of the binary system.\n\n"
        "For an Al-Cu phase diagram, select CU here. The right side "
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
        "Should be above the liquidus (highest melting point) of the "
        "system so the full liquid region is visible.\n"
        "Reference: Al-Cu liquidus is about 1358 K (1085 C)."
    ),
    "pd_calculate": (
        "Run the phase diagram calculation.\n\n"
        "This maps out every phase boundary across the full "
        "composition range using pycalphad's binary strategy mapper. "
        "It may take 30 seconds to a few minutes depending on the "
        "system complexity."
    ),
    "pd_export_png": (
        "Save the phase diagram as a PNG image.\n\n"
        "The exported file includes a subtitle with your calculation "
        "conditions (elements, temperature range, pressure)."
    ),
    "pd_compare": (
        "Enter compare mode to view two phase diagrams side by side.\n\n"
        "The current diagram is copied to the left panel, and you "
        "can run a new calculation for the right panel. This is "
        "useful for comparing different element pairs or temperature "
        "ranges.\nClick again to exit compare mode."
    ),
    "pd_canvas": (
        "Interactive phase diagram plot.\n\n"
        "Click anywhere to inspect the composition and temperature "
        "at that point. Move the mouse to see live coordinates in "
        "the status bar."
    ),

    # ===== Scheil panel =====
    "scheil_start_temp": (
        "The temperature where solidification begins.\n\n"
        "This should be above the liquidus (the temperature where "
        "the alloy is fully liquid).\n"
        "For aluminum alloys: ~900-1000 K.\n"
        "For steels: ~1800-1900 K.\n\n"
        "If unsure, start high -- the simulation will find where "
        "freezing actually begins."
    ),
    "scheil_start_temp_c": (
        "Start temperature in Celsius for the Scheil simulation.\n\n"
        "This must be above the liquidus (fully liquid temperature) "
        "of your alloy -- otherwise there is nothing to solidify!\n\n"
        "Reference starting points:\n"
        "  Aluminum alloys: 627-727 C\n"
        "  Steels:         1327-1527 C\n"
        "  Copper alloys:  1027-1127 C"
    ),
    "scheil_step": (
        "Temperature decrease per simulation step.\n\n"
        "1 K is a good default. Smaller steps are more accurate but "
        "slower. The simulation proceeds by cooling the liquid step "
        "by step."
    ),
    "scheil_step_size": (
        "How much the temperature drops between each Scheil step.\n\n"
        "Smaller values give a smoother, more detailed solidification "
        "curve but take longer to compute.\n\n"
        "  1 K:   Good default -- detailed and reasonably fast\n"
        "  0.5 K: High resolution near eutectic reactions\n"
        "  5 K:   Quick overview (may miss fine details)"
    ),
    "scheil_cutoff": (
        "Stop the simulation when this fraction of liquid remains.\n\n"
        "Default is 0.01 (1% liquid remaining). The very last drop "
        "of liquid can be hard to solidify and may cause numerical "
        "issues.\n"
        "- 0.01: Standard (stops at 1% liquid)\n"
        "- 0.001: More complete but slower"
    ),

    # ===== Single-phase panel =====
    "sp_phase_list": (
        "Check the phases you want to compare.\n\n"
        "Common phases you will encounter:\n"
        "  LIQUID    -- the molten metal\n"
        "  FCC_A1    -- face-centered cubic (aluminum, copper, "
        "austenite)\n"
        "  BCC_A2    -- body-centered cubic (iron/ferrite, tungsten)\n"
        "  HCP_A3    -- hexagonal close-packed (titanium, magnesium)\n"
        "  CEMENTITE -- iron carbide (Fe3C), found in steels\n\n"
        "Each checked phase produces one curve on the plot. The phase "
        "with the lowest Gibbs energy at a given temperature is the "
        "most thermodynamically stable."
    ),

    # ===== Driving force =====
    "driving_force_threshold": (
        "The energy threshold (J/mol) for warning about phase "
        "stability.\n\n"
        "Phases with driving force below this value are 'close to "
        "forming'.\n"
        "- 500 J/mol: Very close (might form during processing)\n"
        "- 1000 J/mol: Moderately close\n"
        "- 5000 J/mol: Far from forming\n\n"
        "Lower threshold = only warn about imminent phase formation."
    ),

    # ===== T-zero =====
    "t0_phase1": (
        "The first crystal structure to compare.\n\n"
        "T0 finds where two structures have equal energy.\n"
        "For steels, compare FCC_A1 (austenite) vs BCC_A2 (ferrite)."
    ),
    "t0_phase2": (
        "The second crystal structure to compare.\n\n"
        "At the T0 temperature, both structures are equally stable.\n"
        "Below T0: one structure wins. Above T0: the other wins."
    ),

    # ===== Database =====
    "db_load": (
        "Load a thermodynamic database file (.TDB).\n\n"
        "This is always the first step. The database contains all "
        "the thermodynamic models needed for calculations."
    ),
    "db_path": (
        "The file path to your thermodynamic database.\n\n"
        "Common formats:\n"
        "- .TDB: Thermo-Calc format (most common)\n"
        "- .PDB: Pandat format\n\n"
        "Several free databases are available online for common "
        "alloy systems."
    ),
    "db_info": (
        "Show information about the currently loaded database.\n\n"
        "This tells you which elements and phases are available for "
        "calculations."
    ),

    # ===== Plot controls =====
    "zoom_in": (
        "Zoom into the chart to see details.\n\n"
        "You can also use the scroll wheel on your mouse to zoom."
    ),
    "zoom_out": (
        "Zoom out to see the full picture.\n\n"
        "Click 'Reset View' to go back to the original view."
    ),
    "reset_view": (
        "Reset the chart to its original zoom level and position.\n\n"
        "Use this if you have zoomed or panned and want to start "
        "fresh."
    ),
    "toggle_celsius": (
        "Switch between Kelvin and Celsius for temperature display.\n\n"
        "Kelvin = Celsius + 273.15\n"
        "Scientists use Kelvin; engineers often prefer Celsius.\n"
        "The underlying calculations always use Kelvin."
    ),
    "toggle_grid": (
        "Show or hide the grid lines on the chart.\n\n"
        "Grid lines help you read exact values from the plot."
    ),
    "legend_toggle": (
        "Show or hide the legend that labels each curve.\n\n"
        "The legend tells you which color corresponds to which phase."
    ),

    # ===== Thermo properties =====
    "property_selector": (
        "Choose which thermodynamic property to plot.\n\n"
        "- Gibbs Energy (G): The master property. The phase with the "
        "lowest G is the most stable.\n"
        "- Enthalpy (H): Heat content. Jumps in H indicate latent "
        "heat.\n"
        "- Entropy (S): Disorder. Higher entropy = more atomic "
        "randomness.\n"
        "- Heat Capacity (Cp): How much energy is needed to raise "
        "the temperature by 1 degree. Peaks in Cp indicate "
        "transformations."
    ),

    # ===== Volume =====
    "molar_volume": (
        "The volume occupied by one mole of atoms (about 6 x 10^23 "
        "atoms).\n\n"
        "Units: m3/mol or cm3/mol.\n"
        "Molar volume depends on crystal structure and temperature. "
        "Metals expand when heated and usually expand further upon "
        "melting."
    ),
    "density": (
        "Mass per unit volume (kg/m3 or g/cm3).\n\n"
        "Common densities:\n"
        "- Aluminum: 2.7 g/cm3 (light)\n"
        "- Titanium: 4.5 g/cm3 (medium)\n"
        "- Steel: 7.8 g/cm3 (heavy)\n"
        "- Tungsten: 19.3 g/cm3 (very heavy)\n"
        "- Gold: 19.3 g/cm3 (same as tungsten!)"
    ),

    # ===== History =====
    "history_panel": (
        "A log of all calculations you have run in this session.\n\n"
        "Click any entry to reload those settings and results. This "
        "is great for comparing different conditions without "
        "re-entering everything."
    ),
    "clear_history": (
        "Delete all saved calculation records from this session.\n\n"
        "This cannot be undone."
    ),
}


# ---------------------------------------------------------------------------
# 3. GLOSSARY -- plain-English definitions of metallurgy terms (50+ entries)
# ---------------------------------------------------------------------------

GLOSSARY: dict[str, dict[str, Any]] = {
    # ---- Basic concepts ----
    "Alloy": {
        "definition": (
            "A metal made by mixing two or more elements. Steel is an "
            "alloy of iron and carbon. Bronze is copper and tin. Brass "
            "is copper and zinc. Almost all metals used in engineering "
            "are alloys, not pure elements."
        ),
        "see_also": ["Element", "Composition"],
    },
    "Element": {
        "definition": (
            "A pure chemical substance made of only one type of atom. "
            "Iron (Fe), aluminum (Al), copper (Cu), and carbon (C) are "
            "elements. You cannot break an element into simpler "
            "substances by chemical means."
        ),
        "see_also": ["Alloy", "Periodic Table"],
    },
    "Composition": {
        "definition": (
            "The recipe of an alloy -- how much of each element it "
            "contains. Composition can be expressed as mole fraction "
            "(counting atoms) or weight percent (measuring mass). For "
            "example, 7075 aluminum is about 5.6% zinc, 2.5% "
            "magnesium, 1.6% copper, and the balance aluminum."
        ),
        "see_also": ["Mole Fraction", "Weight Percent"],
    },
    "Temperature": {
        "definition": (
            "A measure of how much thermal energy the atoms have. "
            "Higher temperature means atoms vibrate more and can "
            "rearrange more easily. In thermodynamics we use Kelvin "
            "(K), where 0 K is absolute zero and 273.15 K is the "
            "freezing point of water."
        ),
        "see_also": ["Pressure", "Equilibrium"],
    },
    "Pressure": {
        "definition": (
            "The force per unit area exerted on a material. Most "
            "metallurgy occurs at atmospheric pressure (101,325 Pa). "
            "Pressure mainly affects gas phases, but extreme pressures "
            "can change crystal structures (e.g., deep in the Earth)."
        ),
        "see_also": ["Temperature"],
    },
    "Mole Fraction": {
        "definition": (
            "The fraction of atoms that are a given element. If 10 "
            "out of 100 atoms are copper, the mole fraction of copper "
            "is 0.10. All mole fractions in an alloy must add up to "
            "1.0."
        ),
        "see_also": ["Weight Percent", "Composition"],
    },
    "Weight Percent": {
        "definition": (
            "The mass of an element divided by the total mass of the "
            "alloy, times 100. If 5 grams of copper are in 100 grams "
            "of alloy, that is 5 wt% copper. Weight percent is "
            "practical because you can measure it directly on a scale."
        ),
        "see_also": ["Mole Fraction", "Composition"],
    },

    # ---- Phase concepts ----
    "Phase": {
        "definition": (
            "A distinct form of matter with uniform properties "
            "throughout. Ice, water, and steam are three phases of "
            "H2O. In metals, different crystal structures are "
            "different phases. A single piece of metal can contain "
            "multiple phases side by side."
        ),
        "see_also": ["Crystal Structure", "Phase Diagram"],
    },
    "Crystal Structure": {
        "definition": (
            "The repeating three-dimensional pattern in which atoms "
            "arrange themselves in a solid. Think of it like a "
            "specific way of stacking oranges. Different stacking "
            "patterns (FCC, BCC, HCP) give the metal different "
            "properties."
        ),
        "see_also": ["FCC", "BCC", "HCP", "Phase"],
    },
    "Phase Diagram": {
        "definition": (
            "A map showing which phases are stable at each "
            "combination of temperature and composition. It is the "
            "most important tool in metallurgy -- it tells you what "
            "your alloy looks like inside at any condition."
        ),
        "see_also": ["Phase", "Phase Boundary", "Phase Region"],
    },
    "Phase Boundary": {
        "definition": (
            "A line on a phase diagram separating two different phase "
            "regions. Crossing a phase boundary means a phase "
            "transformation occurs -- a new phase appears or an "
            "existing one disappears."
        ),
        "see_also": ["Phase Diagram", "Phase Region"],
    },
    "Phase Region": {
        "definition": (
            "An area on a phase diagram where the same set of phases "
            "is stable. Inside a single-phase region, only one "
            "crystal structure exists. In a two-phase region, two "
            "structures coexist."
        ),
        "see_also": ["Phase Boundary", "Single Phase", "Two Phase"],
    },
    "Tie Line": {
        "definition": (
            "A horizontal line in a two-phase region of a phase "
            "diagram that connects the compositions of the two "
            "coexisting phases. It tells you what each phase is made "
            "of at that temperature."
        ),
        "see_also": ["Lever Rule", "Two Phase"],
    },
    "Lever Rule": {
        "definition": (
            "A method to calculate how much of each phase is present "
            "in a two-phase region, using the tie line. It works like "
            "a see-saw: the closer your overall composition is to one "
            "phase's composition, the more of that phase you have."
        ),
        "see_also": ["Tie Line", "Phase Fraction"],
    },
    "Single Phase": {
        "definition": (
            "A region on the phase diagram where only one crystal "
            "structure exists. The alloy is uniform throughout -- "
            "every part looks the same under a microscope."
        ),
        "see_also": ["Two Phase", "Phase Region"],
    },
    "Two Phase": {
        "definition": (
            "A region where two different crystal structures coexist "
            "side by side. Under a microscope you would see two "
            "different types of grains or one type embedded in the "
            "other."
        ),
        "see_also": ["Single Phase", "Tie Line", "Lever Rule"],
    },
    "Phase Fraction": {
        "definition": (
            "The proportion of the alloy that is a particular phase, "
            "expressed as a number between 0 and 1. A phase fraction "
            "of 0.30 means 30% of the material is that phase."
        ),
        "see_also": ["Lever Rule", "Phase"],
    },

    # ---- Important temperatures ----
    "Solidus": {
        "definition": (
            "The temperature below which the alloy is completely "
            "solid. If you heat above the solidus, the first drop of "
            "liquid appears. This is critically important -- never "
            "heat a metal above its solidus during processing unless "
            "you intend to melt it."
        ),
        "see_also": ["Liquidus", "Melting Point"],
    },
    "Liquidus": {
        "definition": (
            "The temperature above which the alloy is completely "
            "liquid. Below the liquidus, the first solid crystals "
            "begin to form during cooling. The liquidus is the "
            "starting point for solidification."
        ),
        "see_also": ["Solidus", "Melting Point"],
    },
    "Solvus": {
        "definition": (
            "The temperature below which a second solid phase "
            "precipitates out of the first. Think of it like sugar "
            "dissolved in tea: as the tea cools, sugar crystals start "
            "to form because the tea can no longer hold as much "
            "dissolved sugar."
        ),
        "see_also": ["Precipitate", "Heat Treatment"],
    },
    "Eutectic": {
        "definition": (
            "A special composition and temperature where liquid "
            "transforms directly into two solid phases simultaneously. "
            "The eutectic temperature is the lowest melting point in "
            "the system. Eutectic alloys are prized for casting "
            "because they melt sharply at one temperature (no mushy "
            "zone)."
        ),
        "see_also": ["Peritectic", "Eutectoid", "Liquidus"],
    },
    "Peritectic": {
        "definition": (
            "A reaction where a solid phase and liquid react to form "
            "a different solid phase upon cooling. Peritectic "
            "reactions are common but often sluggish -- the product "
            "phase can coat the original solid and slow the reaction."
        ),
        "see_also": ["Eutectic", "Liquidus"],
    },
    "Eutectoid": {
        "definition": (
            "Similar to a eutectic, but entirely in the solid state: "
            "one solid phase transforms into two different solid "
            "phases upon cooling. The most famous eutectoid is in "
            "steel at 727 C, where austenite transforms into ferrite "
            "+ cementite (pearlite)."
        ),
        "see_also": ["Eutectic", "Pearlite", "Austenite"],
    },
    "Melting Point": {
        "definition": (
            "The temperature at which a pure element changes from "
            "solid to liquid. For alloys, there is no single melting "
            "point -- instead there is a melting range between the "
            "solidus and liquidus."
        ),
        "see_also": ["Solidus", "Liquidus"],
    },

    # ---- Crystal structures ----
    "FCC": {
        "definition": (
            "Face-Centered Cubic. Atoms sit at each corner and the "
            "center of each face of a cube. This is one of the most "
            "efficient packing arrangements. FCC metals (aluminum, "
            "copper, nickel, gold) tend to be ductile, formable, and "
            "have good corrosion resistance."
        ),
        "see_also": ["BCC", "HCP", "Crystal Structure"],
    },
    "BCC": {
        "definition": (
            "Body-Centered Cubic. Atoms sit at each corner plus one "
            "in the center of the cube. BCC metals (iron at room "
            "temperature, chromium, tungsten) tend to be stronger "
            "than FCC but less ductile, especially at low temperatures."
        ),
        "see_also": ["FCC", "HCP", "Crystal Structure"],
    },
    "HCP": {
        "definition": (
            "Hexagonal Close-Packed. Atoms are arranged in hexagonal "
            "layers. HCP metals (titanium, magnesium, zinc) have "
            "directional properties -- they behave differently "
            "depending on which direction you pull or push."
        ),
        "see_also": ["FCC", "BCC", "Crystal Structure"],
    },
    "Diamond Cubic": {
        "definition": (
            "A crystal structure where each atom bonds to exactly "
            "four neighbors in a tetrahedral arrangement. Silicon "
            "and germanium have this structure. It is the basis of "
            "semiconductor technology."
        ),
        "see_also": ["Crystal Structure", "FCC"],
    },

    # ---- Thermodynamic concepts ----
    "Gibbs Energy": {
        "definition": (
            "The master thermodynamic quantity that determines which "
            "phases are stable. Nature always seeks the lowest Gibbs "
            "energy. The phase (or mixture of phases) with the lowest "
            "total Gibbs energy wins. Also called Gibbs free energy "
            "or simply G."
        ),
        "see_also": ["Enthalpy", "Entropy", "Equilibrium"],
    },
    "Gibbs Free Energy": {
        "definition": (
            "Same as Gibbs Energy (G = H - TS). The thermodynamic "
            "potential that determines phase stability. At equilibrium, "
            "the system minimizes its total Gibbs energy. The phase "
            "with the lowest G at a given temperature and pressure "
            "is the stable one."
        ),
        "see_also": ["Enthalpy", "Entropy", "Equilibrium"],
    },
    "Enthalpy": {
        "definition": (
            "The heat content of a material. When a metal melts, it "
            "absorbs enthalpy (heat) from the surroundings. When it "
            "solidifies, it releases enthalpy. Large enthalpy changes "
            "correspond to large amounts of heat involved in a "
            "transformation."
        ),
        "see_also": ["Gibbs Energy", "Entropy", "Heat Capacity"],
    },
    "Entropy": {
        "definition": (
            "A measure of atomic disorder or randomness. Liquids have "
            "high entropy (atoms are randomly arranged). Perfect "
            "crystals at absolute zero have zero entropy. Nature "
            "tends toward higher entropy, which is why things melt "
            "when heated."
        ),
        "see_also": ["Gibbs Energy", "Enthalpy", "Temperature"],
    },
    "Heat Capacity": {
        "definition": (
            "How much energy is needed to raise the temperature of "
            "the material by one degree. A high heat capacity means "
            "the material takes a lot of energy to heat up. Peaks in "
            "heat capacity versus temperature indicate phase "
            "transformations."
        ),
        "see_also": ["Enthalpy", "Temperature"],
    },
    "Chemical Potential": {
        "definition": (
            "The 'eagerness' of an element to leave or join a phase. "
            "If the chemical potential of copper is higher in phase A "
            "than phase B, copper atoms will tend to move from A to B "
            "until the potentials equalize."
        ),
        "see_also": ["Gibbs Energy", "Equilibrium"],
    },
    "Equilibrium": {
        "definition": (
            "The state where everything has settled down and no "
            "further changes occur. At equilibrium, the Gibbs energy "
            "is at its minimum, and the chemical potential of each "
            "element is the same in every phase. Real processes "
            "rarely reach perfect equilibrium, but it is the "
            "reference point."
        ),
        "see_also": ["Gibbs Energy", "Metastable"],
    },
    "Driving Force": {
        "definition": (
            "The energy difference that pushes a system toward a "
            "phase transformation. A large driving force means the "
            "transformation will happen readily. Zero driving force "
            "means the system is already at equilibrium for that "
            "phase."
        ),
        "see_also": ["Gibbs Energy", "Equilibrium", "Metastable"],
    },
    "Metastable": {
        "definition": (
            "A state that is not the lowest-energy arrangement but "
            "is stable enough to persist for a long time. Martensite "
            "in hardened steel is metastable -- it would prefer to "
            "decompose but does not have enough energy to rearrange "
            "at room temperature. Many useful engineering materials "
            "are metastable."
        ),
        "see_also": ["Equilibrium", "Driving Force", "Martensite"],
    },
    "Latent Heat": {
        "definition": (
            "The energy absorbed or released during a phase change "
            "without any change in temperature. When ice melts, it "
            "absorbs latent heat while staying at 0 C. The same "
            "happens when metals melt -- the latent heat of fusion "
            "must be supplied to complete melting."
        ),
        "see_also": ["Enthalpy", "Melting Point"],
    },
    "Miscibility Gap": {
        "definition": (
            "A composition-temperature region where a single phase "
            "is unstable and separates into two phases of different "
            "compositions. Like oil and water refusing to mix, some "
            "metal atoms prefer to segregate from each other."
        ),
        "see_also": ["Solvus", "Phase Diagram"],
    },

    # ---- Processing terms ----
    "Solidification": {
        "definition": (
            "The process of liquid metal becoming solid. During "
            "solidification, atoms leave the disorganized liquid and "
            "attach to growing crystals. How this happens (fast or "
            "slow, uniformly or not) determines the microstructure "
            "and properties of the final product."
        ),
        "see_also": ["Casting", "Scheil Simulation", "Liquidus"],
    },
    "Casting": {
        "definition": (
            "The process of pouring liquid metal into a mold and "
            "letting it solidify into a desired shape. One of the "
            "oldest metalworking processes, dating back thousands of "
            "years. The Scheil simulation models what happens inside "
            "the casting."
        ),
        "see_also": ["Solidification", "Scheil Simulation"],
    },
    "Heat Treatment": {
        "definition": (
            "Controlled heating and cooling of a solid metal to "
            "change its properties. By carefully choosing temperatures "
            "and cooling rates, metallurgists can make the same alloy "
            "soft or hard, ductile or strong."
        ),
        "see_also": ["Quenching", "Annealing", "Tempering", "Aging"],
    },
    "Quenching": {
        "definition": (
            "Rapidly cooling a metal, usually by plunging it into "
            "water or oil. Quenching traps atoms in a high-temperature "
            "arrangement before they can rearrange. This is how steel "
            "is hardened -- fast cooling traps carbon in a strained "
            "crystal structure (martensite)."
        ),
        "see_also": ["Heat Treatment", "Martensite", "Metastable"],
    },
    "Annealing": {
        "definition": (
            "Heating a metal and then cooling it slowly to make it "
            "softer, more ductile, and relieve internal stresses. "
            "Annealing lets atoms diffuse to their equilibrium "
            "positions, undoing the effects of cold working or "
            "quenching."
        ),
        "see_also": ["Heat Treatment", "Equilibrium"],
    },
    "Tempering": {
        "definition": (
            "Heating a hardened (quenched) steel to a moderate "
            "temperature to reduce brittleness while keeping most "
            "of the hardness. Tempering allows some carbon atoms to "
            "move out of the strained martensite, relieving internal "
            "stress."
        ),
        "see_also": ["Quenching", "Martensite", "Heat Treatment"],
    },
    "Aging": {
        "definition": (
            "A heat treatment where a supersaturated solid solution "
            "is held at an elevated temperature so that tiny "
            "precipitate particles form. These particles block the "
            "movement of crystal defects (dislocations), dramatically "
            "increasing strength. Used widely in aluminum and nickel "
            "alloys."
        ),
        "see_also": ["Precipitate", "Heat Treatment", "Solvus"],
    },
    "Homogenization": {
        "definition": (
            "A heat treatment at high temperature for a long time "
            "that evens out composition differences (segregation) "
            "left over from casting. After homogenization, the alloy "
            "has a more uniform composition throughout."
        ),
        "see_also": ["Casting", "Solidification", "Heat Treatment"],
    },

    # ---- Properties ----
    "Strength": {
        "definition": (
            "How much force a material can withstand before it "
            "permanently deforms or breaks. Measured in MPa or GPa. "
            "High-strength alloys are used in aircraft, bridges, and "
            "tools."
        ),
        "see_also": ["Hardness", "Ductility", "Toughness"],
    },
    "Hardness": {
        "definition": (
            "A material's resistance to being dented or scratched. "
            "Measured by pressing a hard indenter into the surface "
            "and measuring the mark it leaves. Hardness correlates "
            "with strength but is easier to measure."
        ),
        "see_also": ["Strength", "Martensite"],
    },
    "Ductility": {
        "definition": (
            "How much a metal can be stretched or deformed before it "
            "breaks. A ductile metal (like copper or gold) can be "
            "drawn into a thin wire. A brittle metal (like cast iron) "
            "snaps with little deformation."
        ),
        "see_also": ["Toughness", "Strength"],
    },
    "Toughness": {
        "definition": (
            "A material's ability to absorb energy before fracturing. "
            "Tough materials are both strong AND ductile. A tough "
            "metal can take a hit without shattering. Toughness is "
            "critical for safety-critical applications."
        ),
        "see_also": ["Strength", "Ductility"],
    },
    "Corrosion Resistance": {
        "definition": (
            "A material's ability to resist chemical attack (rusting, "
            "tarnishing, dissolving). Stainless steel resists corrosion "
            "because chromium forms a protective oxide layer. Aluminum "
            "also forms a natural protective oxide."
        ),
        "see_also": ["Alloy"],
    },

    # ---- Specific phases ----
    "Austenite": {
        "definition": (
            "The FCC (face-centered cubic) phase of iron. Stable at "
            "high temperatures (above 912 C in pure iron). Austenite "
            "can dissolve much more carbon than ferrite can. "
            "Austenitic stainless steels retain this structure at "
            "room temperature thanks to nickel additions."
        ),
        "see_also": ["Ferrite", "FCC", "Martensite"],
    },
    "Ferrite": {
        "definition": (
            "The BCC (body-centered cubic) phase of iron. Stable at "
            "room temperature. Ferrite is soft, ductile, and "
            "magnetic. It can dissolve very little carbon (only "
            "about 0.02%), which is why excess carbon forms other "
            "phases like cementite."
        ),
        "see_also": ["Austenite", "BCC", "Cementite"],
    },
    "Martensite": {
        "definition": (
            "A very hard, metastable phase formed when austenite is "
            "quenched (cooled rapidly). The carbon atoms get trapped "
            "in a distorted crystal lattice, creating enormous "
            "internal stress that makes the steel extremely hard but "
            "brittle. This is the basis of steel hardening."
        ),
        "see_also": ["Austenite", "Quenching", "Metastable"],
    },
    "Cementite": {
        "definition": (
            "Iron carbide (Fe3C). A hard, brittle compound of iron "
            "and carbon. It forms when there is more carbon than "
            "ferrite can hold. Cementite combined with ferrite in a "
            "layered structure is called pearlite."
        ),
        "see_also": ["Ferrite", "Pearlite"],
    },
    "Pearlite": {
        "definition": (
            "A layered microstructure of alternating plates of "
            "ferrite and cementite, formed by the eutectoid "
            "decomposition of austenite in steel. Named for its "
            "mother-of-pearl appearance under a microscope. Pearlite "
            "provides a good balance of strength and ductility."
        ),
        "see_also": ["Ferrite", "Cementite", "Eutectoid"],
    },
    "Intermetallic": {
        "definition": (
            "A compound formed between two or more metals with a "
            "specific crystal structure and composition (e.g., "
            "Al2Cu, Ni3Al). Intermetallics are usually hard and "
            "brittle. They can be beneficial (strengthening "
            "precipitates) or harmful (embrittling grain boundaries)."
        ),
        "see_also": ["Precipitate", "Phase"],
    },
    "Precipitate": {
        "definition": (
            "A small particle of a second phase that forms within a "
            "matrix phase. Like sugar crystals forming in a cooling "
            "syrup. Precipitates can dramatically increase the "
            "strength of an alloy by blocking the movement of "
            "defects (dislocations)."
        ),
        "see_also": ["Aging", "Solvus", "Intermetallic"],
    },

    # ---- Calculation methods ----
    "CALPHAD": {
        "definition": (
            "CALculation of PHAse Diagrams. A method for modeling "
            "the thermodynamic properties of alloys by fitting "
            "mathematical functions to experimental data. CALPHAD "
            "databases and software can then predict phase diagrams "
            "and properties for any composition and temperature."
        ),
        "see_also": ["Phase Diagram", "Gibbs Energy"],
    },
    "Scheil Simulation": {
        "definition": (
            "A model of solidification that assumes complete mixing "
            "in the liquid (atoms can move freely) but zero diffusion "
            "in the solid (atoms are frozen in place). This is closer "
            "to real casting than equilibrium calculations, especially "
            "for fast cooling."
        ),
        "see_also": ["Solidification", "Casting", "Equilibrium"],
    },
    "T-Zero": {
        "definition": (
            "The temperature at which two phases have the same Gibbs "
            "energy at the same composition. Below T0, a diffusionless "
            "(very fast, no atom mixing needed) transformation from "
            "one phase to the other becomes thermodynamically possible."
        ),
        "see_also": ["Gibbs Energy", "Martensite", "Driving Force"],
    },
    "T-Zero (T0)": {
        "definition": (
            "Same as T-Zero. The temperature at which two phases "
            "have equal Gibbs energy at the same composition. "
            "Important for diffusionless (martensitic) transformations."
        ),
        "see_also": ["Gibbs Energy", "Driving Force"],
    },
    "Molar Volume": {
        "definition": (
            "The volume occupied by one mole (about 6 x 10^23 atoms) "
            "of a substance. Depends on crystal structure and "
            "temperature. Used to calculate density and to predict "
            "volume changes during phase transformations."
        ),
        "see_also": ["Density", "Crystal Structure"],
    },
    "Density": {
        "definition": (
            "Mass per unit volume, usually in g/cm3 or kg/m3. A key "
            "design parameter -- lightweight alloys (aluminum, "
            "magnesium) have low density; heavy-duty alloys (steel, "
            "nickel superalloys) have high density."
        ),
        "see_also": ["Molar Volume", "Alloy"],
    },

    # ---- Additional terms ----
    "Periodic Table": {
        "definition": (
            "The chart that organizes all chemical elements by their "
            "properties. Elements in the same column tend to behave "
            "similarly. In metallurgy, transition metals (the large "
            "middle block) are the most important group."
        ),
        "see_also": ["Element"],
    },
    "Segregation": {
        "definition": (
            "Uneven distribution of elements within a casting. During "
            "solidification, the solid that forms first has a "
            "different composition than the liquid, leading to "
            "composition gradients. Severe segregation can cause weak "
            "spots and inconsistent properties."
        ),
        "see_also": ["Solidification", "Scheil Simulation",
                      "Homogenization"],
    },
    "Diffusion": {
        "definition": (
            "The movement of atoms through a material driven by "
            "concentration or energy differences. Diffusion is faster "
            "at higher temperatures. It is the mechanism behind many "
            "processes: aging, homogenization, carburizing, and "
            "oxidation."
        ),
        "see_also": ["Temperature", "Aging", "Homogenization"],
    },
    "Supersaturation": {
        "definition": (
            "A condition where more of an element is dissolved in a "
            "phase than the equilibrium limit allows. Like dissolving "
            "extra sugar in hot tea -- it stays dissolved until the "
            "tea cools and sugar crystals precipitate out. "
            "Supersaturation is the starting point for precipitation "
            "hardening."
        ),
        "see_also": ["Solvus", "Precipitate", "Aging"],
    },
    "Grain": {
        "definition": (
            "A single crystal within a polycrystalline metal. Most "
            "metals are made of many tiny grains, each with atoms "
            "arranged in the same crystal structure but oriented in "
            "a different direction. Smaller grains generally mean "
            "stronger metal (Hall-Petch effect)."
        ),
        "see_also": ["Crystal Structure", "Grain Boundary"],
    },
    "Grain Boundary": {
        "definition": (
            "The interface between two grains with different "
            "orientations. Grain boundaries are regions of atomic "
            "mismatch -- atoms do not pack as neatly. They can be "
            "sources of strength (blocking defect movement) or "
            "weakness (sites for corrosion or impurity accumulation)."
        ),
        "see_also": ["Grain", "Strength"],
    },
    "TDB File": {
        "definition": (
            "Thermodynamic DataBase file. A text file containing "
            "assessed thermodynamic parameters (Gibbs energy models) "
            "for an alloy system. The standard exchange format for "
            "CALPHAD data. You load one of these to start working."
        ),
        "see_also": ["CALPHAD"],
    },
    "Gibbs Phase Rule": {
        "definition": (
            "F = C - P + 2, where F is degrees of freedom, C is the "
            "number of components (elements), and P is the number of "
            "phases. It tells you how many variables (temperature, "
            "pressure, composition) you can independently change "
            "without losing a phase."
        ),
        "see_also": ["Phase", "Equilibrium", "Eutectic"],
    },
}


# ---------------------------------------------------------------------------
# 4. DID_YOU_KNOW -- educational facts for rotation display (40 entries)
# ---------------------------------------------------------------------------

DID_YOU_KNOW: list[str] = [
    (
        "The Eiffel Tower is made of puddled iron -- a nearly "
        "carbon-free iron alloy that resists corrosion better than "
        "steel."
    ),
    (
        "The Bronze Age began around 3300 BC when humans discovered "
        "that adding tin to copper made it much harder."
    ),
    (
        "Aluminum was once more expensive than gold. Napoleon III "
        "served his most honored guests with aluminum utensils while "
        "lesser guests ate with gold."
    ),
    (
        "Steel is just iron with a tiny amount of carbon -- typically "
        "less than 2%. That small addition changes everything."
    ),
    (
        "The Titanic's hull was made of a steel alloy that becomes "
        "brittle in cold water -- a factor in the disaster."
    ),
    (
        "Jet engine turbine blades operate at temperatures above the "
        "melting point of the blade alloy. Special coatings and "
        "internal cooling channels keep them from melting."
    ),
    (
        "Gold is so ductile that a single ounce can be beaten into a "
        "sheet covering 300 square feet -- thin enough to see light "
        "through."
    ),
    (
        "Stainless steel was discovered by accident in 1913 when "
        "Harry Brearley noticed that discarded chromium-steel samples "
        "in a scrap pile had not rusted."
    ),
    (
        "The CALPHAD method was pioneered by Larry Kaufman in the "
        "1960s and 1970s, combining thermodynamic theory with "
        "computer calculations to predict phase diagrams."
    ),
    (
        "Titanium has the highest strength-to-weight ratio of any "
        "structural metal, which is why it is used in aerospace, "
        "medical implants, and sports equipment."
    ),
    (
        "Shape memory alloys (like Nitinol: nickel-titanium) can be "
        "bent and then return to their original shape when heated. "
        "The secret is a reversible phase transformation."
    ),
    (
        "Pure iron is actually soft and relatively useless for tools. "
        "It was the discovery that carbon transforms iron into steel "
        "that launched the Iron Age."
    ),
    (
        "Aluminum makes up 8% of the Earth's crust by weight -- the "
        "third most abundant element. Yet it was not isolated until "
        "1825 because it bonds so strongly to oxygen."
    ),
    (
        "The Gibbs energy concept was developed by Josiah Willard "
        "Gibbs in the 1870s. His work was so abstract that few "
        "scientists understood it during his lifetime."
    ),
    (
        "Damascus steel swords, famous for their beautiful wave "
        "patterns and legendary sharpness, got their properties from "
        "nanoscale cementite structures -- ancient nanotechnology."
    ),
    (
        "Copper is naturally antibacterial. Hospital doorknobs and "
        "handrails made of copper alloys kill bacteria on contact, "
        "reducing infection rates."
    ),
    (
        "The International Space Station uses aluminum alloy 2219 "
        "for its main structure -- the same alloy family used in the "
        "Saturn V rocket fuel tanks."
    ),
    (
        "Mercury is the only metal that is liquid at room "
        "temperature. Its melting point is -39 C (234 K)."
    ),
    (
        "Eutectic alloys are used in soldering because they melt "
        "sharply at one temperature rather than having a mushy zone. "
        "Classic solder (63% tin, 37% lead) is a near-eutectic "
        "composition."
    ),
    (
        "The cores of white dwarf stars are essentially giant "
        "metallic crystals. In 2004, astronomers found a white dwarf "
        "with a crystallized core estimated at 10 billion trillion "
        "trillion carats of diamond."
    ),
    (
        "Maraging steels (martensitic + aging) are among the "
        "strongest steels ever made, reaching strengths over "
        "2,400 MPa. They contain almost no carbon -- instead using "
        "nickel, cobalt, and molybdenum."
    ),
    (
        "Cast iron was used for buildings and bridges in the 1800s. "
        "Its high carbon content (2-4%) makes it easy to cast but "
        "brittle, which led to some spectacular failures."
    ),
    (
        "Austenitic stainless steels (like 304 and 316) are not "
        "magnetic, but ferritic and martensitic stainless steels are. "
        "You can test with a refrigerator magnet."
    ),
    (
        "The yield strength of pure aluminum is about 10 MPa. After "
        "alloying with copper, magnesium, and zinc and applying heat "
        "treatment, 7075-T6 aluminum reaches 503 MPa -- a 50x "
        "increase."
    ),
    (
        "Tungsten has the highest melting point of any metal: "
        "3,422 C (3,695 K). This is why it is used for light bulb "
        "filaments and rocket nozzles."
    ),
    (
        "Superalloys used in jet engines contain more than ten "
        "different elements, each carefully chosen using CALPHAD-type "
        "calculations to optimize high-temperature strength."
    ),
    (
        "The concept of a phase diagram dates back to 1897 when "
        "Hendrik Roozeboom published the first systematic iron-"
        "carbon diagram, laying the foundation for modern metallurgy."
    ),
    (
        "Gallium melts at just 29.8 C (303 K) -- you can literally "
        "melt it in your hand. It is used in semiconductors and as "
        "a non-toxic replacement for mercury."
    ),
    (
        "Precipitation hardening was discovered in 1906 by Alfred "
        "Wilm, who noticed that an aluminum-copper alloy got harder "
        "over several days after quenching. He did not understand "
        "why until much later -- tiny precipitate particles were "
        "forming."
    ),
    (
        "Steel railway tracks in the 1800s lasted only a few months. "
        "The switch to Bessemer steel (lower impurities, controlled "
        "carbon) increased track life to over a decade."
    ),
    (
        "A single-crystal turbine blade contains no grain boundaries "
        "at all. Growing an entire blade as one perfect crystal "
        "eliminates the weakest links, allowing it to survive "
        "extreme temperatures."
    ),
    (
        "Zinc coating on galvanized steel works by sacrificial "
        "protection. The zinc corrodes preferentially, protecting "
        "the steel underneath even if the coating is scratched."
    ),
    (
        "Plutonium has six different crystal structures (allotropes) "
        "at atmospheric pressure -- more than any other element. "
        "This makes it extremely difficult to machine or cast."
    ),
    (
        "Nickel superalloys in jet engines maintain their strength "
        "at temperatures where aluminum alloys would have already "
        "melted. A gamma-prime precipitate (Ni3Al) is the secret to "
        "their performance."
    ),
    (
        "Modern smartphone cases often use 7000-series aluminum "
        "alloys -- the same family developed for aerospace. CALPHAD "
        "calculations helped optimize these compositions."
    ),
    (
        "Entropy is the reason alloys exist. Mixing different atoms "
        "increases entropy, which lowers Gibbs energy, which means "
        "nature favors mixing over staying pure -- at least to some "
        "extent."
    ),
    (
        "Tin pest is a phase transformation that turns shiny "
        "metallic tin (beta) into a crumbly grey powder (alpha) "
        "below 13 C. Some historians believe it contributed to the "
        "failure of Napoleon's Russian campaign -- tin buttons on "
        "uniforms disintegrated in the cold."
    ),
    (
        "High-entropy alloys contain five or more elements in "
        "roughly equal proportions, defying the traditional concept "
        "of a 'base' metal with minor additions. They can have "
        "remarkable properties."
    ),
    (
        "The Haber-Bosch process, which feeds half the world's "
        "population by synthesizing ammonia fertilizer, relies on an "
        "iron-based catalyst. The catalyst's phase structure is "
        "critical to its function."
    ),
    (
        "The age of the Earth (about 4.5 billion years) was first "
        "accurately determined using isotopic analysis of lead and "
        "uranium in mineral samples -- a technique rooted in the "
        "same thermodynamics used in CALPHAD."
    ),
]


# ---------------------------------------------------------------------------
# 5. PHASE_EXPLANATIONS -- detailed descriptions for phase name popups
# ---------------------------------------------------------------------------

PHASE_EXPLANATIONS: dict[str, dict[str, str]] = {
    "LIQUID": {
        "name": "Liquid",
        "crystal": "None (atoms move freely)",
        "description": (
            "Molten metal. Atoms have enough energy to move around "
            "freely, like water. There is no long-range order -- "
            "atoms are arranged randomly."
        ),
        "found_in": "All metals above their melting point",
        "significance": (
            "This is where casting begins. Understanding the liquid "
            "phase helps predict how metals solidify and what defects "
            "might form during casting."
        ),
    },
    "FCC_A1": {
        "name": "Face-Centered Cubic (FCC)",
        "crystal": (
            "Atoms at each corner and center of each face of a cube"
        ),
        "description": (
            "One of the most common crystal structures in metals. "
            "Atoms pack very efficiently (74% of space is filled), "
            "making these metals generally soft, ductile, and easy "
            "to form."
        ),
        "found_in": (
            "Aluminum, copper, nickel, gold, silver, lead, austenitic "
            "stainless steel, gamma-iron (above 912 C)"
        ),
        "significance": (
            "FCC metals are easy to shape and form. When you bend "
            "aluminum foil, the FCC crystal structure is what allows "
            "it to deform without breaking. FCC has many slip systems, "
            "meaning atoms can slide past each other easily."
        ),
    },
    "BCC_A2": {
        "name": "Body-Centered Cubic (BCC)",
        "crystal": (
            "Atoms at each corner and one in the center of the cube"
        ),
        "description": (
            "A slightly less dense packing than FCC (68% vs 74%). "
            "BCC metals tend to be stronger but less ductile, "
            "especially at low temperatures where they can become "
            "brittle."
        ),
        "found_in": (
            "Iron at room temperature (alpha-iron/ferrite), chromium, "
            "tungsten, vanadium, molybdenum, ferritic and martensitic "
            "stainless steels"
        ),
        "significance": (
            "Iron transforms from BCC (ferrite) to FCC (austenite) "
            "when heated above 912 C. This transformation is the "
            "basis of ALL steel heat treatment. Without it, we could "
            "not harden steel."
        ),
    },
    "BCC_B2": {
        "name": "Ordered BCC (B2)",
        "crystal": (
            "Like BCC but with two types of atoms in specific "
            "positions (one at corners, the other in the center)"
        ),
        "description": (
            "An ordered version of BCC where different elements "
            "occupy specific sites in the crystal. The ordering can "
            "significantly change properties compared to random BCC."
        ),
        "found_in": (
            "NiAl, FeAl, CuZn (beta brass), TiAl (at some "
            "compositions)"
        ),
        "significance": (
            "Ordered phases are often harder and more brittle than "
            "their disordered counterparts. The order-disorder "
            "transition is an important phenomenon in many alloy "
            "systems."
        ),
    },
    "HCP_A3": {
        "name": "Hexagonal Close-Packed (HCP)",
        "crystal": (
            "Atoms in hexagonal layers stacked ABAB. Packing "
            "efficiency is the same as FCC (74%), but the symmetry "
            "is different."
        ),
        "description": (
            "A close-packed structure with hexagonal symmetry. HCP "
            "metals have strong directional properties -- they "
            "behave differently depending on the direction of loading."
        ),
        "found_in": (
            "Titanium (alpha phase), magnesium, zinc, zirconium, "
            "cobalt (at room temperature), beryllium"
        ),
        "significance": (
            "HCP metals are important in aerospace (titanium) and "
            "lightweight applications (magnesium). Their anisotropic "
            "behavior makes texture (preferred grain orientation) "
            "very important in processing."
        ),
    },
    "DIAMOND_A4": {
        "name": "Diamond Cubic",
        "crystal": (
            "Each atom bonds to exactly four neighbors in a "
            "tetrahedron"
        ),
        "description": (
            "A relatively open structure with only 34% packing "
            "efficiency. The strong directional bonds make these "
            "materials very hard but brittle."
        ),
        "found_in": (
            "Silicon, germanium, carbon (diamond), tin (alpha/grey)"
        ),
        "significance": (
            "This is the crystal structure of semiconductors. "
            "Silicon's diamond cubic structure is the foundation of "
            "the entire electronics industry."
        ),
    },
    "CBCC_A12": {
        "name": "Complex BCC (alpha-Mn type)",
        "crystal": "A complex structure with 58 atoms per unit cell",
        "description": (
            "A complicated crystal structure found in manganese at "
            "room temperature. Much more complex than simple BCC."
        ),
        "found_in": (
            "Alpha-manganese, some intermetallic compounds"
        ),
        "significance": (
            "This complex structure makes pure manganese very hard "
            "and brittle. It is an example of how not all metals "
            "have simple crystal structures."
        ),
    },
    "CUB_A13": {
        "name": "Complex Cubic (beta-Mn type)",
        "crystal": (
            "A complex cubic structure with 20 atoms per unit cell"
        ),
        "description": (
            "Another complex crystal structure, found in "
            "beta-manganese between 727 C and 1100 C."
        ),
        "found_in": (
            "Beta-manganese, some intermetallic compounds"
        ),
        "significance": (
            "An intermediate structure in the complex sequence of "
            "transformations that manganese undergoes."
        ),
    },
    "SIGMA": {
        "name": "Sigma Phase",
        "crystal": "Tetragonal structure with 30 atoms per unit cell",
        "description": (
            "A hard, brittle intermetallic phase that can form in "
            "stainless steels and superalloys when held at "
            "intermediate temperatures for too long."
        ),
        "found_in": (
            "Stainless steels (especially duplex and "
            "super-austenitic), Fe-Cr system, nickel superalloys"
        ),
        "significance": (
            "Sigma phase is one of the most feared phases in "
            "stainless steel metallurgy. It drastically reduces "
            "toughness and corrosion resistance. Heat treatment "
            "procedures are carefully designed to avoid it."
        ),
    },
    "CEMENTITE": {
        "name": "Cementite (Fe3C)",
        "crystal": (
            "Orthorhombic structure with 16 atoms per unit cell"
        ),
        "description": (
            "Iron carbide -- a hard, brittle compound containing "
            "6.67 wt% carbon. It is the primary carbon-bearing phase "
            "in most steels."
        ),
        "found_in": "Carbon steels, cast irons, tool steels",
        "significance": (
            "Cementite is what gives steel its hardness. In pearlite, "
            "thin plates of cementite alternating with ferrite create "
            "a structure that is both strong and reasonably ductile."
        ),
    },
    "FE3C": {
        "name": "Cementite (Fe3C)",
        "crystal": (
            "Orthorhombic structure with 16 atoms per unit cell"
        ),
        "description": (
            "Same as CEMENTITE -- iron carbide. Different databases "
            "may use different names for the same phase."
        ),
        "found_in": "Carbon steels, cast irons, tool steels",
        "significance": (
            "The backbone of steel metallurgy. Controls hardness, "
            "wear resistance, and strength."
        ),
    },
    "GRAPHITE": {
        "name": "Graphite",
        "crystal": (
            "Hexagonal layers of carbon atoms with weak bonding "
            "between layers"
        ),
        "description": (
            "The stable form of pure carbon at normal conditions. "
            "Layers slide easily over each other, making graphite an "
            "excellent lubricant."
        ),
        "found_in": (
            "Cast irons (especially ductile and grey iron), carbon "
            "electrodes"
        ),
        "significance": (
            "In cast irons, whether carbon appears as graphite "
            "flakes (grey iron), graphite nodules (ductile iron), "
            "or cementite (white iron) completely determines the "
            "properties."
        ),
    },
    "AL2CU": {
        "name": "Theta Phase (Al2Cu)",
        "crystal": "Body-centered tetragonal (C16 structure)",
        "description": (
            "An intermetallic compound of aluminum and copper. It "
            "is the equilibrium precipitate in Al-Cu alloys."
        ),
        "found_in": (
            "2xxx series aluminum alloys (e.g., 2024, 2219)"
        ),
        "significance": (
            "The theta phase and its precursors (GP zones, "
            "theta-double-prime, theta-prime) are responsible for "
            "the age hardening of Al-Cu alloys. The sequence of "
            "precipitate evolution is a textbook example of "
            "precipitation strengthening."
        ),
    },
    "AL2CU_C16": {
        "name": "Theta Phase (Al2Cu, C16 structure)",
        "crystal": "Body-centered tetragonal",
        "description": (
            "Same as AL2CU -- the equilibrium theta precipitate in "
            "aluminum-copper alloys. The C16 suffix indicates the "
            "specific crystal structure type."
        ),
        "found_in": "2xxx series aluminum alloys",
        "significance": (
            "Understanding this phase is key to designing the heat "
            "treatment of aluminum-copper alloys."
        ),
    },
    "AL3FE": {
        "name": "Al3Fe (Iron Aluminide)",
        "crystal": "Monoclinic",
        "description": (
            "An intermetallic compound of aluminum and iron. "
            "Generally forms as brittle needles."
        ),
        "found_in": (
            "Al-Fe alloys and recycled aluminum with iron impurities"
        ),
        "significance": (
            "Generally undesirable -- forms brittle needles that "
            "reduce ductility in aluminum castings."
        ),
    },
    "MG2SI": {
        "name": "Magnesium Silicide (Mg2Si)",
        "crystal": "Antifluorite cubic structure",
        "description": (
            "An intermetallic compound of magnesium and silicon. It "
            "and its precursors are the strengthening precipitates "
            "in 6xxx series aluminum alloys."
        ),
        "found_in": (
            "6xxx series aluminum alloys (e.g., 6061, 6063)"
        ),
        "significance": (
            "The most widely used aluminum alloys (6xxx series) "
            "derive their strength from Mg2Si-related precipitates. "
            "These alloys are used in extrusions, window frames, "
            "bicycle frames, and automotive structures."
        ),
    },
    "MGZN2": {
        "name": "Eta Phase (MgZn2)",
        "crystal": "Hexagonal Laves phase (C14)",
        "description": (
            "An intermetallic compound of magnesium and zinc. It is "
            "the primary strengthening precipitate in 7xxx series "
            "aluminum alloys."
        ),
        "found_in": (
            "7xxx series aluminum alloys (e.g., 7075, 7050)"
        ),
        "significance": (
            "7xxx alloys are the strongest aluminum alloys, used in "
            "aircraft structures. Their strength comes from MgZn2 "
            "and related precipitates. However, they are susceptible "
            "to stress corrosion cracking."
        ),
    },
    "MG17AL12": {
        "name": "Beta Phase (Mg17Al12)",
        "crystal": "Complex cubic structure (A12 type)",
        "description": (
            "An intermetallic compound found in magnesium-aluminum "
            "alloys. It forms at grain boundaries and can affect "
            "both strength and corrosion behavior."
        ),
        "found_in": (
            "Mg-Al alloys (AZ series: AZ31, AZ91)"
        ),
        "significance": (
            "This phase plays a dual role: it can strengthen the "
            "alloy through precipitation but also accelerate "
            "corrosion if present as a continuous network at grain "
            "boundaries."
        ),
    },
    "AL3NI": {
        "name": "Al3Ni",
        "crystal": "Orthorhombic (D011 structure)",
        "description": (
            "An aluminum-nickel intermetallic compound that forms in "
            "Al-Ni alloys."
        ),
        "found_in": (
            "Al-Ni alloy system, some specialized aluminum alloys"
        ),
        "significance": (
            "Al-Ni intermetallics are studied for high-temperature "
            "applications. NiAl and Ni3Al (the nickel-rich side) are "
            "critical in superalloy technology."
        ),
    },
    "LAVES": {
        "name": "Laves Phase",
        "crystal": (
            "Complex structure with specific size-ratio requirements"
        ),
        "description": (
            "A family of intermetallic phases where atoms of "
            "different sizes pack together efficiently. The ideal "
            "atomic size ratio is about 1.225."
        ),
        "found_in": (
            "Many alloy systems; common in steels, superalloys, and "
            "refractory alloys"
        ),
        "significance": (
            "Laves phases can be beneficial (hydrogen storage "
            "materials) or detrimental (embrittlement of steels and "
            "superalloys). They are among the most common "
            "intermetallic phases."
        ),
    },
    "CHI": {
        "name": "Chi Phase",
        "crystal": "BCC-related complex structure (alpha-Mn type)",
        "description": (
            "An intermetallic phase similar to sigma but with a "
            "different crystal structure. Often found alongside sigma."
        ),
        "found_in": "Stainless steels, Fe-Cr-Mo systems",
        "significance": (
            "Like sigma, chi phase is detrimental to mechanical "
            "properties and corrosion resistance in stainless steels."
        ),
    },
    "MU": {
        "name": "Mu Phase",
        "crystal": "Rhombohedral structure (D85 type)",
        "description": (
            "A topologically close-packed phase that can form in "
            "superalloys and some steels at high temperatures."
        ),
        "found_in": (
            "Nickel superalloys, Co-based alloys, some stainless "
            "steels"
        ),
        "significance": (
            "Mu phase is detrimental to the creep strength of "
            "superalloys. Alloy designers use CALPHAD calculations "
            "to ensure compositions avoid the mu phase stability "
            "region."
        ),
    },
    "NI3AL": {
        "name": "Gamma Prime (Ni3Al)",
        "crystal": "Ordered FCC (L12 structure)",
        "description": (
            "An ordered intermetallic with the remarkable property "
            "of getting STRONGER as temperature increases (up to a "
            "point). This anomalous yield strength behavior is unique."
        ),
        "found_in": (
            "Nickel-based superalloys, Inconel, Waspaloy, Rene alloys"
        ),
        "significance": (
            "Gamma prime is the secret weapon of superalloys. It "
            "provides extraordinary high-temperature strength, "
            "enabling jet engines to operate at higher temperatures "
            "and greater efficiency."
        ),
    },
    "NI3TI": {
        "name": "Eta Phase (Ni3Ti)",
        "crystal": "Hexagonal ordered structure (D024)",
        "description": (
            "A nickel-titanium intermetallic that can form in nickel "
            "superalloys, sometimes competing with gamma prime."
        ),
        "found_in": (
            "Some nickel superalloys, maraging steels"
        ),
        "significance": (
            "In small amounts, eta phase can contribute to "
            "strengthening. In excess, plate-like eta can reduce "
            "ductility and toughness."
        ),
    },
    "DELTA": {
        "name": "Delta Phase (Ni3Nb)",
        "crystal": "Orthorhombic (D0a structure)",
        "description": (
            "A nickel-niobium intermetallic found in Inconel 718 "
            "and similar alloys."
        ),
        "found_in": "Inconel 718, some nickel superalloys",
        "significance": (
            "Delta phase is used to control grain size during "
            "forging of Inconel 718. It pins grain boundaries, "
            "preventing grain growth during hot working."
        ),
    },
}


# ---------------------------------------------------------------------------
# 6. RESULT_TEMPLATES -- templates for plain-English result summaries
# ---------------------------------------------------------------------------

RESULT_TEMPLATES: dict[str, str] = {
    "equilibrium_summary": (
        "At {temp}, your {alloy_name} alloy contains "
        "{phase_descriptions}. {state_description}"
    ),
    "phase_description": (
        "{pct:.0f}% {phase_name} ({explanation})"
    ),
    "fully_solid": (
        "The alloy is completely solid -- all atoms are locked in "
        "crystal structures."
    ),
    "fully_liquid": (
        "The alloy is completely molten -- all atoms are moving "
        "freely."
    ),
    "partially_melted": (
        "The alloy is partially melted -- some crystals remain while "
        "the rest has turned to liquid. This is called the 'mushy "
        "zone' and is important for casting and welding."
    ),
    "stepping_summary": (
        "As temperature increases from {t_min} to {t_max}:\n"
        "{phase_story}"
    ),
    "phase_appears": (
        "  - At {temp}, {phase_name} appears ({explanation})"
    ),
    "phase_disappears": (
        "  - At {temp}, {phase_name} disappears"
    ),
    "melting_begins": (
        "  - At {temp}, melting begins (solidus temperature)"
    ),
    "melting_complete": (
        "  - At {temp}, the alloy is fully liquid (liquidus "
        "temperature)"
    ),
    "scheil_summary": (
        "During solidification from {start_t}:\n"
        "{solidification_story}\n\n"
        "{eutectic_note}"
    ),
    "scheil_first_solid": (
        "  - Solidification begins at {temp} with {phase_name} "
        "crystals forming from the liquid."
    ),
    "scheil_new_phase": (
        "  - At {temp}, {phase_name} starts forming alongside the "
        "existing solid phases."
    ),
    "scheil_eutectic": (
        "The last {pct:.1f}% of liquid solidifies as a eutectic "
        "mixture at {temp}. This is common in casting -- the "
        "eutectic forms in the spaces between the earlier crystals."
    ),
    "scheil_no_eutectic": (
        "Solidification completed without a eutectic reaction. The "
        "alloy freezes progressively with the last liquid "
        "disappearing at {temp}."
    ),
    "driving_force_summary": (
        "At {temp} with {alloy_name}:\n"
        "{force_descriptions}\n\n"
        "{warning}"
    ),
    "driving_force_stable": (
        "  - {phase_name}: STABLE (present in equilibrium)"
    ),
    "driving_force_close": (
        "  - {phase_name}: Driving force = {force:.0f} J/mol "
        "(close to forming -- could appear during processing)"
    ),
    "driving_force_far": (
        "  - {phase_name}: Driving force = {force:.0f} J/mol "
        "(unlikely to form at this condition)"
    ),
    "t0_summary": (
        "The T0 temperature between {phase1} and {phase2} at "
        "{composition}:\n"
        "  T0 = {t0_temp}\n\n"
        "{interpretation}"
    ),
    "t0_interpretation_steel": (
        "For steel, this means diffusionless transformation from "
        "{phase1} to {phase2} is thermodynamically possible below "
        "{t0_temp}. The actual martensite start temperature (Ms) "
        "will be below T0 because additional energy is needed to "
        "form the strained martensite structure."
    ),
    "volume_summary": (
        "At {temp}, {alloy_name} has:\n"
        "  Molar volume: {volume} cm3/mol\n"
        "  Density: {density} g/cm3\n\n"
        "{comparison}"
    ),
}


# ---------------------------------------------------------------------------
# 7. LEARNING_MODE_CONFIG -- tab visibility and naming for learning mode
# ---------------------------------------------------------------------------

LEARNING_MODE_CONFIG: dict[str, Any] = {
    "visible_tabs": [
        "Database",
        "Phase Diagram",
        "Equilibrium",
        "Stepping",
        "Scheil",
    ],
    "hidden_tabs": [
        "Thermo Props",
        "Phase Calc",
        "Driving Force",
        "T-Zero",
        "Volume",
    ],
    "renamed_tabs": {
        "Stepping": "Melting Simulator",
        "Scheil": "Casting Simulator",
        "Equilibrium": "Alloy Analyzer",
    },
    "original_tabs": {
        "Melting Simulator": "Stepping",
        "Casting Simulator": "Scheil",
        "Alloy Analyzer": "Equilibrium",
    },
    "tab_order": [
        "Database",
        "Phase Diagram",
        "Alloy Analyzer",
        "Melting Simulator",
        "Casting Simulator",
    ],
    "show_what_is_this": True,
    "show_did_you_know": True,
    "show_glossary_links": True,
    "auto_select_common_phases": True,
    "simplified_error_messages": True,
}


# ---------------------------------------------------------------------------
# Helper functions for accessing content programmatically
# ---------------------------------------------------------------------------

def get_tab_info(tab_key: str) -> dict[str, Any] | None:
    """Return the educational info dict for a given tab, or None."""
    return TAB_INFO.get(tab_key)


def get_tooltip(widget_key: str) -> str:
    """Return the tooltip text for a given widget key, or a fallback."""
    return TOOLTIPS.get(widget_key, "")


def get_glossary_entry(term: str) -> dict[str, Any] | None:
    """Return the glossary entry for a term (case-insensitive lookup)."""
    if term in GLOSSARY:
        return GLOSSARY[term]
    term_lower = term.lower()
    for key, value in GLOSSARY.items():
        if key.lower() == term_lower:
            return value
    return None


def get_phase_explanation(phase_name: str) -> dict[str, str] | None:
    """Return the explanation dict for a phase name, or None.

    Tries exact match first, then common prefixes (e.g., FCC_A1 matches
    a query of "FCC_A1#2").
    """
    if phase_name in PHASE_EXPLANATIONS:
        return PHASE_EXPLANATIONS[phase_name]
    # Strip database suffixes like "#2" or "_AUTOGENERATED"
    base = phase_name.split("#")[0].split("_AUTOGENERATED")[0]
    if base in PHASE_EXPLANATIONS:
        return PHASE_EXPLANATIONS[base]
    # Try matching just the structure prefix (e.g., "FCC" from "FCC_A1")
    prefix = phase_name.split("_")[0]
    for key in PHASE_EXPLANATIONS:
        if key.startswith(prefix):
            return PHASE_EXPLANATIONS[key]
    return None


def get_random_fact() -> str:
    """Return a random 'Did You Know?' fact."""
    import random
    return random.choice(DID_YOU_KNOW)


def format_result_summary(template_key: str, **kwargs: Any) -> str:
    """Format a result template with the given keyword arguments.

    Missing keys are replaced with '???' to avoid crashing on incomplete
    data.
    """
    template = RESULT_TEMPLATES.get(template_key, "")
    if not template:
        return ""
    try:
        return template.format(**kwargs)
    except KeyError:
        import string
        field_names = [
            fname
            for _, fname, _, _ in string.Formatter().parse(template)
            if fname is not None
        ]
        filled = {name: kwargs.get(name, "???") for name in field_names}
        return template.format(**filled)


def search_glossary(query: str) -> list[tuple[str, dict[str, Any]]]:
    """Search the glossary for terms matching the query string.

    Returns a list of (term, entry) tuples sorted by relevance.
    Matches against term names and definitions.
    """
    query_lower = query.lower()
    results: list[tuple[int, str, dict[str, Any]]] = []

    for term, entry in GLOSSARY.items():
        term_lower = term.lower()
        definition_lower = entry["definition"].lower()

        if query_lower == term_lower:
            results.append((0, term, entry))
        elif query_lower in term_lower:
            results.append((1, term, entry))
        elif query_lower in definition_lower:
            results.append((2, term, entry))

    results.sort(key=lambda x: (x[0], x[1]))
    return [(term, entry) for _, term, entry in results]
