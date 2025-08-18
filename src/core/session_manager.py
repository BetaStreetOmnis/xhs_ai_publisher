import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

from .logger import logger
from .config import config


@dataclass
class Session:
    """会话数据结构"""
    id: str
    name: str
    created_at: float
    last_active_at: float
    status: str = "active"  # active, paused, completed, failed
    browser_data: Optional[Dict[str, Any]] = None
    user_info: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """从字典创建实例"""
        return cls(**data)
    
    def is_expired(self, timeout_hours: int = 24) -> bool:
        """检查会话是否过期"""
        return time.time() - self.last_active_at > timeout_hours * 3600


class SessionManager:
    """会话管理器 - 处理浏览器会话的创建、管理和清理"""
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.current_session_id: Optional[str] = None
        self.sessions_file = None
        self._setup_storage()
    
    def _setup_storage(self):
        """设置存储路径"""
        app_dir = Path(config.app.data_dir)
        app_dir.mkdir(exist_ok=True)
        
        self.sessions_file = app_dir / "sessions.json"
        self._load_sessions()
    
    def _load_sessions(self):
        """从文件加载会话"""
        if not self.sessions_file.exists():
            return
        
        try:
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                sessions_data = json.load(f)
            
            self.sessions = {}
            for session_id, data in sessions_data.items():
                self.sessions[session_id] = Session.from_dict(data)
            
            # 清理过期会话
            self._cleanup_expired_sessions()
            
            logger.info(f"已加载 {len(self.sessions)} 个会话")
            
        except Exception as e:
            logger.error(f"加载会话失败: {str(e)}")
            self.sessions = {}
    
    def _save_sessions(self):
        """保存会话到文件"""
        try:
            sessions_data = {}
            for session_id, session in self.sessions.items():
                sessions_data[session_id] = session.to_dict()
            
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"已保存 {len(self.sessions)} 个会话")
            
        except Exception as e:
            logger.error(f"保存会话失败: {str(e)}")
    
    def _cleanup_expired_sessions(self):
        """清理过期会话"""
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if session.is_expired():
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.info(f"清理过期会话: {session_id}")
        
        if expired_sessions:
            self._save_sessions()
    
    def create_session(self, name: str = None) -> str:
        """创建新会话
        
        Args:
            name: 会话名称
            
        Returns:
            str: 会话ID
        """
        session_id = str(uuid.uuid4())
        
        if name is None:
            name = f"会话_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session = Session(
            id=session_id,
            name=name,
            created_at=time.time(),
            last_active_at=time.time()
        )
        
        self.sessions[session_id] = session
        self.current_session_id = session_id
        self._save_sessions()
        
        logger.info(f"创建会话: {session_id} - {name}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            Session: 会话对象，如果不存在返回None
        """
        return self.sessions.get(session_id)
    
    def get_current_session(self) -> Optional[Session]:
        """获取当前会话
        
        Returns:
            Session: 当前会话对象，如果不存在返回None
        """
        if self.current_session_id:
            return self.sessions.get(self.current_session_id)
        return None
    
    def set_current_session(self, session_id: str) -> bool:
        """设置当前会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 设置是否成功
        """
        if session_id not in self.sessions:
            logger.error(f"会话不存在: {session_id}")
            return False
        
        self.current_session_id = session_id
        self.update_session_activity(session_id)
        
        logger.info(f"设置当前会话: {session_id}")
        return True
    
    def update_session_activity(self, session_id: str) -> bool:
        """更新会话活动时间
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 更新是否成功
        """
        if session_id not in self.sessions:
            return False
        
        self.sessions[session_id].last_active_at = time.time()
        self._save_sessions()
        return True
    
    def update_session_status(self, session_id: str, status: str) -> bool:
        """更新会话状态
        
        Args:
            session_id: 会话ID
            status: 新状态
            
        Returns:
            bool: 更新是否成功
        """
        if session_id not in self.sessions:
            logger.error(f"会话不存在: {session_id}")
            return False
        
        self.sessions[session_id].status = status
        self.sessions[session_id].last_active_at = time.time()
        self._save_sessions()
        
        logger.info(f"更新会话状态: {session_id} -> {status}")
        return True
    
    def update_session_browser_data(self, session_id: str, browser_data: Dict[str, Any]) -> bool:
        """更新会话浏览器数据
        
        Args:
            session_id: 会话ID
            browser_data: 浏览器数据
            
        Returns:
            bool: 更新是否成功
        """
        if session_id not in self.sessions:
            logger.error(f"会话不存在: {session_id}")
            return False
        
        self.sessions[session_id].browser_data = browser_data
        self.sessions[session_id].last_active_at = time.time()
        self._save_sessions()
        
        logger.debug(f"更新会话浏览器数据: {session_id}")
        return True
    
    def update_session_user_info(self, session_id: str, user_info: Dict[str, Any]) -> bool:
        """更新会话用户信息
        
        Args:
            session_id: 会话ID
            user_info: 用户信息
            
        Returns:
            bool: 更新是否成功
        """
        if session_id not in self.sessions:
            logger.error(f"会话不存在: {session_id}")
            return False
        
        self.sessions[session_id].user_info = user_info
        self.sessions[session_id].last_active_at = time.time()
        self._save_sessions()
        
        logger.info(f"更新会话用户信息: {session_id}")
        return True
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 删除是否成功
        """
        if session_id not in self.sessions:
            logger.error(f"会话不存在: {session_id}")
            return False
        
        # 如果删除的是当前会话，清空当前会话ID
        if self.current_session_id == session_id:
            self.current_session_id = None
        
        del self.sessions[session_id]
        self._save_sessions()
        
        logger.info(f"删除会话: {session_id}")
        return True
    
    def list_sessions(self, status: str = None, limit: int = None) -> List[Session]:
        """列出会话
        
        Args:
            status: 状态过滤
            limit: 限制数量
            
        Returns:
            List[Session]: 会话列表
        """
        sessions = list(self.sessions.values())
        
        # 状态过滤
        if status:
            sessions = [s for s in sessions if s.status == status]
        
        # 按最后活动时间倒序排序
        sessions.sort(key=lambda x: x.last_active_at, reverse=True)
        
        # 限制数量
        if limit:
            sessions = sessions[:limit]
        
        return sessions
    
    def get_session_stats(self) -> Dict[str, int]:
        """获取会话统计信息
        
        Returns:
            Dict[str, int]: 统计信息
        """
        stats = {
            'total': len(self.sessions),
            'active': 0,
            'paused': 0,
            'completed': 0,
            'failed': 0
        }
        
        for session in self.sessions.values():
            stats[session.status] = stats.get(session.status, 0) + 1
        
        return stats
    
    def cleanup_all_sessions(self):
        """清理所有会话"""
        self.sessions.clear()
        self.current_session_id = None
        self._save_sessions()
        logger.info("已清理所有会话")
    
    def get_active_sessions(self) -> List[Session]:
        """获取活跃会话（24小时内有活动）
        
        Returns:
            List[Session]: 活跃会话列表
        """
        active_sessions = []
        current_time = time.time()
        
        for session in self.sessions.values():
            if current_time - session.last_active_at <= 24 * 3600:  # 24小时内
                active_sessions.append(session)
        
        return active_sessions
    
    def pause_session(self, session_id: str) -> bool:
        """暂停会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 暂停是否成功
        """
        return self.update_session_status(session_id, "paused")
    
    def resume_session(self, session_id: str) -> bool:
        """恢复会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 恢复是否成功
        """
        return self.update_session_status(session_id, "active")
    
    def complete_session(self, session_id: str) -> bool:
        """完成会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 完成是否成功
        """
        return self.update_session_status(session_id, "completed") 