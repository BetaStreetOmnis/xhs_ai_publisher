# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['playwright', 'playwright.sync_api', 'playwright._impl._driver', 'playwright.async_api']
hiddenimports += collect_submodules('src')


a = Analysis(
    ['../main.py'],
    pathex=['..'],
    binaries=[],
    datas=[('/Users/smallshaxiaoche/miniconda3/envs/xhs_publisher/lib/python3.12/site-packages/certifi/cacert.pem', 'certifi'), ('../src', 'src')],
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
    a.binaries,
    a.datas,
    [],
    name='XhsAi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['MyIcon.icns'],
)
app = BUNDLE(
    exe,
    name='XhsAi.app',
    icon='MyIcon.icns',
    bundle_identifier=None,
)
