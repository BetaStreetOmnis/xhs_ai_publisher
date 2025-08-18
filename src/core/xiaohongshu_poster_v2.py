import asyncio
import json
import os
import time
from typing import List, Optional, Dict, Any
from pathlib import Path

from .browser_manager import BrowserManager, browser_session
from .logger import logger
from .config import config
from .auth_manager import AuthManager
from .content_publisher import ContentPublisher


class XiaohongshuPosterV2:
    """小红书自动发布器 V2 - 重构版本"""
    
    def __init__(self):
        self.browser_manager: Optional[BrowserManager] = None
        self.auth_manager = AuthManager()
        self.content_publisher = ContentPublisher()
        self._session_active = False
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close_session()
    
    async def start_session(self) -> None:
        """启动会话"""
        if self._session_active:
            return
        
        try:
            logger.info("启动小红书发布会话...")
            self.browser_manager = BrowserManager()
            await self.browser_manager.initialize()
            
            # 初始化子模块
            await self.auth_manager.initialize(self.browser_manager)
            await self.content_publisher.initialize(self.browser_manager)
            
            self._session_active = True
            logger.info("会话启动成功")
            
        except Exception as e:
            logger.error(f"启动会话失败: {str(e)}", exc_info=True)
            await self.close_session()
            raise
    
    async def close_session(self) -> None:
        """关闭会话"""
        if not self._session_active:
            return
        
        try:
            logger.info("关闭小红书发布会话...")
            
            if self.content_publisher:
                await self.content_publisher.cleanup()
            
            if self.auth_manager:
                await self.auth_manager.cleanup()
            
            if self.browser_manager:
                await self.browser_manager.close()
            
            self._session_active = False
            logger.info("会话关闭成功")
            
        except Exception as e:
            logger.error(f"关闭会话时出错: {str(e)}", exc_info=True)
    
    async def login(self, phone: str, country_code: str = "+86") -> bool:
        """登录小红书
        
        Args:
            phone: 手机号
            country_code: 国家代码
            
        Returns:
            bool: 登录是否成功
        """
        if not self._session_active:
            await self.start_session()
        
        try:
            logger.info(f"开始登录，手机号: {phone}")
            success = await self.auth_manager.login(phone, country_code)
            
            if success:
                logger.info("登录成功")
            else:
                logger.warning("登录失败")
            
            return success
            
        except Exception as e:
            logger.error(f"登录过程出错: {str(e)}", exc_info=True)
            return False
    
    async def post_article(
        self, 
        title: str, 
        content: str, 
        images: Optional[List[str]] = None,
        auto_publish: bool = False
    ) -> bool:
        """发布文章
        
        Args:
            title: 文章标题
            content: 文章内容
            images: 图片路径列表
            auto_publish: 是否自动发布（默认为手动确认）
            
        Returns:
            bool: 发布是否成功
        """
        if not self._session_active:
            raise RuntimeError("会话未启动，请先调用 start_session() 或使用上下文管理器")
        
        try:
            logger.info(f"开始发布文章: {title}")
            
            # 检查登录状态
            if not await self.auth_manager.is_logged_in():
                logger.error("用户未登录，无法发布文章")
                return False
            
            # 发布文章
            success = await self.content_publisher.publish_article(
                title=title,
                content=content,
                images=images,
                auto_publish=auto_publish
            )
            
            if success:
                logger.info("文章发布成功")
            else:
                logger.warning("文章发布失败")
            
            return success
            
        except Exception as e:
            logger.error(f"发布文章时出错: {str(e)}", exc_info=True)
            return False
    
    async def get_login_status(self) -> Dict[str, Any]:
        """获取登录状态"""
        if not self._session_active:
            return {"logged_in": False, "error": "会话未启动"}
        
        try:
            is_logged_in = await self.auth_manager.is_logged_in()
            user_info = await self.auth_manager.get_user_info() if is_logged_in else None
            
            return {
                "logged_in": is_logged_in,
                "user_info": user_info,
                "session_active": self._session_active
            }
            
        except Exception as e:
            logger.error(f"获取登录状态时出错: {str(e)}", exc_info=True)
            return {"logged_in": False, "error": str(e)}


# 便捷函数
async def quick_publish(
    phone: str,
    title: str, 
    content: str, 
    images: Optional[List[str]] = None,
    auto_publish: bool = False
) -> bool:
    """快速发布文章的便捷函数"""
    async with XiaohongshuPosterV2() as poster:
        # 登录
        if not await poster.login(phone):
            return False
        
        # 发布文章
        return await poster.post_article(
            title=title,
            content=content,
            images=images,
            auto_publish=auto_publish
        )


# 使用浏览器会话的便捷函数
async def with_browser_session(func):
    """使用浏览器会话的装饰器"""
    async with browser_session() as browser:
        return await func(browser) 