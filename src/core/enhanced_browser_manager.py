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
            
            # 注入反检测脚本和指纹配置
            await self._inject_stealth_script()
            await self._inject_fingerprint_script()
            
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
    
    async def _inject_stealth_script(self) -> None:
        """注入反检测脚本"""
        stealth_js = """
        (function(){
            // 反检测脚本
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh']
            });
            
            window.chrome = { runtime: {} };
            
            // 移除webdriver属性
            delete navigator.__proto__.webdriver;
            
            // 禁用Service Worker注册以避免错误
            if ('serviceWorker' in navigator) {
                const originalRegister = navigator.serviceWorker.register;
                navigator.serviceWorker.register = function() {
                    return Promise.reject(new Error('Service Worker registration disabled'));
                };
                
                // 也可以完全移除serviceWorker
                Object.defineProperty(navigator, 'serviceWorker', {
                    get: () => undefined
                });
            }
            
            // 捕获并忽略Service Worker相关错误
            window.addEventListener('error', function(e) {
                if (e.message && e.message.includes('serviceWorker')) {
                    e.preventDefault();
                    return false;
                }
            });
            
            // 捕获未处理的Promise拒绝（Service Worker相关）
            window.addEventListener('unhandledrejection', function(e) {
                if (e.reason && e.reason.message && e.reason.message.includes('serviceWorker')) {
                    e.preventDefault();
                    return false;
                }
            });
        })();
        """
        await self.page.add_init_script(stealth_js)
    
    async def _inject_fingerprint_script(self) -> None:
        """注入浏览器指纹脚本"""
        if not self.current_fingerprint:
            return
        
        fingerprint_js = f"""
        (function(){{
            // 修改屏幕分辨率
            Object.defineProperty(screen, 'width', {{
                get: () => {self.current_fingerprint.screen_width}
            }});
            Object.defineProperty(screen, 'height', {{
                get: () => {self.current_fingerprint.screen_height}
            }});
            
            // 修改时区
            const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
            Date.prototype.getTimezoneOffset = function() {{
                return -480; // 北京时间偏移
            }};
            
            // 修改语言
            Object.defineProperty(navigator, 'language', {{
                get: () => '{self.current_fingerprint.locale}'
            }});
            
            // 修改平台
            Object.defineProperty(navigator, 'platform', {{
                get: () => '{self.current_fingerprint.platform}'
            }});
            
            // 修改WebGL信息
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                if (parameter === 37445) {{
                    return '{self.current_fingerprint.webgl_vendor or "Google Inc. (Intel)"}';
                }}
                if (parameter === 37446) {{
                    return '{self.current_fingerprint.webgl_renderer or "ANGLE (Intel, Intel(R) HD Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)"}';
                }}
                return getParameter.call(this, parameter);
            }};
        }})();
        """
        await self.page.add_init_script(fingerprint_js)
    
    async def _restore_user_session(self) -> None:
        """恢复用户的登录会话"""
        if not self.current_user or not self.current_user.is_logged_in:
            return
        
        try:
            cookies = self.current_user.get_login_cookies()
            if cookies:
                await self.context.add_cookies(cookies)
                logger.info("已恢复用户登录会话")
        except Exception as e:
            logger.warning(f"恢复用户会话失败: {str(e)}")
    
    async def save_user_session(self) -> None:
        """保存用户的登录会话"""
        if not self.current_user or not self.context:
            return
        
        try:
            cookies = await self.context.cookies()
            if cookies:
                user_service.update_login_status(
                    self.current_user.id, 
                    True, 
                    cookies
                )
                logger.info("已保存用户登录会话")
        except Exception as e:
            logger.error(f"保存用户会话失败: {str(e)}")
    
    async def switch_user(self, user_id: int) -> None:
        """切换用户"""
        if self.current_user and self.current_user.id == user_id:
            logger.info("用户未发生变化，无需切换")
            return
        
        logger.info(f"切换用户到 ID: {user_id}")
        
        # 保存当前用户会话
        await self.save_user_session()
        
        # 关闭当前浏览器
        await self.close()
        
        # 切换用户
        user_service.switch_user(user_id)
        
        # 重新初始化浏览器
        await self.initialize(user_id)
    
    async def update_proxy_config(self, proxy_id: Optional[int] = None) -> None:
        """更新代理配置"""
        if not self.current_user:
            raise ValueError("未找到当前用户")
        
        if proxy_id:
            new_proxy = proxy_service.get_proxy_config_by_id(proxy_id)
            if not new_proxy or new_proxy.user_id != self.current_user.id:
                raise ValueError("代理配置不存在或不属于当前用户")
        else:
            new_proxy = proxy_service.get_default_proxy_config(self.current_user.id)
        
        if new_proxy != self.current_proxy:
            logger.info(f"更新代理配置: {new_proxy.name if new_proxy else '无代理'}")
            self.current_proxy = new_proxy
            
            # 重新初始化浏览器以应用新的代理配置
            await self.close()
            await self.initialize()
    
    async def update_fingerprint_config(self, fingerprint_id: Optional[int] = None) -> None:
        """更新浏览器指纹配置"""
        if not self.current_user:
            raise ValueError("未找到当前用户")
        
        if fingerprint_id:
            new_fingerprint = fingerprint_service.get_fingerprint_by_id(fingerprint_id)
            if not new_fingerprint or new_fingerprint.user_id != self.current_user.id:
                raise ValueError("浏览器指纹配置不存在或不属于当前用户")
        else:
            new_fingerprint = fingerprint_service.get_default_fingerprint(self.current_user.id)
        
        if new_fingerprint != self.current_fingerprint:
            logger.info(f"更新浏览器指纹配置: {new_fingerprint.name if new_fingerprint else '默认指纹'}")
            self.current_fingerprint = new_fingerprint
            
            # 重新初始化浏览器以应用新的指纹配置
            await self.close()
            await self.initialize()
    
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