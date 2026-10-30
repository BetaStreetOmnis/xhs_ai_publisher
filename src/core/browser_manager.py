import asyncio
import os
import sys
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from typing import Optional, Dict, Any

from .logger import logger
from .config import config


class BrowserManager:
    """浏览器管理器 - 使用上下文管理器确保资源正确释放"""
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._initialized = False
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def initialize(self) -> None:
        """初始化浏览器"""
        if self._initialized:
            return
        
        try:
            logger.info("开始初始化浏览器...")
            self.playwright = await async_playwright().start()
            
            launch_args = self._get_launch_args()
            chromium_path = self._get_chromium_path()
            
            if chromium_path:
                launch_args['executable_path'] = chromium_path
            
            self.browser = await self.playwright.chromium.launch(**launch_args)
            self.context = await self.browser.new_context(
                permissions=['geolocation']
            )
            self.page = await self.context.new_page()
            
            # 注入反检测脚本
            
            self._initialized = True
            logger.info("浏览器初始化成功")
            
        except Exception as e:
            logger.error(f"浏览器初始化失败: {str(e)}", exc_info=True)
            await self.close()
            raise
    
    def _get_launch_args(self) -> Dict[str, Any]:
        """获取浏览器启动参数"""
        return {
            'headless': bool(config.browser.headless),
            'args': [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-extensions',
                '--disable-infobars',
                '--start-maximized',
                '--ignore-certificate-errors',
                '--ignore-ssl-errors'
            ]
        }
    
    def _get_chromium_path(self) -> Optional[str]:
        """获取Chromium路径"""
        if not getattr(sys, 'frozen', False):
            return None
        
        executable_dir = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
        
        if sys.platform == 'darwin':
            return self._get_macos_chromium_path(executable_dir)
        else:
            return self._get_windows_chromium_path(executable_dir)
    
    def _get_macos_chromium_path(self, executable_dir: str) -> str:
        """获取macOS Chromium路径"""
        if 'XhsAi' in executable_dir:
            browser_path = os.path.join(executable_dir, "ms-playwright")
        else:
            browser_path = os.path.join(executable_dir, "Contents", "MacOS", "ms-playwright")
        
        return os.path.join(browser_path, "chromium-1161/chrome-mac/Chromium.app/Contents/MacOS/Chromium")
    
    def _get_windows_chromium_path(self, executable_dir: str) -> str:
        """获取Windows Chromium路径"""
        browser_path = os.path.join(executable_dir, "ms-playwright")
        chromium_path = os.path.join(browser_path, "chrome-win", "chrome.exe")
        
        if os.path.exists(chromium_path):
            os.chmod(chromium_path, 0o755)
            return chromium_path
        
        raise FileNotFoundError(f"浏览器文件不存在: {chromium_path}")
    
    async def close(self) -> None:
        """关闭浏览器资源"""
        try:
            if self.context:
                await self.context.close()
                logger.debug("浏览器上下文已关闭")
            
            if self.browser:
                await self.browser.close()
                logger.debug("浏览器已关闭")
            
            if self.playwright:
                await self.playwright.stop()
                logger.debug("Playwright已停止")
                
        except Exception as e:
            logger.error(f"关闭浏览器时出错: {str(e)}", exc_info=True)
        finally:
            self.playwright = None
            self.browser = None
            self.context = None
            self.page = None
            self._initialized = False

    async def cleanup(self) -> None:
        await self.close()
    
    async def ensure_initialized(self) -> None:
        """确保浏览器已初始化"""
        if not self._initialized:
            await self.initialize()


@asynccontextmanager
async def browser_session():
    """浏览器会话上下文管理器"""
    manager = BrowserManager()
    try:
        await manager.initialize()
        yield manager
    finally:
        await manager.close() 
