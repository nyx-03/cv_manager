# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

# --- Data files bundled inside the app ---
# QSS theme and built-in Jinja2 templates must be available at runtime.
# Paths are relative to the project root (where this .spec file lives).
datas = [
    ("ui/style.qss", "ui"),
    # Bundle the whole templates folder (PyInstaller will include its contents)
    ("data/templates", "data/templates"),
    # Optional: bundle a seed SQLite DB if you ship one (copied on first run)
    ("data/cv_manager.sqlite", "data"),
]

# --- Validate/sanitize datas (must be sequence of 2- or 3-tuples) ---
_sanitized_datas = []
for _item in datas:
    if isinstance(_item, (list, tuple)) and len(_item) in (2, 3):
        # Ensure src/dest are strings (PyInstaller expects paths as strings)
        if len(_item) == 2:
            _src, _dst = _item
            _sanitized_datas.append((str(_src), str(_dst)))
        else:
            _src, _dst, _typecode = _item
            _sanitized_datas.append((str(_src), str(_dst), _typecode))
    else:
        raise SystemExit(f"Invalid datas entry in spec: {_item!r} (expected 2- or 3-tuple)")

datas = _sanitized_datas

# --- Hidden imports ---
# Some packages are imported dynamically and can be missed by analysis.
hiddenimports = []
hiddenimports += collect_submodules("jinja2")
hiddenimports += collect_submodules("bs4")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CV Manager',
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='CV Manager',
)

app = BUNDLE(
    coll,
    name='CV Manager.app',
    icon=None,
    bundle_identifier='com.nyx03.cvmanager',
)
