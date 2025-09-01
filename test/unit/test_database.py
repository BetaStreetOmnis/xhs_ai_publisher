#!/usr/bin/env python3
"""
数据库功能测试套件
测试数据库连接、模型创建、CRUD操作等
"""

import pytest
import os
import tempfile
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.config.database import DatabaseManager
from src.core.models.user import User, ProxyConfig, BrowserFingerprint
from src.core.models.cover_template import CoverTemplate

class TestDatabase:
    """数据库测试类"""
    
    @pytest.fixture
    def temp_db(self):
        """创建临时数据库用于测试"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        # 创建临时数据库
        engine = create_engine(f'sqlite:///{db_path}')
        from src.core.models.user import Base as UserBase
        from src.core.models.cover_template import Base as TemplateBase
        UserBase.metadata.create_all(engine)
        TemplateBase.metadata.create_all(engine)
        
        yield engine, db_path
        
        # 清理
        os.unlink(db_path)
    
    def test_database_connection(self, temp_db):
        """测试数据库连接"""
        engine, db_path = temp_db
        assert engine is not None
        
        # 测试连接
        connection = engine.connect()
        assert connection is not None
        connection.close()
    
    def test_user_creation(self, temp_db):
        """测试用户创建"""
        engine, db_path = temp_db
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # 创建用户
        user = User(
            username='test_user',
            phone='13800138000',
            display_name='测试用户',
            is_active=True,
            is_current=True
        )
        session.add(user)
        session.commit()
        
        # 验证创建
        assert user.id is not None
        assert user.username == 'test_user'
        assert user.phone == '13800138000'
        assert user.is_active is True
        
        session.close()
    
    def test_proxy_config_creation(self, temp_db):
        """测试代理配置创建"""
        engine, db_path = temp_db
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # 先创建用户
        user = User(username='proxy_user', phone='13900139000')
        session.add(user)
        session.commit()
        
        # 创建代理配置
        proxy = ProxyConfig(
            user_id=user.id,
            name='测试代理',
            proxy_type='http',
            host='127.0.0.1',
            port=8080,
            is_active=True
        )
        session.add(proxy)
        session.commit()
        
        assert proxy.id is not None
        assert proxy.name == '测试代理'
        assert proxy.user_id == user.id
        
        session.close()
    
    def test_browser_fingerprint_creation(self, temp_db):
        """测试浏览器指纹创建"""
        engine, db_path = temp_db
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # 创建用户
        user = User(username='fingerprint_user', phone='13700137000')
        session.add(user)
        session.commit()
        
        # 创建指纹配置
        fingerprint = BrowserFingerprint(
            user_id=user.id,
            name='测试指纹',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport_width=1920,
            viewport_height=1080,
            platform='Win32'
        )
        session.add(fingerprint)
        session.commit()
        
        assert fingerprint.id is not None
        assert fingerprint.name == '测试指纹'
        assert fingerprint.platform == 'Win32'
        
        session.close()
    
    def test_cover_template_creation(self, temp_db):
        """测试封面模板创建"""
        engine, db_path = temp_db
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # 创建模板
        template = CoverTemplate(
            name='测试模板',
            category='简约',
            style_type='minimal',
            description='这是一个测试模板',
            config={
                'background_color': '#ffffff',
                'text_color': '#000000',
                'font_size': 24
            },
            is_active=True
        )
        session.add(template)
        session.commit()
        
        assert template.id is not None
        assert template.name == '测试模板'
        assert template.category == '简约'
        assert isinstance(template.config, dict)
        
        session.close()
    
    def test_user_proxy_relationship(self, temp_db):
        """测试用户和代理的关系"""
        engine, db_path = temp_db
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # 创建用户和多个代理
        user = User(username='multi_proxy_user', phone='13600136000')
        session.add(user)
        session.commit()
        
        proxy1 = ProxyConfig(
            user_id=user.id,
            name='代理1',
            proxy_type='http',
            host='127.0.0.1',
            port=8080
        )
        
        proxy2 = ProxyConfig(
            user_id=user.id,
            name='代理2',
            proxy_type='https',
            host='127.0.0.1',
            port=8443
        )
        
        session.add_all([proxy1, proxy2])
        session.commit()
        
        # 验证关系
        user_from_db = session.query(User).filter_by(id=user.id).first()
        assert len(user_from_db.proxy_configs) == 2
        assert user_from_db.proxy_configs[0].name in ['代理1', '代理2']
        
        session.close()
    
    def test_database_manager_integration(self):
        """测试数据库管理器集成"""
        # 创建临时目录
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            # 模拟数据库管理器
            from src.config.database import db_manager
            
            # 测试数据库路径
            assert db_manager.db_path is not None
            assert os.path.exists(os.path.dirname(db_manager.db_path))

if __name__ == '__main__':
    pytest.main([__file__, '-v'])