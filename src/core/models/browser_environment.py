"""
浏览器环境配置模型
包含代理配置、浏览器指纹等完整环境信息
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship

# 从user.py导入共享的Base
from .user import Base


class BrowserEnvironment(Base):
    """浏览器环境配置模型（合并代理和指纹）"""
    __tablename__ = 'browser_environments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment='用户ID')
    name = Column(String(100), nullable=False, comment='环境配置名称')
    
    # 代理配置
    proxy_enabled = Column(Boolean, default=False, comment='是否启用代理')
    proxy_type = Column(String(20), comment='代理类型: http, https, socks5, direct')
    proxy_host = Column(String(255), comment='代理主机')
    proxy_port = Column(Integer, comment='代理端口')
    proxy_username = Column(String(100), comment='代理用户名')
    proxy_password = Column(String(100), comment='代理密码')
    
    # 浏览器指纹配置
    user_agent = Column(Text, comment='用户代理字符串')
    viewport_width = Column(Integer, default=1920, comment='视窗宽度')
    viewport_height = Column(Integer, default=1080, comment='视窗高度')
    screen_width = Column(Integer, default=1920, comment='屏幕宽度')
    screen_height = Column(Integer, default=1080, comment='屏幕高度')
    platform = Column(String(50), comment='平台信息')
    timezone = Column(String(50), default='Asia/Shanghai', comment='时区')
    locale = Column(String(20), default='zh-CN', comment='语言环境')
    
    # WebGL指纹
    webgl_vendor = Column(String(100), comment='WebGL供应商')
    webgl_renderer = Column(String(200), comment='WebGL渲染器')
    
    # 其他指纹信息
    canvas_fingerprint = Column(String(100), comment='Canvas指纹')
    webrtc_public_ip = Column(String(50), comment='WebRTC公网IP')
    webrtc_local_ip = Column(String(50), comment='WebRTC本地IP')
    fonts = Column(Text, comment='字体列表(JSON)')
    plugins = Column(Text, comment='插件列表(JSON)')
    
    # 地理位置
    geolocation_latitude = Column(String(20), comment='地理位置纬度')
    geolocation_longitude = Column(String(20), comment='地理位置经度')
    
    # 高级配置
    extra_config = Column(JSON, comment='额外配置(JSON格式)')
    
    # 状态信息
    is_active = Column(Boolean, default=True, comment='是否启用')
    is_default = Column(Boolean, default=False, comment='是否为默认环境')
    
    # 测试信息
    last_test_at = Column(DateTime, comment='最后测试时间')
    test_success = Column(Boolean, comment='最后测试是否成功')
    test_latency = Column(Float, comment='测试延迟(毫秒)')
    test_result = Column(Text, comment='测试结果详情')
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关联关系
    user = relationship("User", back_populates="browser_environments")
    
    def __repr__(self):
        return f"<BrowserEnvironment(id={self.id}, name='{self.name}', user_id={self.user_id})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            
            # 代理信息
            'proxy_enabled': self.proxy_enabled,
            'proxy_type': self.proxy_type,
            'proxy_host': self.proxy_host,
            'proxy_port': self.proxy_port,
            'proxy_username': self.proxy_username,
            'proxy_display': self.get_proxy_display(),
            
            # 指纹信息
            'user_agent': self.user_agent,
            'viewport_width': self.viewport_width,
            'viewport_height': self.viewport_height,
            'screen_width': self.screen_width,
            'screen_height': self.screen_height,
            'platform': self.platform,
            'timezone': self.timezone,
            'locale': self.locale,
            'resolution_display': f"{self.viewport_width}x{self.viewport_height}",
            
            # 状态信息
            'is_active': self.is_active,
            'is_default': self.is_default,
            'test_success': self.test_success,
            'test_latency': self.test_latency,
            'last_test_at': self.last_test_at.isoformat() if self.last_test_at else None,
            
            # 时间信息
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_proxy_display(self):
        """获取代理显示文本"""
        if not self.proxy_enabled or not self.proxy_type:
            return "直连"
        
        if self.proxy_type == 'direct':
            return "直连"
        
        return f"{self.proxy_type}://{self.proxy_host}:{self.proxy_port}"
    
    def get_proxy_url(self):
        """获取代理URL"""
        if not self.proxy_enabled or self.proxy_type == 'direct':
            return None
            
        if self.proxy_username and self.proxy_password:
            return f"{self.proxy_type}://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}"
        else:
            return f"{self.proxy_type}://{self.proxy_host}:{self.proxy_port}"
    
    def get_browser_config(self):
        """获取浏览器配置"""
        config = {
            'user_agent': self.user_agent,
            'viewport': {
                'width': self.viewport_width,
                'height': self.viewport_height
            },
            'screen': {
                'width': self.screen_width,
                'height': self.screen_height
            },
            'locale': self.locale,
            'timezone_id': self.timezone,
            'geolocation': None
        }
        
        # 添加地理位置
        if self.geolocation_latitude and self.geolocation_longitude:
            config['geolocation'] = {
                'latitude': float(self.geolocation_latitude),
                'longitude': float(self.geolocation_longitude)
            }
        
        # 添加代理配置
        if self.proxy_enabled and self.proxy_type != 'direct':
            config['proxy'] = {
                'server': self.get_proxy_url()
            }
        
        return config
    
    def get_fingerprint_config(self):
        """获取指纹配置"""
        return {
            'user_agent': self.user_agent,
            'platform': self.platform,
            'webgl_vendor': self.webgl_vendor,
            'webgl_renderer': self.webgl_renderer,
            'canvas_fingerprint': self.canvas_fingerprint,
            'fonts': self.fonts,
            'plugins': self.plugins,
            'webrtc_public_ip': self.webrtc_public_ip,
            'webrtc_local_ip': self.webrtc_local_ip
        }