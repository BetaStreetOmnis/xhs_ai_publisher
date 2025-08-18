"""
内容管理相关数据模型
包含内容模板、发布历史、定时任务等模型
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

# 从user模块导入Base
from .user import Base


class ContentTemplate(Base):
    """内容模板模型"""
    __tablename__ = 'content_templates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment='用户ID')
    name = Column(String(100), nullable=False, comment='模板名称')
    title = Column(String(200), comment='标题模板')
    content = Column(Text, comment='内容模板')
    tags = Column(Text, comment='标签（JSON数组）')
    category = Column(String(50), comment='分类')
    is_active = Column(Boolean, default=True, comment='是否启用')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关联关系
    user = relationship("User", back_populates="content_templates")
    
    def __repr__(self):
        return f"<ContentTemplate(id={self.id}, name='{self.name}', user_id={self.user_id})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'title': self.title,
            'content': self.content,
            'tags': self.tags,
            'category': self.category,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class PublishHistory(Base):
    """发布历史模型"""
    __tablename__ = 'publish_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment='用户ID')
    template_id = Column(Integer, ForeignKey('content_templates.id'), comment='模板ID')
    title = Column(String(200), nullable=False, comment='发布标题')
    content = Column(Text, nullable=False, comment='发布内容')
    platform = Column(String(50), nullable=False, comment='发布平台')
    status = Column(String(20), default='pending', comment='发布状态: pending, success, failed')
    publish_url = Column(String(500), comment='发布链接')
    error_message = Column(Text, comment='错误信息')
    publish_time = Column(DateTime, comment='发布时间')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    
    # 关联关系
    user = relationship("User", back_populates="publish_history")
    template = relationship("ContentTemplate")
    
    def __repr__(self):
        return f"<PublishHistory(id={self.id}, title='{self.title}', platform='{self.platform}')>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'template_id': self.template_id,
            'title': self.title,
            'content': self.content,
            'platform': self.platform,
            'status': self.status,
            'publish_url': self.publish_url,
            'error_message': self.error_message,
            'publish_time': self.publish_time.isoformat() if self.publish_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ScheduledTask(Base):
    """定时任务模型"""
    __tablename__ = 'scheduled_tasks'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment='用户ID')
    template_id = Column(Integer, ForeignKey('content_templates.id'), comment='模板ID')
    name = Column(String(100), nullable=False, comment='任务名称')
    platform = Column(String(50), nullable=False, comment='发布平台')
    schedule_type = Column(String(20), default='once', comment='调度类型: once, daily, weekly, monthly')
    schedule_time = Column(DateTime, nullable=False, comment='调度时间')
    is_active = Column(Boolean, default=True, comment='是否启用')
    last_run_time = Column(DateTime, comment='最后运行时间')
    next_run_time = Column(DateTime, comment='下次运行时间')
    run_count = Column(Integer, default=0, comment='运行次数')
    created_at = Column(DateTime, default=datetime.utcnow, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment='更新时间')
    
    # 关联关系
    user = relationship("User", back_populates="scheduled_tasks")
    template = relationship("ContentTemplate")
    
    def __repr__(self):
        return f"<ScheduledTask(id={self.id}, name='{self.name}', platform='{self.platform}')>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'template_id': self.template_id,
            'name': self.name,
            'platform': self.platform,
            'schedule_type': self.schedule_type,
            'schedule_time': self.schedule_time.isoformat() if self.schedule_time else None,
            'is_active': self.is_active,
            'last_run_time': self.last_run_time.isoformat() if self.last_run_time else None,
            'next_run_time': self.next_run_time.isoformat() if self.next_run_time else None,
            'run_count': self.run_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 