import importlib
import logging
import os
from pathlib import Path
import subprocess
import sys
import threading
from types import ModuleType, SimpleNamespace
import pytest


def test_release_starts_without_accessing_a_desktop_directory(tmp_path):
    env = {**os.environ, 'XHS_DATA_DIR': str(tmp_path / 'data'), 'QT_QPA_PLATFORM': 'offscreen'}
    script = '''
import os, runpy, sys
expanduser = os.path.expanduser
def reject_desktop(path):
    if 'Desktop' in os.fspath(path):
        raise RuntimeError('Startup must not require a Desktop directory')
    return expanduser(path)
os.path.expanduser = reject_desktop
sys.argv = ['main.py', '--smoke-test']
runpy.run_path('main.py', run_name='__main__')
'''
    result = subprocess.run([sys.executable, '-c', script], env=env,
                            cwd=Path(__file__).resolve().parents[2],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert '"status": "ok"' in result.stdout
    assert (tmp_path / 'data/logs/xhsai_error.log').is_file()


@pytest.fixture(scope='session')
def mac_application():
    from PyQt5.QtCore import QCoreApplication
    application=QCoreApplication.instance() or QCoreApplication([])
    yield application


def test_browser_download_verification_uses_existing_context(monkeypatch, tmp_path, mac_application):
    monkeypatch.setenv('XHS_DATA_DIR',str(tmp_path))
    monkeypatch.setattr(logging,'basicConfig',lambda **kwargs:None)
    keys=ModuleType('src.core.ai_integration.api_key_manager')
    keys.api_key_manager=SimpleNamespace()
    monkeypatch.setitem(sys.modules,keys.__name__,keys)
    for name in ('src.core.logger','core.logger'):
        module=ModuleType(name)
        module.logger=logging.getLogger('mac-startup-test')
        monkeypatch.setitem(sys.modules,name,module)
    main=importlib.import_module('main')
    import playwright.sync_api
    entries=[]
    launches=[]
    events=[]
    downloads=[]

    def launch(**kwargs):
        launches.append(kwargs)
        if len(launches)<4: raise RuntimeError("Executable doesn't exist")
        return SimpleNamespace(close=lambda:None)

    class Context:
        def __enter__(self):
            entries.append(True)
            if len(entries)>1: raise RuntimeError('Nested sync context')
            return SimpleNamespace(chromium=SimpleNamespace(launch=launch))
        def __exit__(self,*args): pass

    monkeypatch.setattr(playwright.sync_api,'sync_playwright',Context)
    monkeypatch.setattr(subprocess,'run',lambda *args,**kwargs: downloads.append(args) or SimpleNamespace(returncode=0))

    class InlineThread:
        def __init__(self,target,**kwargs): self.target=target
        def start(self): self.target()

    monkeypatch.setattr(threading,'Thread',InlineThread)
    logger=SimpleNamespace(info=events.append,error=events.append,success=events.append)
    main.XiaohongshuUI.start_downloader_thread(SimpleNamespace(logger=logger))
    assert len(entries)==1
    assert len(downloads)==1
    assert len(launches)==4
    assert any('Chrome浏览器验证成功' in x for x in events)
    assert not any('下载出错' in x for x in events)
