# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for CalcPHAD — Windows portable executable."""

import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect hidden imports for scientific libraries with compiled extensions
hiddenimports = (
    collect_submodules("pycalphad")
    + collect_submodules("scheil")
    + collect_submodules("symengine")
    + [
        "matplotlib.backends.backend_qtagg",
        "matplotlib.backends.backend_agg",
    ]
)

# Collect data files needed by pycalphad at runtime
datas = collect_data_files("pycalphad") + collect_data_files("scheil")

# Bundled application resources
datas += [
    ("COST507.tdb", "."),
    ("calphad.png", "."),
    ("calphad_64.png", "."),
    ("calphad_128.png", "."),
    ("gui", "gui"),
    ("core", "core"),
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CalcPHAD",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # --windowed (no console window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="calphad.ico",     # Windows taskbar / explorer icon
)
