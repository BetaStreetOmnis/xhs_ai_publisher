import asyncio
import os
import sys
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from typing import Optional, Dict, Any

from .logger import logger
from .services.user_service import user_service
from .services.proxy_service import proxy_service
from .services.fingerprint_service import fingerprint_service


class EnhancedBrowserManager:
    """增强的浏览器管理器 - 支持多用户、代理和浏览器指纹"""
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._initialized = False
        self.current_user = None
        self.current_proxy = None
        self.current_fingerprint = None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def initialize(self, user_id: Optional[int] = None) -> None:
        """初始化浏览器"""
        if self._initialized:
            return
        
        try:
            logger.info("开始初始化增强浏览器管理器...")
            
            # 获取当前用户
            if user_id:
                self.current_user = user_service.get_user_by_id(user_id)
            else:
                self.current_user = user_service.get_current_user()
            
            if not self.current_user:
                raise ValueError("未找到当前用户，请先登录或切换用户")
            
            logger.info(f"当前用户: {self.current_user.username} ({self.current_user.display_name})")
            
            # 获取用户的代理配置
            self.current_proxy = proxy_service.get_default_proxy_config(self.current_user.id)
            if self.current_proxy:
                logger.info(f"使用代理: {self.current_proxy.name} ({self.current_proxy.host}:{self.current_proxy.port})")
            
            # 获取用户的浏览器指纹配置
            self.current_fingerprint = fingerprint_service.get_default_fingerprint(self.current_user.id)
            if self.current_fingerprint:
                logger.info(f"使用浏览器指纹: {self.current_fingerprint.name}")
            
            # 启动Playwright
            self.playwright = await async_playwright().start()
            
            # 获取启动参数
            launch_args = self._get_launch_args()
            chromium_path = self._get_chromium_path()
            
            if chromium_path:
                launch_args['executable_path'] = chromium_path
            
            # 启动浏览器
            self.browser = await self.playwright.chromium.launch(**launch_args)
            
            # 创建浏览器上下文（应用代理和指纹配置）
            context_options = self._get_context_options()
            self.context = await self.browser.new_context(**context_options)
            
            # 创建页面
            self.page = await self.context.new_page()
            
            
            # 恢复用户的登录状态
            await self._restore_user_session()
            
            self._initialized = True
            logger.info("增强浏览器管理器初始化成功")
            
        except Exception as e:
            logger.error(f"增强浏览器管理器初始化失败: {str(e)}", exc_info=True)
            await self.close()
            raise
    
    def _get_launch_args(self) -> Dict[str, Any]:
        """获取浏览器启动参数"""
        args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-extensions',
            '--disable-infobars',
            '--start-maximized',
            '--ignore-certificate-errors',
            '--ignore-ssl-errors'
        ]
        
        # 如果有代理配置，添加代理参数
        if self.current_proxy:
            proxy_url = self.current_proxy.get_proxy_url()
            args.append(f'--proxy-server={proxy_url}')
        
        return {
            'headless': False,
            'args': args
        }
    
    def _get_context_options(self) -> Dict[str, Any]:
        """获取浏览器上下文选项"""
        options = {
            'permissions': ['geolocation']
        }
        
        # 应用浏览器指纹配置
        if self.current_fingerprint:
            fingerprint_options = self.current_fingerprint.get_browser_context_options()
            options.update(fingerprint_options)
        
        # 应用代理配置（如果Playwright支持上下文级代理）
        if self.current_proxy:
            proxy_dict = self.current_proxy.get_proxy_dict()
            # 注意：Playwright的代理配置通常在启动时设置，这里主要用于记录
            logger.info(f"代理配置: {proxy_dict}")
        
        return options
    
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
            # 保存用户会话
            await self.save_user_session()
            
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
    
    async def ensure_initialized(self) -> None:
        """确保浏览器已初始化"""
        if not self._initialized:
            await self.initialize()
    
    def get_current_config(self) -> Dict[str, Any]:
        """获取当前配置信息"""
        return {
            'user': {
                'id': self.current_user.id if self.current_user else None,
                'username': self.current_user.username if self.current_user else None,
                'display_name': self.current_user.display_name if self.current_user else None,
            } if self.current_user else None,
            'proxy': {
                'id': self.current_proxy.id if self.current_proxy else None,
                'name': self.current_proxy.name if self.current_proxy else None,
                'host': self.current_proxy.host if self.current_proxy else None,
                'port': self.current_proxy.port if self.current_proxy else None,
            } if self.current_proxy else None,
            'fingerprint': {
                'id': self.current_fingerprint.id if self.current_fingerprint else None,
                'name': self.current_fingerprint.name if self.current_fingerprint else None,
                'user_agent': self.current_fingerprint.user_agent if self.current_fingerprint else None,
                'viewport': f"{self.current_fingerprint.viewport_width}x{self.current_fingerprint.viewport_height}" if self.current_fingerprint else None,
            } if self.current_fingerprint else None,
        }


@asynccontextmanager
async def enhanced_browser_session(user_id: Optional[int] = None):
    """增强浏览器会话上下文管理器"""
    manager = EnhancedBrowserManager()
    try:
        await manager.initialize(user_id)
        yield manager
    finally:
        await manager.close() 