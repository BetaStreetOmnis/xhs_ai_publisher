import json

from src.core.config import ConfigManager, WebConfig
from src.version import __version__


def test_upgrading_saved_config_keeps_data_but_updates_runtime_version(tmp_path, monkeypatch):
    monkeypatch.delenv("XHS_DATA_DIR", raising=False)
    monkeypatch.delenv("XHS_APP_DATA_DIR", raising=False)
    saved = tmp_path / "config.json"
    saved.write_text(json.dumps({"app": {"version": "1.0.0", "data_dir": str(tmp_path),
                                         "log_level": "WARNING"}}))
    config = ConfigManager(str(saved))
    assert config.app.version == __version__
    assert config.app.data_dir == str(tmp_path)
    assert config.app.log_level == "WARNING"


def test_web_defaults_do_not_expose_all_network_interfaces():
    assert WebConfig().host == "127.0.0.1"
    assert not WebConfig().debug
    assert not WebConfig().reload
