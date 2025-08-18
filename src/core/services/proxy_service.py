from sqlalchemy.orm import Session
from sqlalchemy import and_
from src.config.database import db_manager
from src.core.models.user import ProxyConfig
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx
import asyncio
import time


class ProxyService:
    """代理配置管理服务"""
    
    def __init__(self):
        self.db_manager = db_manager
    
    def create_proxy_config(self, user_id: int, name: str, host: str, port: int,
                          proxy_type: str = 'http', username: str = None, 
                          password: str = None) -> ProxyConfig:
        """创建代理配置"""
        session = self.db_manager.get_session_direct()
        try:
            # 检查同一用户下是否已有同名配置
            existing_config = session.query(ProxyConfig).filter(
                and_(ProxyConfig.user_id == user_id, ProxyConfig.name == name)
            ).first()
            
            if existing_config:
                raise ValueError(f"代理配置 '{name}' 已存在")
            
            # 如果是第一个代理配置，设为默认
            is_default = session.query(ProxyConfig).filter(
                ProxyConfig.user_id == user_id
            ).count() == 0
            
            proxy_config = ProxyConfig(
                user_id=user_id,
                name=name,
                proxy_type=proxy_type,
                host=host,
                port=port,
                username=username,
                password=password,
                is_default=is_default,
                is_active=True
            )
            
            session.add(proxy_config)
            session.commit()
            session.refresh(proxy_config)
            
            return proxy_config
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_proxy_config_by_id(self, config_id: int) -> Optional[ProxyConfig]:
        """根据ID获取代理配置"""
        session = self.db_manager.get_session_direct()
        try:
            return session.query(ProxyConfig).filter(ProxyConfig.id == config_id).first()
        finally:
            session.close()
    
    def get_user_proxy_configs(self, user_id: int, active_only: bool = True) -> List[ProxyConfig]:
        """获取用户的所有代理配置"""
        session = self.db_manager.get_session_direct()
        try:
            query = session.query(ProxyConfig).filter(ProxyConfig.user_id == user_id)
            if active_only:
                query = query.filter(ProxyConfig.is_active == True)
            return query.order_by(ProxyConfig.is_default.desc(), ProxyConfig.created_at.desc()).all()
        finally:
            session.close()
    
    def get_default_proxy_config(self, user_id: int) -> Optional[ProxyConfig]:
        """获取用户的默认代理配置"""
        session = self.db_manager.get_session_direct()
        try:
            return session.query(ProxyConfig).filter(
                and_(
                    ProxyConfig.user_id == user_id,
                    ProxyConfig.is_default == True,
                    ProxyConfig.is_active == True
                )
            ).first()
        finally:
            session.close()
    
    def set_default_proxy_config(self, user_id: int, config_id: int) -> ProxyConfig:
        """设置默认代理配置"""
        session = self.db_manager.get_session_direct()
        try:
            # 取消用户所有代理配置的默认状态
            session.query(ProxyConfig).filter(
                ProxyConfig.user_id == user_id
            ).update({ProxyConfig.is_default: False})
            
            # 设置指定配置为默认
            target_config = session.query(ProxyConfig).filter(
                and_(ProxyConfig.id == config_id, ProxyConfig.user_id == user_id)
            ).first()
            
            if not target_config:
                raise ValueError(f"代理配置ID {config_id} 不存在")
            
            target_config.is_default = True
            target_config.is_active = True
            target_config.updated_at = datetime.now()
            
            session.commit()
            session.refresh(target_config)
            
            return target_config
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def update_proxy_config(self, config_id: int, **kwargs) -> ProxyConfig:
        """更新代理配置"""
        session = self.db_manager.get_session_direct()
        try:
            proxy_config = session.query(ProxyConfig).filter(ProxyConfig.id == config_id).first()
            if not proxy_config:
                raise ValueError(f"代理配置ID {config_id} 不存在")
            
            # 更新允许的字段
            allowed_fields = [
                'name', 'proxy_type', 'host', 'port', 'username', 'password', 'is_active'
            ]
            
            for field, value in kwargs.items():
                if field in allowed_fields and hasattr(proxy_config, field):
                    setattr(proxy_config, field, value)
            
            proxy_config.updated_at = datetime.now()
            session.commit()
            session.refresh(proxy_config)
            
            return proxy_config
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete_proxy_config(self, config_id: int) -> bool:
        """删除代理配置"""
        session = self.db_manager.get_session_direct()
        try:
            proxy_config = session.query(ProxyConfig).filter(ProxyConfig.id == config_id).first()
            if not proxy_config:
                raise ValueError(f"代理配置ID {config_id} 不存在")
            
            user_id = proxy_config.user_id
            is_default = proxy_config.is_default
            
            session.delete(proxy_config)
            
            # 如果删除的是默认配置，设置另一个配置为默认
            if is_default:
                remaining_config = session.query(ProxyConfig).filter(
                    and_(ProxyConfig.user_id == user_id, ProxyConfig.is_active == True)
                ).first()
                if remaining_config:
                    remaining_config.is_default = True
            
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    async def test_proxy_config(self, config_id: int, timeout: int = 10) -> Dict[str, Any]:
        """测试代理配置连通性"""
        session = self.db_manager.get_session_direct()
        try:
            proxy_config = session.query(ProxyConfig).filter(ProxyConfig.id == config_id).first()
            if not proxy_config:
                raise ValueError(f"代理配置ID {config_id} 不存在")
            
            # 测试代理连通性
            start_time = time.time()
            test_result = False
            latency = None
            error_message = None
            
            try:
                proxy_url = proxy_config.get_proxy_url()
                
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
                        
            except Exception as e:
                error_message = str(e)
            
            # 更新测试结果到数据库
            proxy_config.last_test_time = datetime.now()
            proxy_config.last_test_result = test_result
            proxy_config.test_latency = latency
            proxy_config.updated_at = datetime.now()
            
            session.commit()
            
            return {
                'config_id': config_id,
                'test_result': test_result,
                'latency': latency,
                'error_message': error_message,
                'test_time': proxy_config.last_test_time
            }
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    async def test_all_user_proxies(self, user_id: int) -> List[Dict[str, Any]]:
        """测试用户的所有代理配置"""
        proxy_configs = self.get_user_proxy_configs(user_id, active_only=True)
        
        tasks = []
        for config in proxy_configs:
            task = self.test_proxy_config(config.id)
            tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return [r for r in results if not isinstance(r, Exception)]
        else:
            return []
    
    def get_proxy_config_stats(self, user_id: int) -> Dict[str, Any]:
        """获取用户代理配置统计信息"""
        session = self.db_manager.get_session_direct()
        try:
            configs = session.query(ProxyConfig).filter(ProxyConfig.user_id == user_id).all()
            
            stats = {
                'total_count': len(configs),
                'active_count': len([c for c in configs if c.is_active]),
                'tested_count': len([c for c in configs if c.last_test_time is not None]),
                'working_count': len([c for c in configs if c.last_test_result == True]),
                'default_config': None,
                'avg_latency': None
            }
            
            # 获取默认配置信息
            default_config = next((c for c in configs if c.is_default), None)
            if default_config:
                stats['default_config'] = {
                    'id': default_config.id,
                    'name': default_config.name,
                    'host': default_config.host,
                    'port': default_config.port,
                    'last_test_result': default_config.last_test_result
                }
            
            # 计算平均延迟
            working_configs = [c for c in configs if c.test_latency is not None]
            if working_configs:
                stats['avg_latency'] = sum(c.test_latency for c in working_configs) // len(working_configs)
            
            return stats
            
        finally:
            session.close()

# 全局代理服务实例
proxy_service = ProxyService() 