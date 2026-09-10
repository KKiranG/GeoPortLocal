# PyInstaller specification for the first macOS GeoPortLocal qualification build.

from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all

PROJECT_ROOT = Path.cwd()
PMD_DATAS, PMD_BINARIES, PMD_HIDDEN_IMPORTS = collect_all("pymobiledevice3")

WEB_DATAS = [
    (str(PROJECT_ROOT / "src/geoportlocal/web/templates"), "geoportlocal/web/templates"),
    (str(PROJECT_ROOT / "src/geoportlocal/web/static"), "geoportlocal/web/static"),
]

HIDDEN_IMPORTS = PMD_HIDDEN_IMPORTS + [
    "geoportlocal.device.pymobiledevice",
    "geoportlocal.fuel.project_zero_three",
]

analysis = Analysis(
    [str(PROJECT_ROOT / "src/geoportlocal/__main__.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=PMD_BINARIES,
    datas=WEB_DATAS + PMD_DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="GeoPortLocal",
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

collect = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="GeoPortLocal",
)

if sys.platform == "darwin":
    app = BUNDLE(
        collect,
        name="GeoPortLocal.app",
        icon=None,
        bundle_identifier="io.github.kkirang.geoportlocal",
        info_plist={
            "CFBundleDisplayName": "GeoPortLocal",
            "CFBundleShortVersionString": "0.1.0",
            "CFBundleVersion": "1",
            "NSHighResolutionCapable": True,
        },
    )
