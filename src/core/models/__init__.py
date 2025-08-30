"""
数据模型包初始化文件
包含所有数据模型类的导入
"""

# 从user模块导入Base和所有模型类
from .user import Base, User, ProxyConfig, BrowserFingerprint
from .browser_environment import BrowserEnvironment
from .content import ContentTemplate, PublishHistory, ScheduledTask
from .cover_template import CoverTemplate

# 公开的模型接口
__all__ = [
    'Base',
    'User',
    'ProxyConfig', 
    'BrowserFingerprint',
    'BrowserEnvironment',
    'ContentTemplate',
    'PublishHistory',
    'ScheduledTask',
    'CoverTemplate'
] 