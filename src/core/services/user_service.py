"""
用户管理服务
提供用户的增删改查等功能
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import and_, or_

from ..models.user import User
from ...config.database import db_manager


class UserService:
    """用户服务类"""
    
    def __init__(self):
        self.db_manager = db_manager
    
    def create_user(self, username: str, phone: str, display_name: str = None) -> User:
        """创建新用户"""
        session = self.db_manager.get_session_direct()
        try:
            # 检查用户名是否已存在
            existing_user = session.query(User).filter(User.username == username).first()
            if existing_user:
                raise ValueError(f"用户名 '{username}' 已存在")
            
            # 检查手机号是否已存在
            existing_phone = session.query(User).filter(User.phone == phone).first()
            if existing_phone:
                raise ValueError(f"手机号 '{phone}' 已存在")
            
            # 创建新用户
            user = User(
                username=username,
                phone=phone,
                display_name=display_name,
                is_active=True,
                is_current=False,
                is_logged_in=False
            )
            
            session.add(user)
            session.commit()
            session.refresh(user)
            
            return user
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        session = self.db_manager.get_session_direct()
        try:
            return session.query(User).filter(User.id == user_id).first()
        finally:
            session.close()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        session = self.db_manager.get_session_direct()
        try:
            return session.query(User).filter(User.username == username).first()
        finally:
            session.close()
    
    def get_user_by_phone(self, phone: str) -> Optional[User]:
        """根据手机号获取用户"""
        session = self.db_manager.get_session_direct()
        try:
            return session.query(User).filter(User.phone == phone).first()
        finally:
            session.close()
    
    def get_current_user(self) -> Optional[User]:
        """获取当前用户"""
        session = self.db_manager.get_session_direct()
        try:
            return session.query(User).filter(
                and_(User.is_current == True, User.is_active == True)
            ).first()
        finally:
            session.close()
    
    def get_all_users(self, include_inactive: bool = False) -> List[User]:
        """获取所有用户"""
        session = self.db_manager.get_session_direct()
        try:
            query = session.query(User)
            if not include_inactive:
                query = query.filter(User.is_active == True)
            return query.order_by(User.created_at.desc()).all()
        finally:
            session.close()
    
    def switch_user(self, user_id: int) -> User:
        """切换当前用户"""
        session = self.db_manager.get_session_direct()
        try:
            # 检查目标用户是否存在
            target_user = session.query(User).filter(
                and_(User.id == user_id, User.is_active == True)
            ).first()
            
            if not target_user:
                raise ValueError(f"用户ID {user_id} 不存在或已被禁用")
            
            # 取消所有用户的当前状态
            session.query(User).update({User.is_current: False})
            
            # 设置目标用户为当前用户
            target_user.is_current = True
            target_user.last_login_at = datetime.utcnow()
            
            session.commit()
            session.refresh(target_user)
            
            return target_user
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def update_user(self, user_id: int, **kwargs) -> User:
        """更新用户信息"""
        session = self.db_manager.get_session_direct()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"用户ID {user_id} 不存在")
            
            # 检查用户名是否已被其他用户使用
            if 'username' in kwargs and kwargs['username'] != user.username:
                existing_user = session.query(User).filter(
                    and_(User.username == kwargs['username'], User.id != user_id)
                ).first()
                if existing_user:
                    raise ValueError(f"用户名 '{kwargs['username']}' 已存在")
            
            # 检查手机号是否已被其他用户使用
            if 'phone' in kwargs and kwargs['phone'] != user.phone:
                existing_phone = session.query(User).filter(
                    and_(User.phone == kwargs['phone'], User.id != user_id)
                ).first()
                if existing_phone:
                    raise ValueError(f"手机号 '{kwargs['phone']}' 已存在")
            
            # 更新允许的字段
            allowed_fields = [
                'username', 'phone', 'display_name', 'is_active'
            ]
            
            for field, value in kwargs.items():
                if field in allowed_fields and hasattr(user, field):
                    setattr(user, field, value)
            
            user.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(user)
            
            return user
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def update_login_status(self, user_id: int, is_logged_in: bool) -> User:
        """更新用户登录状态"""
        session = self.db_manager.get_session_direct()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"用户ID {user_id} 不存在")
            
            user.is_logged_in = is_logged_in
            if is_logged_in:
                user.last_login_at = datetime.utcnow()
            
            user.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(user)
            
            return user
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete_user(self, user_id: int, hard_delete: bool = False) -> bool:
        """删除用户（软删除或硬删除）"""
        session = self.db_manager.get_session_direct()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"用户ID {user_id} 不存在")
            
            if user.is_current:
                raise ValueError("不能删除当前用户，请先切换到其他用户")
            
            if hard_delete:
                # 硬删除：直接从数据库中删除
                session.delete(user)
            else:
                # 软删除：标记为非活跃状态
                user.is_active = False
                user.is_logged_in = False
                user.updated_at = datetime.utcnow()
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def search_users(self, keyword: str) -> List[User]:
        """搜索用户"""
        session = self.db_manager.get_session_direct()
        try:
            return session.query(User).filter(
                and_(
                    User.is_active == True,
                    or_(
                        User.username.like(f'%{keyword}%'),
                        User.display_name.like(f'%{keyword}%'),
                        User.phone.like(f'%{keyword}%')
                    )
                )
            ).order_by(User.created_at.desc()).all()
        finally:
            session.close()
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """获取用户统计信息"""
        session = self.db_manager.get_session_direct()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"用户ID {user_id} 不存在")
            
            # 获取用户统计信息
            stats = {
                'user_id': user.id,
                'username': user.username,
                'display_name': user.display_name,
                'phone': user.phone,
                'is_logged_in': user.is_logged_in,
                'last_login_at': user.last_login_at,
                'created_at': user.created_at,
                'proxy_configs_count': len(user.proxy_configs),
                'browser_fingerprints_count': len(user.browser_fingerprints),
            }
            
            return stats
        finally:
            session.close()


# 全局用户服务实例
user_service = UserService() 