"""
用户相关数据模型
包含用户、代理配置、浏览器指纹等模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

# 创建基类（这里直接创建，避免循环导入）
Base = declarative_base()


class User(Base):
    """用户模型"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment='用户名')
    phone = Column(String(20), unique=True, nullable=False, comment='手机号')
    display_name = Column(String(100), comment='显示名称')
    is_active = Column(Boolean, default=True, comment='是否激活')
    is_current = Column(Boolean, default=False, comment='是否为当前用户')
    is_logged_in = Column(Boolean, default=False, comment='是否已登录')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    last_login_at = Column(DateTime, comment='最后登录时间')
    
    # 关联关系
    proxy_configs = relationship("ProxyConfig", back_populates="user", cascade="all, delete-orphan")
    browser_fingerprints = relationship("BrowserFingerprint", back_populates="user", cascade="all, delete-orphan")
    content_templates = relationship("ContentTemplate", back_populates="user", cascade="all, delete-orphan")
    publish_history = relationship("PublishHistory", back_populates="user", cascade="all, delete-orphan")
    scheduled_tasks = relationship("ScheduledTask", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', phone='{self.phone}')>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'username': self.username,
            'phone': self.phone,
            'display_name': self.display_name,
            'is_active': self.is_active,
            'is_current': self.is_current,
            'is_logged_in': self.is_logged_in,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None
        }


class ProxyConfig(Base):
    """代理配置模型"""
    __tablename__ = 'proxy_configs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment='用户ID')
    name = Column(String(100), nullable=False, comment='配置名称')
    proxy_type = Column(String(20), nullable=False, comment='代理类型: http, https, socks5')
    host = Column(String(255), nullable=False, comment='代理主机')
    port = Column(Integer, nullable=False, comment='代理端口')
    username = Column(String(100), comment='代理用户名')
    password = Column(String(100), comment='代理密码')
    is_active = Column(Boolean, default=True, comment='是否启用')
    is_default = Column(Boolean, default=False, comment='是否为默认代理')
    test_url = Column(String(500), default='https://httpbin.org/ip', comment='测试URL')
    test_latency = Column(Float, comment='测试延迟(毫秒)')
    test_success = Column(Boolean, comment='最后测试是否成功')
    last_test_at = Column(DateTime, comment='最后测试时间')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关联关系
    user = relationship("User", back_populates="proxy_configs")
    
    def __repr__(self):
        return f"<ProxyConfig(id={self.id}, name='{self.name}', host='{self.host}:{self.port}')>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'proxy_type': self.proxy_type,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'test_url': self.test_url,
            'test_latency': self.test_latency,
            'test_success': self.test_success,
            'last_test_at': self.last_test_at.isoformat() if self.last_test_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_proxy_url(self):
        """获取代理URL"""
        if self.username and self.password:
            return f"{self.proxy_type}://{self.username}:{self.password}@{self.host}:{self.port}"
        else:
            return f"{self.proxy_type}://{self.host}:{self.port}"


class BrowserFingerprint(Base):
    """浏览器指纹模型"""
    __tablename__ = 'browser_fingerprints'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment='用户ID')
    name = Column(String(100), nullable=False, comment='指纹配置名称')
    user_agent = Column(Text, comment='用户代理字符串')
    viewport_width = Column(Integer, default=1920, comment='视窗宽度')
    viewport_height = Column(Integer, default=1080, comment='视窗高度')
    screen_width = Column(Integer, default=1920, comment='屏幕宽度')
    screen_height = Column(Integer, default=1080, comment='屏幕高度')
    platform = Column(String(50), comment='平台信息')
    timezone = Column(String(50), default='Asia/Shanghai', comment='时区')
    locale = Column(String(20), default='zh-CN', comment='语言环境')
    webgl_vendor = Column(String(100), comment='WebGL供应商')
    webgl_renderer = Column(String(200), comment='WebGL渲染器')
    canvas_fingerprint = Column(String(100), comment='Canvas指纹')
    webrtc_public_ip = Column(String(50), comment='WebRTC公网IP')
    webrtc_local_ip = Column(String(50), comment='WebRTC本地IP')
    fonts = Column(Text, comment='字体列表(JSON)')
    plugins = Column(Text, comment='插件列表(JSON)')
    is_active = Column(Boolean, default=True, comment='是否启用')
    is_default = Column(Boolean, default=False, comment='是否为默认指纹')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关联关系
    user = relationship("User", back_populates="browser_fingerprints")
    
    def __repr__(self):
        return f"<BrowserFingerprint(id={self.id}, name='{self.name}', platform='{self.platform}')>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'user_agent': self.user_agent,
            'viewport_width': self.viewport_width,
            'viewport_height': self.viewport_height,
            'screen_width': self.screen_width,
            'screen_height': self.screen_height,
            'platform': self.platform,
            'timezone': self.timezone,
            'locale': self.locale,
            'webgl_vendor': self.webgl_vendor,
            'webgl_renderer': self.webgl_renderer,
            'canvas_fingerprint': self.canvas_fingerprint,
            'webrtc_public_ip': self.webrtc_public_ip,
            'webrtc_local_ip': self.webrtc_local_ip,
            'fonts': self.fonts,
            'plugins': self.plugins,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 