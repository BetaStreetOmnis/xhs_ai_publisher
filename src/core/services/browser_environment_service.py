"""
浏览器环境管理服务
提供代理+指纹的综合环境管理
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import and_, or_
import asyncio
import httpx
import time
import random
import json

from ..models.browser_environment import BrowserEnvironment
from ...config.database import db_manager


class BrowserEnvironmentService:
    """浏览器环境管理服务"""
    
    def __init__(self):
        self.db_manager = db_manager
    
    def create_environment(self, user_id: int, name: str, **kwargs) -> BrowserEnvironment:
        """创建浏览器环境配置"""
        session = self.db_manager.get_session_direct()
        try:
            # 检查同一用户下是否已有同名配置
            existing_env = session.query(BrowserEnvironment).filter(
                and_(BrowserEnvironment.user_id == user_id, BrowserEnvironment.name == name)
            ).first()
            
            if existing_env:
                raise ValueError(f"环境配置 '{name}' 已存在")
            
            # 如果是第一个环境配置，设为默认
            is_default = session.query(BrowserEnvironment).filter(
                BrowserEnvironment.user_id == user_id
            ).count() == 0
            
            environment = BrowserEnvironment(
                user_id=user_id,
                name=name,
                is_default=is_default,
                is_active=True,
                **kwargs
            )
            
            session.add(environment)
            session.commit()
            session.refresh(environment)
            
            return environment
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_environment_by_id(self, env_id: int) -> Optional[BrowserEnvironment]:
        """根据ID获取环境配置"""
        session = self.db_manager.get_session_direct()
        try:
            return session.query(BrowserEnvironment).filter(BrowserEnvironment.id == env_id).first()
        finally:
            session.close()
    
    def get_user_environments(self, user_id: int, active_only: bool = True) -> List[BrowserEnvironment]:
        """获取用户的所有环境配置"""
        session = self.db_manager.get_session_direct()
        try:
            query = session.query(BrowserEnvironment).filter(BrowserEnvironment.user_id == user_id)
            if active_only:
                query = query.filter(BrowserEnvironment.is_active == True)
            return query.order_by(BrowserEnvironment.is_default.desc(), BrowserEnvironment.created_at.desc()).all()
        finally:
            session.close()
    
    def get_all_environments(self, user_id: int = None, active_only: bool = True) -> List[BrowserEnvironment]:
        """获取所有环境配置"""
        session = self.db_manager.get_session_direct()
        try:
            query = session.query(BrowserEnvironment)
            if user_id:
                query = query.filter(BrowserEnvironment.user_id == user_id)
            if active_only:
                query = query.filter(BrowserEnvironment.is_active == True)
            return query.order_by(BrowserEnvironment.created_at.desc()).all()
        finally:
            session.close()
    
    def get_all(self, user_id: int = None):
        """兼容旧接口的方法"""
        environments = self.get_all_environments(user_id)
        return [env.to_dict() for env in environments]
    
    def get_default_environment(self, user_id: int) -> Optional[BrowserEnvironment]:
        """获取用户的默认环境配置"""
        session = self.db_manager.get_session_direct()
        try:
            return session.query(BrowserEnvironment).filter(
                and_(
                    BrowserEnvironment.user_id == user_id,
                    BrowserEnvironment.is_default == True,
                    BrowserEnvironment.is_active == True
                )
            ).first()
        finally:
            session.close()
    
    def set_default_environment(self, user_id: int, env_id: int) -> BrowserEnvironment:
        """设置默认环境配置"""
        session = self.db_manager.get_session_direct()
        try:
            # 取消用户所有环境的默认状态
            session.query(BrowserEnvironment).filter(
                BrowserEnvironment.user_id == user_id
            ).update({BrowserEnvironment.is_default: False})
            
            # 设置指定环境为默认
            target_env = session.query(BrowserEnvironment).filter(
                and_(BrowserEnvironment.id == env_id, BrowserEnvironment.user_id == user_id)
            ).first()
            
            if not target_env:
                raise ValueError(f"环境配置ID {env_id} 不存在")
            
            target_env.is_default = True
            target_env.is_active = True
            target_env.updated_at = datetime.utcnow()
            
            session.commit()
            session.refresh(target_env)
            
            return target_env
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def update_environment(self, env_id: int, **kwargs) -> BrowserEnvironment:
        """更新环境配置"""
        session = self.db_manager.get_session_direct()
        try:
            environment = session.query(BrowserEnvironment).filter(BrowserEnvironment.id == env_id).first()
            if not environment:
                raise ValueError(f"环境配置ID {env_id} 不存在")
            
            # 更新允许的字段
            allowed_fields = [
                'name', 'proxy_enabled', 'proxy_type', 'proxy_host', 'proxy_port', 
                'proxy_username', 'proxy_password', 'user_agent', 'viewport_width', 
                'viewport_height', 'screen_width', 'screen_height', 'platform', 
                'timezone', 'locale', 'webgl_vendor', 'webgl_renderer', 
                'canvas_fingerprint', 'fonts', 'plugins', 'geolocation_latitude',
                'geolocation_longitude', 'is_active', 'extra_config'
            ]
            
            for field, value in kwargs.items():
                if field in allowed_fields and hasattr(environment, field):
                    setattr(environment, field, value)
            
            environment.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(environment)
            
            return environment
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete_environment(self, env_id: int) -> bool:
        """删除环境配置"""
        session = self.db_manager.get_session_direct()
        try:
            environment = session.query(BrowserEnvironment).filter(BrowserEnvironment.id == env_id).first()
            if not environment:
                raise ValueError(f"环境配置ID {env_id} 不存在")
            
            user_id = environment.user_id
            is_default = environment.is_default
            
            session.delete(environment)
            
            # 如果删除的是默认配置，设置另一个配置为默认
            if is_default:
                remaining_env = session.query(BrowserEnvironment).filter(
                    and_(BrowserEnvironment.user_id == user_id, BrowserEnvironment.is_active == True)
                ).first()
                if remaining_env:
                    remaining_env.is_default = True
            
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    async def test_environment(self, env_id: int, timeout: int = 10) -> Dict[str, Any]:
        """测试环境配置（包括代理和指纹）"""
        session = self.db_manager.get_session_direct()
        try:
            environment = session.query(BrowserEnvironment).filter(BrowserEnvironment.id == env_id).first()
            if not environment:
                raise ValueError(f"环境配置ID {env_id} 不存在")
            
            # 测试代理连通性
            start_time = time.time()
            test_result = False
            latency = None
            error_message = None
            
            try:
                if environment.proxy_enabled and environment.proxy_type != 'direct':
                    proxy_url = environment.get_proxy_url()
                    
                    async with httpx.AsyncClient(
                        proxies={'http://': proxy_url, 'https://': proxy_url},
                        timeout=timeout
                    ) as client:
                        response = await client.get('https://httpbin.org/ip')
                        if response.status_code == 200:
                            test_result = True
                            latency = int((time.time() - start_time) * 1000)
                        else:
                            error_message = f"HTTP状态码: {response.status_code}"
                else:
                    # 直连测试
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        response = await client.get('https://httpbin.org/ip')
                        if response.status_code == 200:
                            test_result = True
                            latency = int((time.time() - start_time) * 1000)
                        
            except Exception as e:
                error_message = str(e)
            
            # 更新测试结果到数据库
            environment.last_test_at = datetime.utcnow()
            environment.test_success = test_result
            environment.test_latency = latency
            environment.test_result = error_message or "测试成功"
            environment.updated_at = datetime.utcnow()
            
            session.commit()
            
            return {
                'env_id': env_id,
                'test_result': test_result,
                'latency': latency,
                'error_message': error_message,
                'test_time': environment.last_test_at,
                'proxy_enabled': environment.proxy_enabled,
                'proxy_display': environment.get_proxy_display()
            }
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def create_preset_environments(self, user_id: int) -> List[BrowserEnvironment]:
        """为用户创建预设的浏览器环境"""
        presets = [
            {
                'name': 'Windows Chrome 直连',
                'proxy_enabled': False,
                'proxy_type': 'direct',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'viewport_width': 1920,
                'viewport_height': 937,
                'screen_width': 1920,
                'screen_height': 1080,
                'platform': 'Win32',
                'timezone': 'Asia/Shanghai',
                'locale': 'zh-CN',
                'webgl_vendor': 'Google Inc. (Intel)',
                'webgl_renderer': 'ANGLE (Intel, Intel(R) HD Graphics Direct3D11)'
            },
            {
                'name': 'Mac Chrome 直连',
                'proxy_enabled': False,
                'proxy_type': 'direct',
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'viewport_width': 1440,
                'viewport_height': 764,
                'screen_width': 1440,
                'screen_height': 900,
                'platform': 'MacIntel',
                'timezone': 'Asia/Shanghai',
                'locale': 'zh-CN',
                'webgl_vendor': 'Apple Inc.',
                'webgl_renderer': 'Apple GPU'
            },
            {
                'name': 'Windows SOCKS5环境',
                'proxy_enabled': True,
                'proxy_type': 'socks5',
                'proxy_host': '127.0.0.1',
                'proxy_port': 1080,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'viewport_width': 1366,
                'viewport_height': 625,
                'screen_width': 1366,
                'screen_height': 768,
                'platform': 'Win32',
                'timezone': 'Asia/Shanghai',
                'locale': 'zh-CN'
            }
        ]
        
        created_environments = []
        for preset in presets:
            try:
                environment = self.create_environment(user_id, **preset)
                created_environments.append(environment)
            except ValueError:
                # 如果已存在同名配置，跳过
                continue
        
        return created_environments
    
    def generate_random_environment(self, user_id: int, name: str) -> BrowserEnvironment:
        """生成随机浏览器环境"""
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
        
        # 随机选择配置
        resolution = random.choice(resolutions)
        user_agent = random.choice(user_agents)
        
        # 视窗大小通常比屏幕分辨率小一些
        viewport_width = resolution[0] - random.randint(0, 100)
        viewport_height = resolution[1] - random.randint(100, 200)
        
        environment_data = {
            'proxy_enabled': random.choice([True, False]),
            'proxy_type': random.choice(['direct', 'socks5', 'http']) if random.choice([True, False]) else 'direct',
            'proxy_host': '127.0.0.1' if random.choice([True, False]) else None,
            'proxy_port': random.choice([1080, 8080, 3128]) if random.choice([True, False]) else None,
            'user_agent': user_agent,
            'viewport_width': viewport_width,
            'viewport_height': viewport_height,
            'screen_width': resolution[0],
            'screen_height': resolution[1],
            'timezone': 'Asia/Shanghai',
            'locale': 'zh-CN',
            'platform': 'Win32' if 'Windows' in user_agent else 'MacIntel',
            'webgl_vendor': 'Google Inc. (Intel)',
            'webgl_renderer': 'ANGLE (Intel, Intel(R) HD Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)',
        }
        
        # 如果代理未启用，设置为直连
        if not environment_data['proxy_enabled']:
            environment_data['proxy_type'] = 'direct'
            environment_data['proxy_host'] = None
            environment_data['proxy_port'] = None
        
        return self.create_environment(user_id, name, **environment_data)


# 全局浏览器环境服务实例
browser_environment_service = BrowserEnvironmentService()