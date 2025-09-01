#!/usr/bin/env python3
"""
AI内容生成测试套件
测试内容生成、模板处理、标签推荐等功能
"""

import pytest
import os
import json
import tempfile
from unittest.mock import Mock, patch

# 添加项目根目录到路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.processor.content import ContentProcessor
from src.core.processor.img import ImageProcessor
from src.core.models.user import User

class TestAIContent:
    """AI内容生成测试类"""
    
    @pytest.fixture
    def content_processor(self):
        """创建内容处理器实例"""
        return ContentProcessor()
    
    @pytest.fixture
    def image_processor(self):
        """创建图片处理器实例"""
        return ImageProcessor()
    
    def test_content_processor_initialization(self, content_processor):
        """测试内容处理器初始化"""
        assert content_processor is not None
        assert hasattr(content_processor, 'generate_content')
        assert hasattr(content_processor, 'generate_title')
    
    def test_title_generation(self, content_processor):
        """测试标题生成功能"""
        topic = "夏日护肤"
        title = content_processor.generate_title(topic)
        
        assert title is not None
        assert isinstance(title, str)
        assert len(title) > 5  # 标题应该有一定长度
        assert len(title) < 50  # 小红书标题不宜过长
    
    def test_content_generation(self, content_processor):
        """测试内容生成功能"""
        topic = "夏日护肤"
        title = "夏日护肤必备指南"
        
        content = content_processor.generate_content(topic, title)
        
        assert content is not None
        assert isinstance(content, str)
        assert len(content) > 100  # 内容应该有一定长度
        assert "夏日" in content or "护肤" in content
    
    def test_hashtag_generation(self, content_processor):
        """测试标签生成功能"""
        topic = "夏日护肤"
        content = "夏日护肤非常重要，要注意防晒和补水..."
        
        hashtags = content_processor.generate_hashtags(topic, content)
        
        assert hashtags is not None
        assert isinstance(hashtags, list)
        assert len(hashtags) > 0
        assert len(hashtags) <= 10  # 标签数量限制
        assert all(ishtag.startswith('#') for hashtag in hashtags)
    
    def test_content_template_processing(self, content_processor):
        """测试内容模板处理"""
        template = {
            "title": "{topic}完全指南",
            "content": "关于{topic}，你需要知道以下几点：\n{points}",
            "hashtags": ["#{topic}", "#指南", "#必备"]
        }
        
        data = {
            "topic": "夏日防晒",
            "points": "1. 选择合适的防晒霜\n2. 每2小时补涂\n3. 物理防晒也很重要"
        }
        
        result = content_processor.process_template(template, data)
        
        assert result is not None
        assert "夏日防晒完全指南" in result["title"]
        assert "夏日防晒" in result["content"]
        assert "#夏日防晒" in result["hashtags"]
    
    def test_image_search_and_processing(self, image_processor):
        """测试图片搜索和处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试图片
            test_image_path = os.path.join(temp_dir, "test.jpg")
            
            # 模拟图片搜索
            images = image_processor.search_images("夏日护肤")
            
            assert isinstance(images, list)
            # 实际测试时可能需要网络连接
    
    def test_image_resizing(self, image_processor):
        """测试图片尺寸调整"""
        from PIL import Image
        import numpy as np
        
        # 创建测试图片
        test_img = Image.new('RGB', (1000, 800), color='red')
        
        # 调整尺寸
        resized_img = image_processor.resize_image(test_img, (800, 800))
        
        assert resized_img.size == (800, 800)
    
    def test_content_length_validation(self, content_processor):
        """测试内容长度验证"""
        # 小红书内容长度限制
        max_length = 1000
        
        # 生成内容
        content = content_processor.generate_content("测试", "测试标题")
        
        # 验证长度
        assert len(content) <= max_length
    
    def test_empty_topic_handling(self, content_processor):
        """测试空主题处理"""
        with pytest.raises(ValueError):
            content_processor.generate_title("")
    
    def test_special_character_handling(self, content_processor):
        """测试特殊字符处理"""
        topic = "夏日护肤@2023!"
        title = content_processor.generate_title(topic)
        
        # 应该清理特殊字符
        assert '@' not in title or '!' not in title
    
    def test_content_uniqueness(self, content_processor):
        """测试内容唯一性"""
        topic = "测试唯一性"
        
        content1 = content_processor.generate_content(topic, "测试标题1")
        content2 = content_processor.generate_content(topic, "测试标题2")
        
        # 相同主题但不同标题应该产生不同内容
        assert content1 != content2

if __name__ == '__main__':
    pytest.main([__file__, '-v'])