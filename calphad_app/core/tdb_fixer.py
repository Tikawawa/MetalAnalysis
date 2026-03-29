"""TDB file fixer for common COST507-format issues."""

import re
from pathlib import Path


def fix_tdb_content(raw_bytes: bytes) -> str:
    """Fix common TDB formatting issues and return cleaned text.

    Handles:
    - Non-ASCII characters (read as latin-1, strip chars > 127)
    - Scientific notation: "8.89059+01" -> "8.89059E+01" (before whitespace)
    - "N REF: 0" suffixes on PARAMETER lines
    - Duplicate FUNCTION entries (keep first occurrence)
    """
    text = raw_bytes.decode("latin-1")

    # Strip non-ASCII characters (code points > 127)
    text = "".join(ch if ord(ch) < 128 else "" for ch in text)

    # Fix scientific notation: number followed by +/- and digits before whitespace
    # Matches patterns like "1.234+05" or "5.678-03" that lack the 'E'
    # Only fix when the exponent part is followed by whitespace, comma, semicolon, or EOL
    text = re.sub(
        r"(\d\.?\d*)([\+\-])(\d{1,3})(\s|;|,|$)",
        r"\1E\2\3\4",
        text,
    )

    # Strip "N REF: 0" (and variants like "N REF:0", "N  REF: 0") from PARAMETER lines
    text = re.sub(r"\s+N\s+REF:\s*\d+", "", text)

    # Remove duplicate FUNCTION entries (keep first occurrence)
    text = _remove_duplicate_functions(text)

    return text


def _remove_duplicate_functions(text: str) -> str:
    """Remove duplicate FUNCTION definitions, keeping the first occurrence."""
    lines = text.split("\n")
    seen_functions: set[str] = set()
    result_lines: list[str] = []
    skip_until_semicolon = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if skip_until_semicolon:
            if ";" in stripped:
                skip_until_semicolon = False
            i += 1
            continue

        # Check if this line starts a FUNCTION definition
        match = re.match(r"^\s*FUNCTION\s+(\S+)", stripped, re.IGNORECASE)
        if match:
            func_name = match.group(1).upper()
            if func_name in seen_functions:
                # Skip this duplicate function definition
                if ";" not in stripped:
                    skip_until_semicolon = True
                i += 1
                continue
            else:
                seen_functions.add(func_name)

        result_lines.append(line)
        i += 1

    return "\n".join(result_lines)


def fix_tdb_file(input_path: str, output_path: str | None = None) -> str:
    """Fix a TDB file and write the corrected version.

    Args:
        input_path: Path to the original TDB file.
        output_path: Where to write fixed file. If None, writes to
                     '<stem>_fixed.tdb' next to the original.

    Returns:
        Path to the fixed TDB file.
    """
    src = Path(input_path)
    raw = src.read_bytes()
    fixed = fix_tdb_content(raw)

    if output_path is None:
        dst = src.with_stem(src.stem + "_fixed")
    else:
        dst = Path(output_path)

    dst.write_text(fixed, encoding="utf-8")
    return str(dst)


def extract_elements(tdb_text: str) -> list[str]:
    """Extract element names from TDB text."""
    elements = []
    for line in tdb_text.split("\n"):
        stripped = line.strip().upper()
        if stripped.startswith("ELEMENT"):
            parts = stripped.split()
            if len(parts) >= 2:
                el = parts[1]
                if el not in ("/-", "VA", "%", "*", "/", "") and el not in elements:
                    elements.append(el)
    return elements


def extract_phases(tdb_text: str) -> list[str]:
    """Extract phase names from TDB text."""
    phases = []
    for line in tdb_text.split("\n"):
        stripped = line.strip().upper()
        if stripped.startswith("PHASE"):
            parts = stripped.split()
            if len(parts) >= 2:
                phase = parts[1].rstrip(",:%")
                if phase not in phases:
                    phases.append(phase)
    return phases
