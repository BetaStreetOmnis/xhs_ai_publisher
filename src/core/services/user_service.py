"""
用户管理服务
提供多用户/当前用户切换/登录状态维护等能力
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, or_

from src.config.database import db_manager
from src.core.models.user import User


class UserService:
    """用户管理服务"""

    def __init__(self):
        self.db_manager = db_manager

    def list_users(self, active_only: bool = False) -> List[User]:
        session = self.db_manager.get_session_direct()
        try:
            query = session.query(User)
            if active_only:
                query = query.filter(User.is_active == True)
            return query.order_by(User.is_current.desc(), User.created_at.desc()).all()
        finally:
            session.close()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        session = self.db_manager.get_session_direct()
        try:
            return session.query(User).filter(User.id == user_id).first()
        finally:
            session.close()

    def get_user_by_phone(self, phone: str) -> Optional[User]:
        session = self.db_manager.get_session_direct()
        try:
            return session.query(User).filter(User.phone == phone).first()
        finally:
            session.close()

    def get_user_by_username(self, username: str) -> Optional[User]:
        session = self.db_manager.get_session_direct()
        try:
            return session.query(User).filter(User.username == username).first()
        finally:
            session.close()

    def get_current_user(self) -> Optional[User]:
        """获取当前用户；如果没有当前用户则自动选一个（或创建默认用户）。"""
        session = self.db_manager.get_session_direct()
        try:
            current = (
                session.query(User)
                .filter(and_(User.is_current == True, User.is_active == True))
                .order_by(User.updated_at.desc(), User.id.desc())
                .first()
            )
            if current:
                return current

            # 没有 current：选择第一个可用用户
            fallback = session.query(User).filter(User.is_active == True).order_by(User.id.asc()).first()
            if fallback:
                session.query(User).update({User.is_current: False})
                fallback.is_current = True
                fallback.updated_at = datetime.utcnow()
                session.commit()
                session.refresh(fallback)
                return fallback

            # 仍然没有用户：创建默认用户
            default_user = User(
                username="default_user",
                phone="13800138000",
                display_name="默认用户",
                is_active=True,
                is_current=True,
                is_logged_in=False,
            )
            session.add(default_user)
            session.commit()
            session.refresh(default_user)
            return default_user
        finally:
            session.close()

    def create_user(
        self,
        username: str,
        phone: str,
        display_name: Optional[str] = None,
        set_current: bool = True,
    ) -> User:
        """创建用户；默认设为当前用户。"""
        username = (username or "").strip()
        phone = (phone or "").strip()
        display_name = (display_name or "").strip() or None

        if not username:
            raise ValueError("用户名不能为空")
        if not phone:
            raise ValueError("手机号不能为空")

        session = self.db_manager.get_session_direct()
        try:
            existing = session.query(User).filter(or_(User.username == username, User.phone == phone)).first()
            if existing:
                raise ValueError("用户名或手机号已存在")

            if set_current:
                session.query(User).update({User.is_current: False})

            user = User(
                username=username,
                phone=phone,
                display_name=display_name,
                is_active=True,
                is_current=set_current,
                is_logged_in=False,
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            # 为新用户创建一个默认环境（直连 + 常用指纹）
            try:
                from src.core.services.browser_environment_service import browser_environment_service

                if not browser_environment_service.get_default_environment(user.id):
                    browser_environment_service.create_environment(
                        user_id=user.id,
                        name="默认环境",
                        proxy_enabled=False,
                        proxy_type="direct",
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        viewport_width=1920,
                        viewport_height=937,
                        screen_width=1920,
                        screen_height=1080,
                        platform="Win32",
                        timezone="Asia/Shanghai",
                        locale="zh-CN",
                        webgl_vendor="Google Inc. (Intel)",
                        webgl_renderer="ANGLE (Intel, Intel(R) HD Graphics Direct3D11)",
                    )
            except Exception:
                # 环境创建失败不影响用户创建
                pass

            return user
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def update_user(self, user_id: int, **kwargs) -> User:
        """更新用户基础信息。"""
        session = self.db_manager.get_session_direct()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"用户ID {user_id} 不存在")

            new_username = kwargs.get("username", user.username)
            new_phone = kwargs.get("phone", user.phone)

            # 唯一性校验（用户名/手机号）
            conflict = (
                session.query(User)
                .filter(
                    and_(
                        User.id != user_id,
                        or_(User.username == new_username, User.phone == new_phone),
                    )
                )
                .first()
            )
            if conflict:
                raise ValueError("用户名或手机号已存在")

            allowed_fields = ["username", "phone", "display_name", "is_active"]
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

    def delete_user(self, user_id: int) -> bool:
        """删除用户；如果删除当前用户，会自动切换到另一个可用用户。"""
        session = self.db_manager.get_session_direct()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"用户ID {user_id} 不存在")

            was_current = bool(user.is_current)

            next_user = None
            if was_current:
                next_user = (
                    session.query(User)
                    .filter(and_(User.id != user_id, User.is_active == True))
                    .order_by(User.id.asc())
                    .first()
                )

            session.delete(user)

            if was_current:
                if next_user:
                    session.query(User).update({User.is_current: False})
                    next_user.is_current = True
                    next_user.updated_at = datetime.utcnow()

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def switch_user(self, user_id: int) -> User:
        """切换当前用户。"""
        session = self.db_manager.get_session_direct()
        try:
            target = session.query(User).filter(User.id == user_id).first()
            if not target:
                raise ValueError(f"用户ID {user_id} 不存在")
            if not target.is_active:
                raise ValueError("该用户已被禁用")

            session.query(User).update({User.is_current: False})
            target.is_current = True
            target.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(target)
            return target
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def update_login_status(self, user_id: int, is_logged_in: bool) -> User:
        """更新登录状态。"""
        session = self.db_manager.get_session_direct()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"用户ID {user_id} 不存在")

            user.is_logged_in = bool(is_logged_in)
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


# 全局用户服务实例
user_service = UserService()
