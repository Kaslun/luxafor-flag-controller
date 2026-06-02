# PyInstaller spec for Beacon — single windowed one-file exe.
#
# Bundles the engine package, the built React UI (ui/dist), the tray icon,
# and hidapi's native DLL (PyInstaller's hook collects it on Windows).
# Build with:  pyinstaller packaging/beacon.spec   (run from repo root)

import os
from PyInstaller.utils.hooks import collect_dynamic_libs

block_cipher = None

ROOT = os.path.abspath(os.getcwd())
UI_DIST = os.path.join(ROOT, "ui", "dist")
ICON = os.path.join(ROOT, "packaging", "icon.ico")

datas = []
if os.path.isdir(UI_DIST):
    # ship the built UI under ui/dist inside the bundle; app.py resolves it
    # via sys._MEIPASS at runtime.
    datas.append((UI_DIST, os.path.join("ui", "dist")))

# hidapi native libs
binaries = collect_dynamic_libs("hid") + collect_dynamic_libs("hidapi")

a = Analysis(
    ["..\\engine\\__main__.py"],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=["engine", "uvicorn.logging", "uvicorn.loops.auto",
                   "uvicorn.protocols.http.auto", "uvicorn.protocols.websockets.auto",
                   "uvicorn.lifespan.on"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="beacon",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,  # windowed — no console flash
    icon=ICON if os.path.exists(ICON) else None,
)
