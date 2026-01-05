#!/usr/bin/env python3
"""
用户管理测试套件
测试用户创建、代理配置、浏览器指纹等功能
"""

import pytest
import asyncio
import os
import tempfile
from datetime import datetime

# 添加项目根目录到路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.services.fingerprint_service import FingerprintService
from src.core.services.proxy_service import ProxyService
from src.config.database import db_manager

class TestUserManagement:
    """用户管理测试类"""
    
    @pytest.fixture
    def fingerprint_service(self):
        """创建指纹服务实例"""
        return FingerprintService()
    
    @pytest.fixture
    def proxy_service(self):
        """创建代理服务实例"""
        return ProxyService()
    
    def test_fingerprint_service_initialization(self, fingerprint_service):
        """测试指纹服务初始化"""
        assert fingerprint_service is not None
        assert hasattr(fingerprint_service, 'create_fingerprint')
        assert hasattr(fingerprint_service, 'generate_random_fingerprint')
    
    def test_proxy_service_initialization(self, proxy_service):
        """测试代理服务初始化"""
        assert proxy_service is not None
        assert hasattr(proxy_service, 'create_proxy_config')
        assert hasattr(proxy_service, 'test_proxy_config')
    
    def test_random_fingerprint_generation(self, fingerprint_service):
        """测试随机指纹生成"""
        # 创建测试用户
        user_id = 1  # 模拟用户ID
        
        fingerprint = fingerprint_service.generate_random_fingerprint(
            user_id, "测试随机指纹"
        )
        
        assert fingerprint is not None
        assert fingerprint.user_id == user_id
        assert fingerprint.name == "测试随机指纹"
        assert fingerprint.user_agent is not None
        assert fingerprint.viewport_width > 0
        assert fingerprint.viewport_height > 0
    
    def test_preset_fingerprints_creation(self, fingerprint_service):
        """测试预设指纹创建"""
        user_id = 1
        
        fingerprints = fingerprint_service.create_preset_fingerprints(user_id)
        
        assert fingerprints is not None
        assert len(fingerprints) > 0
        
        # 验证每个指纹
        for fingerprint in fingerprints:
            assert fingerprint.user_id == user_id
            assert fingerprint.name is not None
            assert fingerprint.user_agent is not None
    
    def test_proxy_config_creation(self, proxy_service):
        """测试代理配置创建"""
        user_id = 1
        
        proxy_config = proxy_service.create_proxy_config(
            user_id=user_id,
            name="测试代理",
            host="127.0.0.1",
            port=8080,
            proxy_type="http"
        )
        
        assert proxy_config is not None
        assert proxy_config.user_id == user_id
        assert proxy_config.name == "测试代理"
        assert proxy_config.host == "127.0.0.1"
        assert proxy_config.port == 8080
        assert proxy_config.proxy_type == "http"
    
    def test_proxy_url_generation(self, proxy_service):
        """测试代理URL生成"""
        user_id = 1
        
        # 无认证代理
        proxy1 = proxy_service.create_proxy_config(
            user_id=user_id,
            name="无认证代理",
            host="127.0.0.1",
            port=8080,
            proxy_type="http"
        )
        
        url1 = proxy1.get_proxy_url()
        assert url1 == "http://127.0.0.1:8080"
        
        # 有认证代理
        proxy2 = proxy_service.create_proxy_config(
            user_id=user_id,
            name="认证代理",
            host="127.0.0.1",
            port=8080,
            proxy_type="http",
            username="user",
            password="pass"
        )
        
        url2 = proxy2.get_proxy_url()
        assert "user:pass@127.0.0.1:8080" in url2
    
    def test_default_config_setting(self, fingerprint_service):
        """测试默认配置设置"""
        user_id = 1
        
        # 创建多个指纹
        fingerprint1 = fingerprint_service.create_fingerprint(
            user_id=user_id,
            name="指纹1",
            user_agent="Test UA 1"
        )
        
        fingerprint2 = fingerprint_service.create_fingerprint(
            user_id=user_id,
            name="指纹2",
            user_agent="Test UA 2"
        )
        
        # 设置默认
        default_fingerprint = fingerprint_service.set_default_fingerprint(
            user_id=user_id,
            fingerprint_id=fingerprint2.id
        )
        
        assert default_fingerprint.id == fingerprint2.id
        assert default_fingerprint.is_default is True
        
        # 验证其他不再是默认
        updated_fingerprint1 = fingerprint_service.get_fingerprint_by_id(fingerprint1.id)
        assert updated_fingerprint1.is_default is False
    
    def test_proxy_stats_generation(self, proxy_service):
        """测试代理统计生成"""
        user_id = 1
        
        # 创建多个代理配置
        proxy1 = proxy_service.create_proxy_config(
            user_id=user_id,
            name="代理1",
            host="127.0.0.1",
            port=8080
        )
        
        proxy2 = proxy_service.create_proxy_config(
            user_id=user_id,
            name="代理2",
            host="127.0.0.1",
            port=8081
        )
        
        # 生成统计
        stats = proxy_service.get_proxy_config_stats(user_id)
        
        assert stats is not None
        assert stats['total_count'] == 2
        assert stats['active_count'] == 2
    
    def test_fingerprint_stats_generation(self, fingerprint_service):
        """测试指纹统计生成"""
        user_id = 1
        
        # 创建多个指纹
        fingerprint_service.create_preset_fingerprints(user_id)
        
        # 生成统计
        stats = fingerprint_service.get_fingerprint_stats(user_id)
        
        assert stats is not None
        assert stats['total_count'] > 0
        assert 'platforms' in stats
        assert 'user_agents' in stats
    
    @pytest.mark.asyncio
    async def test_proxy_connection_test(self, proxy_service):
        """测试代理连接测试"""
        user_id = 1
        
        proxy_config = proxy_service.create_proxy_config(
            user_id=user_id,
            name="测试连接",
            host="127.0.0.1",
            port=8080
        )
        
        # 测试连接（预期失败，因为是测试地址）
        result = await proxy_service.test_proxy_config(proxy_config.id)
        
        assert result is not None
        assert 'config_id' in result
        assert 'test_result' in result
        assert 'latency' in result
        assert 'error_message' in result
    
    def test_user_proxy_relationship(self, proxy_service):
        """测试用户和代理的关系"""
        user_id = 1
        
        # 创建多个代理
        proxy1 = proxy_service.create_proxy_config(
            user_id=user_id,
            name="用户代理1",
            host="127.0.0.1",
            port=8080
        )
        
        proxy2 = proxy_service.create_proxy_config(
            user_id=user_id,
            name="用户代理2",
            host="127.0.0.1",
            port=8081
        )
        
        # 获取用户所有代理
        user_proxies = proxy_service.get_user_proxy_configs(user_id)
        
        assert len(user_proxies) == 2
        assert all(proxy.user_id == user_id for proxy in user_proxies)
    
    def test_duplicate_name_prevention(self, proxy_service):
        """测试重复名称防止"""
        user_id = 1
        
        # 第一次创建应该成功
        proxy1 = proxy_service.create_proxy_config(
            user_id=user_id,
            name="唯一名称",
            host="127.0.0.1",
            port=8080
        )
        
        assert proxy1 is not None
        
        # 第二次创建相同名称应该失败
        with pytest.raises(ValueError):
            proxy_service.create_proxy_config(
                user_id=user_id,
                name="唯一名称",
                host="127.0.0.1",
                port=8081
            )
    
    def test_config_update(self, proxy_service):
        """测试配置更新"""
        user_id = 1
        
        proxy = proxy_service.create_proxy_config(
            user_id=user_id,
            name="待更新代理",
            host="127.0.0.1",
            port=8080
        )
        
        # 更新配置
        updated_proxy = proxy_service.update_proxy_config(
            config_id=proxy.id,
            name="已更新代理",
            port=9090
        )
        
        assert updated_proxy.name == "已更新代理"
        assert updated_proxy.port == 9090

if __name__ == '__main__':
    pytest.main([__file__, '-v'])