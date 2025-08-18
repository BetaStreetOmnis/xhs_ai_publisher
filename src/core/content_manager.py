import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import mimetypes

from .logger import logger
from .config import config


@dataclass
class ContentItem:
    """内容项数据结构"""
    id: str
    title: str
    content: str
    images: List[str]
    tags: List[str]
    created_at: float
    status: str = "draft"  # draft, published, failed
    published_at: Optional[float] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentItem':
        """从字典创建实例"""
        return cls(**data)


class ContentManager:
    """内容管理器 - 处理内容的创建、编辑、保存和管理"""
    
    def __init__(self):
        self.storage_dir = None
        self.images_dir = None
        self.content_file = None
        self.contents: Dict[str, ContentItem] = {}
        self._setup_storage()
    
    def _setup_storage(self):
        """设置存储路径"""
        app_dir = Path(config.app.data_dir)
        app_dir.mkdir(exist_ok=True)
        
        self.storage_dir = app_dir / "contents"
        self.storage_dir.mkdir(exist_ok=True)
        
        self.images_dir = self.storage_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
        
        self.content_file = self.storage_dir / "contents.json"
        
        # 加载已有内容
        self._load_contents()
    
    def _load_contents(self):
        """从文件加载内容"""
        if not self.content_file.exists():
            return
        
        try:
            with open(self.content_file, 'r', encoding='utf-8') as f:
                contents_data = json.load(f)
            
            self.contents = {}
            for content_id, data in contents_data.items():
                self.contents[content_id] = ContentItem.from_dict(data)
            
            logger.info(f"已加载 {len(self.contents)} 个内容项")
            
        except Exception as e:
            logger.error(f"加载内容失败: {str(e)}")
            self.contents = {}
    
    def _save_contents(self):
        """保存内容到文件"""
        try:
            contents_data = {}
            for content_id, content in self.contents.items():
                contents_data[content_id] = content.to_dict()
            
            with open(self.content_file, 'w', encoding='utf-8') as f:
                json.dump(contents_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"已保存 {len(self.contents)} 个内容项")
            
        except Exception as e:
            logger.error(f"保存内容失败: {str(e)}")
    
    def _generate_content_id(self, title: str, content: str) -> str:
        """生成内容ID"""
        text = f"{title}_{content}_{time.time()}"
        return hashlib.md5(text.encode()).hexdigest()[:12]
    
    def create_content(self, title: str, content: str, tags: List[str] = None) -> str:
        """创建新内容
        
        Args:
            title: 标题
            content: 内容
            tags: 标签列表
            
        Returns:
            str: 内容ID
        """
        if tags is None:
            tags = []
        
        content_id = self._generate_content_id(title, content)
        
        content_item = ContentItem(
            id=content_id,
            title=title,
            content=content,
            images=[],
            tags=tags,
            created_at=time.time()
        )
        
        self.contents[content_id] = content_item
        self._save_contents()
        
        logger.info(f"创建内容: {content_id} - {title}")
        return content_id
    
    def update_content(self, content_id: str, title: str = None, content: str = None, 
                      tags: List[str] = None) -> bool:
        """更新内容
        
        Args:
            content_id: 内容ID
            title: 新标题
            content: 新内容
            tags: 新标签列表
            
        Returns:
            bool: 更新是否成功
        """
        if content_id not in self.contents:
            logger.error(f"内容不存在: {content_id}")
            return False
        
        content_item = self.contents[content_id]
        
        if title is not None:
            content_item.title = title
        if content is not None:
            content_item.content = content
        if tags is not None:
            content_item.tags = tags
        
        self._save_contents()
        logger.info(f"更新内容: {content_id}")
        return True
    
    def delete_content(self, content_id: str) -> bool:
        """删除内容
        
        Args:
            content_id: 内容ID
            
        Returns:
            bool: 删除是否成功
        """
        if content_id not in self.contents:
            logger.error(f"内容不存在: {content_id}")
            return False
        
        content_item = self.contents[content_id]
        
        # 删除关联的图片文件
        for image_path in content_item.images:
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
            except Exception as e:
                logger.warning(f"删除图片失败: {image_path}, {str(e)}")
        
        # 删除内容项
        del self.contents[content_id]
        self._save_contents()
        
        logger.info(f"删除内容: {content_id}")
        return True
    
    def get_content(self, content_id: str) -> Optional[ContentItem]:
        """获取内容
        
        Args:
            content_id: 内容ID
            
        Returns:
            ContentItem: 内容项，如果不存在返回None
        """
        return self.contents.get(content_id)
    
    def list_contents(self, status: str = None, limit: int = None) -> List[ContentItem]:
        """列出内容
        
        Args:
            status: 状态过滤
            limit: 限制数量
            
        Returns:
            List[ContentItem]: 内容列表
        """
        contents = list(self.contents.values())
        
        # 状态过滤
        if status:
            contents = [c for c in contents if c.status == status]
        
        # 按创建时间倒序排序
        contents.sort(key=lambda x: x.created_at, reverse=True)
        
        # 限制数量
        if limit:
            contents = contents[:limit]
        
        return contents
    
    def save_image(self, image_data: bytes, filename: str = None) -> str:
        """保存图片
        
        Args:
            image_data: 图片二进制数据
            filename: 文件名（可选）
            
        Returns:
            str: 保存的图片路径
        """
        if filename is None:
            # 生成文件名
            timestamp = int(time.time() * 1000)
            filename = f"image_{timestamp}.jpg"
        
        # 确保文件名唯一
        counter = 1
        base_name, ext = os.path.splitext(filename)
        while (self.images_dir / filename).exists():
            filename = f"{base_name}_{counter}{ext}"
            counter += 1
        
        image_path = self.images_dir / filename
        
        try:
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            logger.info(f"保存图片: {image_path}")
            return str(image_path)
            
        except Exception as e:
            logger.error(f"保存图片失败: {str(e)}")
            raise
    
    def add_image_to_content(self, content_id: str, image_path: str) -> bool:
        """为内容添加图片
        
        Args:
            content_id: 内容ID
            image_path: 图片路径
            
        Returns:
            bool: 添加是否成功
        """
        if content_id not in self.contents:
            logger.error(f"内容不存在: {content_id}")
            return False
        
        content_item = self.contents[content_id]
        
        if image_path not in content_item.images:
            content_item.images.append(image_path)
            self._save_contents()
            logger.info(f"为内容 {content_id} 添加图片: {image_path}")
        
        return True
    
    def remove_image_from_content(self, content_id: str, image_path: str) -> bool:
        """从内容中移除图片
        
        Args:
            content_id: 内容ID
            image_path: 图片路径
            
        Returns:
            bool: 移除是否成功
        """
        if content_id not in self.contents:
            logger.error(f"内容不存在: {content_id}")
            return False
        
        content_item = self.contents[content_id]
        
        if image_path in content_item.images:
            content_item.images.remove(image_path)
            self._save_contents()
            logger.info(f"从内容 {content_id} 移除图片: {image_path}")
        
        return True
    
    def update_content_status(self, content_id: str, status: str, 
                             error_message: str = None) -> bool:
        """更新内容状态
        
        Args:
            content_id: 内容ID
            status: 新状态
            error_message: 错误信息（可选）
            
        Returns:
            bool: 更新是否成功
        """
        if content_id not in self.contents:
            logger.error(f"内容不存在: {content_id}")
            return False
        
        content_item = self.contents[content_id]
        content_item.status = status
        
        if status == "published":
            content_item.published_at = time.time()
            content_item.error_message = None
        elif status == "failed":
            content_item.error_message = error_message
        
        self._save_contents()
        logger.info(f"更新内容状态: {content_id} -> {status}")
        return True
    
    def get_content_stats(self) -> Dict[str, int]:
        """获取内容统计信息
        
        Returns:
            Dict[str, int]: 统计信息
        """
        stats = {
            'total': len(self.contents),
            'draft': 0,
            'published': 0,
            'failed': 0
        }
        
        for content in self.contents.values():
            stats[content.status] = stats.get(content.status, 0) + 1
        
        return stats
    
    def validate_content(self, content_item: ContentItem) -> Tuple[bool, List[str]]:
        """验证内容
        
        Args:
            content_item: 内容项
            
        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors = []
        
        # 检查标题
        if not content_item.title or not content_item.title.strip():
            errors.append("标题不能为空")
        elif len(content_item.title) > 100:
            errors.append("标题长度不能超过100字符")
        
        # 检查内容
        if not content_item.content or not content_item.content.strip():
            errors.append("内容不能为空")
        elif len(content_item.content) > 2000:
            errors.append("内容长度不能超过2000字符")
        
        # 检查图片
        if len(content_item.images) > 9:
            errors.append("图片数量不能超过9张")
        
        # 检查图片文件是否存在
        for image_path in content_item.images:
            if not os.path.exists(image_path):
                errors.append(f"图片文件不存在: {image_path}")
        
        # 检查标签
        if len(content_item.tags) > 20:
            errors.append("标签数量不能超过20个")
        
        for tag in content_item.tags:
            if len(tag) > 20:
                errors.append(f"标签长度不能超过20字符: {tag}")
        
        return len(errors) == 0, errors 