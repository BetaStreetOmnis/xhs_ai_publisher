from __future__ import annotations

from typing import List, Optional

from .browser_manager import BrowserManager
from .write_xiaohongshu import XiaohongshuPoster


class ContentPublisher:
    """兼容层：为 V2 调用方复用现有发布实现。"""

    def __init__(self):
        self.browser_manager: Optional[BrowserManager] = None
        self.poster = XiaohongshuPoster()

    async def initialize(self, browser_manager: BrowserManager) -> None:
        self.browser_manager = browser_manager
        self.poster.attach_browser_session(
            playwright=getattr(browser_manager, "playwright", None),
            browser=getattr(browser_manager, "browser", None),
            context=getattr(browser_manager, "context", None),
            page=getattr(browser_manager, "page", None),
        )

    async def publish_article(
        self,
        title: str,
        content: str,
        images: Optional[List[str]] = None,
        *,
        auto_publish: bool = False,
    ) -> bool:
        return await self.poster.post_article(
            title=title,
            content=content,
            images=images,
            auto_publish=auto_publish,
        )

    async def cleanup(self) -> None:
        await self.poster.cleanup()
