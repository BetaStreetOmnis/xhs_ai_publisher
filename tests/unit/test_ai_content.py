"""Content-generation dispatch against the current thread API, without network I/O."""
from types import SimpleNamespace

import pytest

from src.core.processor import content


@pytest.mark.parametrize("allow_fallback", [True, False])
def test_unconfigured_model_respects_offline_preview_choice(monkeypatch, allow_fallback):
    monkeypatch.setenv("XHS_ALLOW_FALLBACK", "true" if allow_fallback else "false")
    monkeypatch.setattr(content, "Config", lambda: SimpleNamespace(get_templates_config=lambda: {}))
    button = SimpleNamespace(setText=lambda text: None, setEnabled=lambda enabled: None)
    thread = content.ContentGeneratorThread("这是我提供的原稿。", "项目介绍", "作者", button)
    monkeypatch.setattr(thread, "_try_generate_with_custom_model", lambda: False)
    previews = []
    errors = []
    monkeypatch.setattr(thread, "_use_backup_generator", lambda info_reason: previews.append(info_reason))
    thread.error.connect(errors.append)
    thread.run()
    assert bool(previews) == allow_fallback
    assert bool(errors) != allow_fallback
