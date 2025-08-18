# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('src', 'src'), ('init_db.py', '.'), ('fix_database.py', '.'), ('check_db.py', '.')],
    hiddenimports=['PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'sqlalchemy', 'sqlalchemy.orm', 'sqlalchemy.sql', 'sqlalchemy.pool', 'sqlalchemy.engine', 'sqlalchemy.event', 'sqlalchemy.ext', 'sqlalchemy.dialects.sqlite', 'sqlite3', 'json', 'threading', 'asyncio', 'concurrent.futures', 'requests', 'playwright', 'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont', 'openai', 'dotenv'],
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
    name='小红书发文助手',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
