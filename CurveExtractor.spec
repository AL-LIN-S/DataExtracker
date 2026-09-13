# -*- mode: python ; coding: utf-8 -*-
"""Windows GUI freeze for Curve Extractor 0.2.0.

The frozen window is the same GUI as `python -m curve_extractor`
(curve_extractor.__main__ → curve_extractor.app.main_window.run).

Tesseract is NOT bundled. Axis-tick OCR remains a separate install.
"""

from __future__ import annotations

import os

from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

SPEC_ROOT = os.path.dirname(os.path.abspath(SPEC))


def _try_collect(package: str) -> tuple[list, list, list]:
    try:
        datas, binaries, hidden = collect_all(package)
        return list(datas), list(binaries), list(hidden)
    except Exception:
        try:
            return [], list(collect_dynamic_libs(package)), [package]
        except Exception:
            return [], [], [package]


datas: list = []
binaries: list = []
hiddenimports: list = [
    "curve_extractor",
    "curve_extractor.app",
    "curve_extractor.app.main_window",
    "curve_extractor.app.image_io",
    "curve_extractor.app.image_view",
    "curve_extractor.core",
    "curve_extractor.core.auto_calibration",
    "curve_extractor.core.calibration",
    "curve_extractor.core.color_cluster",
    "curve_extractor.core.extraction",
    "curve_extractor.core.export",
    "cv2",
    "numpy",
    "pandas",
    "PIL",
    "pytesseract",
    "PySide6",
    "shiboken6",
]

# collect-all PySide6; also pull cv2 / numpy / pandas binaries that Analysis
# often misses when those packages use lazy or binary-only imports.
for package in ("PySide6", "shiboken6", "cv2", "numpy", "pandas", "PIL", "pytesseract"):
    pkg_datas, pkg_binaries, pkg_hidden = _try_collect(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

a = Analysis(
    [os.path.join(SPEC_ROOT, "scripts", "gui_entry.py")],
    pathex=[SPEC_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "scipy", "tkinter", "IPython", "pytest"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CurveExtractor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory="_internal",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CurveExtractor",
)
