import asyncio
import json
import os
import time
from typing import Optional, Dict, Any
from pathlib import Path

from .logger import logger
from .config import config


class AuthManager:
    """认证管理器 - 处理登录、登出和认证状态管理"""
    
    def __init__(self):
        self.browser_manager = None
        self.token_file = None
        self.cookies_file = None
        self.token = None
        self._setup_storage()
    
    def _setup_storage(self):
        """设置存储路径"""
        app_dir = Path(config.app.data_dir)
        app_dir.mkdir(exist_ok=True)
        
        self.token_file = app_dir / "xiaohongshu_token.json"
        self.cookies_file = app_dir / "xiaohongshu_cookies.json"
    
    async def initialize(self, browser_manager):
        """初始化认证管理器"""
        self.browser_manager = browser_manager
        self.token = self._load_token()
        await self._load_cookies()
        logger.info("认证管理器初始化完成")
    
    async def cleanup(self):
        """清理资源"""
        await self._save_cookies()
        logger.info("认证管理器清理完成")
    
    def _load_token(self) -> Optional[str]:
        """从文件加载token"""
        if not self.token_file.exists():
            return None
        
        try:
            with open(self.token_file, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            
            # 检查token是否过期
            if token_data.get('expire_time', 0) > time.time():
                logger.debug("已加载有效的token")
                return token_data.get('token')
            else:
                logger.debug("token已过期")
                return None
                
        except Exception as e:
            logger.error(f"加载token失败: {str(e)}")
            return None
    
    def _save_token(self, token: str):
        """保存token到文件"""
        try:
            token_data = {
                'token': token,
                'expire_time': time.time() + 30 * 24 * 3600  # 30天有效期
            }
            
            with open(self.token_file, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, ensure_ascii=False, indent=2)
            
            self.token = token
            logger.info("token已保存")
            
        except Exception as e:
            logger.error(f"保存token失败: {str(e)}")
    
    async def _load_cookies(self):
        """从文件加载cookies"""
        if not self.cookies_file.exists():
            return
        
        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            # 确保cookies包含必要的字段
            for cookie in cookies:
                if 'domain' not in cookie:
                    cookie['domain'] = '.xiaohongshu.com'
                if 'path' not in cookie:
                    cookie['path'] = '/'
            
            await self.browser_manager.context.add_cookies(cookies)
            logger.info(f"已加载 {len(cookies)} 个cookies")
            
        except Exception as e:
            logger.error(f"加载cookies失败: {str(e)}")
    
    async def _save_cookies(self):
        """保存cookies到文件"""
        if not self.browser_manager or not self.browser_manager.context:
            return
        
        try:
            cookies = await self.browser_manager.context.cookies()
            
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存 {len(cookies)} 个cookies")
            
        except Exception as e:
            logger.error(f"保存cookies失败: {str(e)}")
    
    async def login(self, phone: str, country_code: str = "+86") -> bool:
        """登录小红书
        
        Args:
            phone: 手机号
            country_code: 国家代码
            
        Returns:
            bool: 登录是否成功
        """
        try:
            # 如果token有效，先尝试使用cookies登录
            if self.token:
                if await self._try_cookie_login():
                    return True
            
            # cookies登录失败，进行手动登录流程
            logger.info(f"开始手机号登录流程: {phone}")
            
            # 这里不实际执行登录，因为登录逻辑在Web API中处理
            # 这个方法主要用于保存登录状态
            return True
            
        except Exception as e:
            logger.error(f"登录失败: {str(e)}", exc_info=True)
            return False
    
    async def _try_cookie_login(self) -> bool:
        """尝试使用cookies登录"""
        try:
            # 导航到创作者中心
            await self.browser_manager.page.goto(config.xiaohongshu.base_url, wait_until="networkidle")
            await asyncio.sleep(2)
            
            # 检查是否已经登录
            current_url = self.browser_manager.page.url
            if "login" not in current_url:
                logger.info("cookies登录成功")
                return True
            else:
                logger.info("cookies登录失败")
                return False
                
        except Exception as e:
            logger.error(f"cookies登录尝试失败: {str(e)}")
            return False
    
    async def is_logged_in(self) -> bool:
        """检查是否已登录"""
        if not self.browser_manager or not self.browser_manager.page:
            return False
        
        try:
            current_url = self.browser_manager.page.url
            
            # 如果当前不在小红书域名，先导航过去
            if "xiaohongshu.com" not in current_url:
                await self.browser_manager.page.goto(config.xiaohongshu.base_url, wait_until="networkidle")
                await asyncio.sleep(2)
                current_url = self.browser_manager.page.url
            
            # 检查URL是否包含login，如果不包含说明已登录
            is_logged_in = "login" not in current_url
            logger.debug(f"登录状态检查: {is_logged_in}, URL: {current_url}")
            
            return is_logged_in
            
        except Exception as e:
            logger.error(f"检查登录状态失败: {str(e)}")
            return False
    
    async def get_user_info(self) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        if not await self.is_logged_in():
            return None
        
        try:
            # 尝试从页面获取用户信息
            user_info = await self.browser_manager.page.evaluate("""
                () => {
                    // 尝试从页面中提取用户信息
                    const userElements = document.querySelectorAll('[data-testid="user-info"], .user-info, .user-name');
                    if (userElements.length > 0) {
                        return {
                            username: userElements[0].textContent || '未知用户',
                            timestamp: Date.now()
                        };
                    }
                    return null;
                }
            """)
            
            return user_info
            
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}")
            return None
    
    async def logout(self) -> bool:
        """登出"""
        try:
            # 清除cookies和token
            if self.browser_manager and self.browser_manager.context:
                await self.browser_manager.context.clear_cookies()
            
            # 删除本地存储的认证信息
            if self.token_file.exists():
                self.token_file.unlink()
            
            if self.cookies_file.exists():
                self.cookies_file.unlink()
            
            self.token = None
            logger.info("已登出")
            return True
            
        except Exception as e:
            logger.error(f"登出失败: {str(e)}")
            return False 