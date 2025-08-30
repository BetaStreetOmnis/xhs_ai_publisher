from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class CoverTemplate(Base):
    __tablename__ = 'cover_templates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment='模板名称')
    category = Column(String(50), nullable=False, comment='模板分类')
    style_type = Column(String(50), nullable=False, comment='样式类型')
    description = Column(Text, comment='模板描述')
    thumbnail_path = Column(String(255), comment='缩略图路径')
    config = Column(JSON, comment='模板配置JSON')
    is_default = Column(Boolean, default=False, comment='是否为默认模板')
    is_active = Column(Boolean, default=True, comment='是否启用')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'style_type': self.style_type,
            'description': self.description,
            'thumbnail_path': self.thumbnail_path,
            'config': self.config,
            'is_default': self.is_default,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }