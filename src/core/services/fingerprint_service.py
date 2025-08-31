from sqlalchemy.orm import Session
from sqlalchemy import and_
from src.config.database import db_manager
from src.core.models.user import BrowserFingerprint
from typing import List, Optional, Dict, Any
from datetime import datetime
import random
import json


class FingerprintService:
    """浏览器指纹管理服务"""
    
    def __init__(self):
        self.db_manager = db_manager
    
    def create_fingerprint(self, user_id: int, name: str, **kwargs) -> BrowserFingerprint:
        """创建浏览器指纹配置"""
        session = self.db_manager.get_session_direct()
        try:
            # 检查同一用户下是否已有同名配置
            existing_fingerprint = session.query(BrowserFingerprint).filter(
                and_(BrowserFingerprint.user_id == user_id, BrowserFingerprint.name == name)
            ).first()
            
            if existing_fingerprint:
                raise ValueError(f"浏览器指纹配置 '{name}' 已存在")
            
            # 如果是第一个指纹配置，设为默认
            is_default = session.query(BrowserFingerprint).filter(
                BrowserFingerprint.user_id == user_id
            ).count() == 0
            
            fingerprint = BrowserFingerprint(
                user_id=user_id,
                name=name,
                is_default=is_default,
                is_active=True,
                **kwargs
            )
            
            session.add(fingerprint)
            session.commit()
            session.refresh(fingerprint)
            
            return fingerprint
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_fingerprint_by_id(self, fingerprint_id: int) -> Optional[BrowserFingerprint]:
        """根据ID获取浏览器指纹配置"""
        session = self.db_manager.get_session_direct()
        try:
            return session.query(BrowserFingerprint).filter(BrowserFingerprint.id == fingerprint_id).first()
        finally:
            session.close()
    
    def get_user_fingerprints(self, user_id: int, active_only: bool = True) -> List[BrowserFingerprint]:
        """获取用户的所有浏览器指纹配置"""
        session = self.db_manager.get_session_direct()
        try:
            query = session.query(BrowserFingerprint).filter(BrowserFingerprint.user_id == user_id)
            if active_only:
                query = query.filter(BrowserFingerprint.is_active == True)
            return query.order_by(BrowserFingerprint.is_default.desc(), BrowserFingerprint.created_at.desc()).all()
        finally:
            session.close()
    
    def get_default_fingerprint(self, user_id: int) -> Optional[BrowserFingerprint]:
        """获取用户的默认浏览器指纹配置"""
        session = self.db_manager.get_session_direct()
        try:
            return session.query(BrowserFingerprint).filter(
                and_(
                    BrowserFingerprint.user_id == user_id,
                    BrowserFingerprint.is_default == True,
                    BrowserFingerprint.is_active == True
                )
            ).first()
        finally:
            session.close()
    
    def set_default_fingerprint(self, user_id: int, fingerprint_id: int) -> BrowserFingerprint:
        """设置默认浏览器指纹配置"""
        session = self.db_manager.get_session_direct()
        try:
            # 取消用户所有指纹配置的默认状态
            session.query(BrowserFingerprint).filter(
                BrowserFingerprint.user_id == user_id
            ).update({BrowserFingerprint.is_default: False})
            
            # 设置指定配置为默认
            target_fingerprint = session.query(BrowserFingerprint).filter(
                and_(BrowserFingerprint.id == fingerprint_id, BrowserFingerprint.user_id == user_id)
            ).first()
            
            if not target_fingerprint:
                raise ValueError(f"浏览器指纹配置ID {fingerprint_id} 不存在")
            
            target_fingerprint.is_default = True
            target_fingerprint.is_active = True
            target_fingerprint.updated_at = datetime.now()
            
            session.commit()
            session.refresh(target_fingerprint)
            
            return target_fingerprint
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def update_fingerprint(self, fingerprint_id: int, **kwargs) -> BrowserFingerprint:
        """更新浏览器指纹配置"""
        session = self.db_manager.get_session_direct()
        try:
            fingerprint = session.query(BrowserFingerprint).filter(BrowserFingerprint.id == fingerprint_id).first()
            if not fingerprint:
                raise ValueError(f"浏览器指纹配置ID {fingerprint_id} 不存在")
            
            # 更新允许的字段
            allowed_fields = [
                'name', 'user_agent', 'viewport_width', 'viewport_height',
                'screen_width', 'screen_height', 'timezone', 'locale',
                'geolocation_latitude', 'geolocation_longitude', 'platform',
                'webgl_vendor', 'webgl_renderer', 'fonts', 'plugins',
                'canvas_fingerprint', 'is_active'
            ]
            
            for field, value in kwargs.items():
                if field in allowed_fields and hasattr(fingerprint, field):
                    setattr(fingerprint, field, value)
            
            fingerprint.updated_at = datetime.now()
            session.commit()
            session.refresh(fingerprint)
            
            return fingerprint
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete_fingerprint(self, fingerprint_id: int) -> bool:
        """删除浏览器指纹配置"""
        session = self.db_manager.get_session_direct()
        try:
            fingerprint = session.query(BrowserFingerprint).filter(BrowserFingerprint.id == fingerprint_id).first()
            if not fingerprint:
                raise ValueError(f"浏览器指纹配置ID {fingerprint_id} 不存在")
            
            user_id = fingerprint.user_id
            is_default = fingerprint.is_default
            
            session.delete(fingerprint)
            
            # 如果删除的是默认配置，设置另一个配置为默认
            if is_default:
                remaining_fingerprint = session.query(BrowserFingerprint).filter(
                    and_(BrowserFingerprint.user_id == user_id, BrowserFingerprint.is_active == True)
                ).first()
                if remaining_fingerprint:
                    remaining_fingerprint.is_default = True
            
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def generate_random_fingerprint(self, user_id: int, name: str) -> BrowserFingerprint:
        """生成随机浏览器指纹配置"""
        # 常见的User-Agent列表
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
        ]
        
        # 常见的屏幕分辨率
        resolutions = [
            (1920, 1080), (1366, 768), (1440, 900), (1536, 864),
            (1280, 720), (1600, 900), (2560, 1440), (1920, 1200)
        ]
        
        # 常见的时区
        timezones = [
            'Asia/Shanghai', 'Asia/Beijing', 'Asia/Hong_Kong',
            'Asia/Taipei', 'Asia/Singapore', 'Asia/Tokyo'
        ]
        
        # 随机选择配置
        resolution = random.choice(resolutions)
        timezone = random.choice(timezones)
        user_agent = random.choice(user_agents)
        
        # 视窗大小通常比屏幕分辨率小一些
        viewport_width = resolution[0] - random.randint(0, 100)
        viewport_height = resolution[1] - random.randint(100, 200)
        
        # 生成随机地理位置（中国范围内）
        latitude = round(random.uniform(18.0, 54.0), 6)  # 中国纬度范围
        longitude = round(random.uniform(73.0, 135.0), 6)  # 中国经度范围
        
        # 常见字体列表
        common_fonts = [
            "Arial", "Helvetica", "Times New Roman", "Courier New",
            "Verdana", "Georgia", "Palatino", "Garamond", "Bookman",
            "Comic Sans MS", "Trebuchet MS", "Arial Black", "Impact",
            "Microsoft YaHei", "SimSun", "SimHei", "KaiTi", "FangSong"
        ]
        
        fingerprint_data = {
            'user_agent': user_agent,
            'viewport_width': viewport_width,
            'viewport_height': viewport_height,
            'screen_width': resolution[0],
            'screen_height': resolution[1],
            'timezone': timezone,
            'locale': 'zh-CN',
            'geolocation_latitude': str(latitude),
            'geolocation_longitude': str(longitude),
            'platform': 'Win32' if 'Windows' in user_agent else 'MacIntel',
            'webgl_vendor': 'Google Inc. (Intel)',
            'webgl_renderer': 'ANGLE (Intel, Intel(R) HD Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)',
        }
        
        fingerprint = self.create_fingerprint(user_id, name, **fingerprint_data)
        
        # 设置字体列表
        fingerprint.set_fonts_list(random.sample(common_fonts, random.randint(12, 18)))
        
        # 更新到数据库
        session = self.db_manager.get_session_direct()
        try:
            session.merge(fingerprint)
            session.commit()
            session.refresh(fingerprint)
            return fingerprint
        finally:
            session.close()
    
    def create_preset_fingerprints(self, user_id: int) -> List[BrowserFingerprint]:
        """为用户创建预设的浏览器指纹配置"""
        presets = [
            {
                'name': 'Windows Chrome 默认',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'viewport_width': 1920,
                'viewport_height': 937,
                'screen_width': 1920,
                'screen_height': 1080,
                'platform': 'Win32',
                'timezone': 'Asia/Shanghai',
                'locale': 'zh-CN'
            },
            {
                'name': 'Mac Chrome 默认',
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'viewport_width': 1440,
                'viewport_height': 764,
                'screen_width': 1440,
                'screen_height': 900,
                'platform': 'MacIntel',
                'timezone': 'Asia/Shanghai',
                'locale': 'zh-CN'
            },
            {
                'name': 'Windows Firefox 默认',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
                'viewport_width': 1366,
                'viewport_height': 625,
                'screen_width': 1366,
                'screen_height': 768,
                'platform': 'Win32',
                'timezone': 'Asia/Shanghai',
                'locale': 'zh-CN'
            }
        ]
        
        created_fingerprints = []
        for preset in presets:
            try:
                fingerprint = self.create_fingerprint(user_id, **preset)
                created_fingerprints.append(fingerprint)
            except ValueError:
                # 如果已存在同名配置，跳过
                continue
        
        return created_fingerprints
    
    def get_all_fingerprints(self, user_id: int = None, active_only: bool = True) -> List[BrowserFingerprint]:
        """获取所有浏览器指纹配置（兼容旧接口）"""
        if user_id is None:
            # 如果没有指定用户，返回所有配置
            session = self.db_manager.get_session_direct()
            try:
                query = session.query(BrowserFingerprint)
                if active_only:
                    query = query.filter(BrowserFingerprint.is_active == True)
                return query.order_by(BrowserFingerprint.created_at.desc()).all()
            finally:
                session.close()
        else:
            return self.get_user_fingerprints(user_id, active_only)
    
    def get_all(self, user_id: int = None):
        """兼容旧接口的方法"""
        fingerprints = self.get_all_fingerprints(user_id)
        return [fingerprint.to_dict() for fingerprint in fingerprints]
    
    def get_fingerprint_stats(self, user_id: int) -> Dict[str, Any]:
        """获取用户浏览器指纹配置统计信息"""
        session = self.db_manager.get_session_direct()
        try:
            fingerprints = session.query(BrowserFingerprint).filter(BrowserFingerprint.user_id == user_id).all()
            
            stats = {
                'total_count': len(fingerprints),
                'active_count': len([f for f in fingerprints if f.is_active]),
                'default_fingerprint': None,
                'platforms': {},
                'user_agents': {}
            }
            
            # 获取默认配置信息
            default_fingerprint = next((f for f in fingerprints if f.is_default), None)
            if default_fingerprint:
                stats['default_fingerprint'] = {
                    'id': default_fingerprint.id,
                    'name': default_fingerprint.name,
                    'platform': default_fingerprint.platform,
                    'viewport': f"{default_fingerprint.viewport_width}x{default_fingerprint.viewport_height}"
                }
            
            # 统计平台分布
            for fingerprint in fingerprints:
                if fingerprint.platform:
                    stats['platforms'][fingerprint.platform] = stats['platforms'].get(fingerprint.platform, 0) + 1
            
            # 统计浏览器类型
            for fingerprint in fingerprints:
                if fingerprint.user_agent:
                    if 'Chrome' in fingerprint.user_agent:
                        browser = 'Chrome'
                    elif 'Firefox' in fingerprint.user_agent:
                        browser = 'Firefox'
                    elif 'Safari' in fingerprint.user_agent and 'Chrome' not in fingerprint.user_agent:
                        browser = 'Safari'
                    else:
                        browser = 'Other'
                    stats['user_agents'][browser] = stats['user_agents'].get(browser, 0) + 1
            
            return stats
            
        finally:
            session.close()

# 全局浏览器指纹服务实例
fingerprint_service = FingerprintService() 