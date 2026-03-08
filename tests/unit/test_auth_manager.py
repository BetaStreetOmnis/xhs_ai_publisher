import pytest

from src.core.auth_manager import AuthManager


class DummyPage:
    def __init__(self, url: str, marker_result: bool = False):
        self.url = url
        self.marker_result = marker_result
        self.goto_calls = []

    async def goto(self, url, wait_until=None):
        self.goto_calls.append((url, wait_until))
        self.url = url

    async def evaluate(self, script):
        return self.marker_result


class DummyBrowserManager:
    def __init__(self, page):
        self.page = page


class DummyPoster:
    def __init__(self, probe_result: bool):
        self.context = object()
        self.probe_result = probe_result

    async def _is_creator_logged_in(self):
        return self.probe_result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_is_logged_in_falls_back_to_workspace_page_when_probe_returns_false():
    manager = AuthManager()
    page = DummyPage("https://creator.xiaohongshu.com/new/home", marker_result=True)
    manager.browser_manager = DummyBrowserManager(page)
    manager.poster = DummyPoster(probe_result=False)

    assert await manager.is_logged_in() is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_is_logged_in_returns_false_on_login_page():
    manager = AuthManager()
    page = DummyPage("https://creator.xiaohongshu.com/login", marker_result=True)
    manager.browser_manager = DummyBrowserManager(page)
    manager.poster = DummyPoster(probe_result=False)

    assert await manager.is_logged_in() is False
