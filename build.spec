# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_all

# 获取项目根目录
project_root = os.path.dirname(os.path.abspath(__file__))

# 收集PyQt5数据文件
datas = []
binaries = []
hiddenimports = []

# 收集PyQt5相关文件
pyqt5_data = collect_all('PyQt5')
datas.extend(pyqt5_data[0])
binaries.extend(pyqt5_data[1])
hiddenimports.extend(pyqt5_data[2])

# 添加项目资源文件
resources = [
    ('templates', 'templates'),
    ('fonts', 'fonts'),
    ('assets', 'assets'),
    ('build/icon.png', 'build/'),
]

for src, dst in resources:
    src_path = os.path.join(project_root, src)
    if os.path.exists(src_path):
        if os.path.isfile(src_path):
            datas.append((src_path, dst))
        else:
            for root, dirs, files in os.walk(src_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, project_root)
                    datas.append((file_path, os.path.dirname(rel_path)))

# 添加配置文件路径
config_path = os.path.join(os.path.expanduser('~'), '.xhs_system')
datas.append((config_path, '.xhs_system'))

# 隐藏导入的模块
hiddenimports.extend([
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.QtNetwork',
    'PyQt5.QtWebEngineWidgets',
    'src.core.pages.simple_backend_config',
    'src.core.scheduler.schedule_manager',
    'src.core.database_manager',
    'src.logger.logger',
    'src.config.config',
    'src.core.browser',
    'src.core.pages.home',
    'src.core.pages.setting',
    'src.core.pages.tools',
    'src.core.pages.browser_environment_page',
    'playwright.sync_api',
    'requests',
    'urllib3',
    'json',
    'sqlite3',
    'datetime',
    'os',
    'sys',
    'time',
    'threading',
    'queue',
    'logging',
    'traceback',
    'signal',
    'cryptography',
    'base64',
    'hashlib',
    're',
])

# 主程序配置
a = Analysis(
    ['main.py'],
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# 清理不必要的模块
excluded_modules = [
    'tkinter',
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'PIL',
    'pillow',
]

for module in excluded_modules:
    if module in a.pure:
        a.pure.remove(module)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

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
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='build/icon.png',
)

# 创建应用程序包（macOS专用）
app = BUNDLE(
    exe,
    name='小红书发文助手.app',
    icon='build/icon.png',
    bundle_identifier='com.xhs.poster',
    version='1.0.0',
)