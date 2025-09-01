#!/usr/bin/env python3
"""
封面模板测试套件
测试封面模板生成、样式应用、图片处理等功能
"""

import pytest
import os
import tempfile
from PIL import Image, ImageDraw, ImageFont
import json

# 添加项目根目录到路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.core.services.cover_template_service import CoverTemplateService
from src.core.models.cover_template import CoverTemplate

class TestCoverTemplates:
    """封面模板测试类"""
    
    @pytest.fixture
    def template_service(self):
        """创建模板服务实例"""
        return CoverTemplateService()
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    def test_template_service_initialization(self, template_service):
        """测试模板服务初始化"""
        assert template_service is not None
        assert hasattr(template_service, 'generate_cover')
        assert hasattr(template_service, 'get_templates')
    
    def test_minimal_template_generation(self, template_service, temp_dir):
        """测试简约模板生成"""
        output_path = os.path.join(temp_dir, "minimal_test.jpg")
        
        result = template_service.generate_cover(
            template_name="简约文字",
            title="夏日护肤指南",
            subtitle="新手必看",
            output_path=output_path
        )
        
        assert result is not None
        assert os.path.exists(output_path)
        
        # 验证图片尺寸
        with Image.open(output_path) as img:
            assert img.size == (1080, 1080)  # 小红书标准尺寸
    
    def test_gradient_template_generation(self, template_service, temp_dir):
        """测试渐变模板生成"""
        output_path = os.path.join(temp_dir, "gradient_test.jpg")
        
        result = template_service.generate_cover(
            template_name="渐变背景",
            title="时尚穿搭",
            subtitle="2024流行趋势",
            output_path=output_path
        )
        
        assert result is not None
        assert os.path.exists(output_path)
    
    def test_card_template_generation(self, template_service, temp_dir):
        """测试卡片模板生成"""
        output_path = os.path.join(temp_dir, "card_test.jpg")
        
        result = template_service.generate_cover(
            template_name="卡片风格",
            title="护肤步骤",
            subtitle="详细教程",
            output_path=output_path
        )
        
        assert result is not None
        assert os.path.exists(output_path)
    
    def test_fresh_template_generation(self, template_service, temp_dir):
        """测试小清新模板生成"""
        output_path = os.path.join(temp_dir, "fresh_test.jpg")
        
        result = template_service.generate_cover(
            template_name="小清新",
            title="生活记录",
            subtitle="日常分享",
            output_path=output_path
        )
        
        assert result is not None
        assert os.path.exists(output_path)
    
    def test_business_template_generation(self, template_service, temp_dir):
        """测试商务模板生成"""
        output_path = os.path.join(temp_dir, "business_test.jpg")
        
        result = template_service.generate_cover(
            template_name="商务风格",
            title="职场干货",
            subtitle="效率提升",
            output_path=output_path
        )
        
        assert result is not None
        assert os.path.exists(output_path)
    
    def test_custom_background_image(self, template_service, temp_dir):
        """测试自定义背景图片"""
        # 创建测试背景图片
        bg_path = os.path.join(temp_dir, "test_bg.jpg")
        bg_img = Image.new('RGB', (1200, 800), color='lightblue')
        bg_img.save(bg_path)
        
        output_path = os.path.join(temp_dir, "custom_bg_test.jpg")
        
        result = template_service.generate_cover(
            template_name="简约文字",
            title="夏日护肤",
            subtitle="必备指南",
            background_image=bg_path,
            output_path=output_path
        )
        
        assert result is not None
        assert os.path.exists(output_path)
    
    def test_text_overflow_handling(self, template_service, temp_dir):
        """测试文本溢出处理"""
        output_path = os.path.join(temp_dir, "overflow_test.jpg")
        
        # 超长标题
        long_title = "这是一个非常非常非常非常非常非常非常非常非常非常长的标题测试"
        long_subtitle = "这是一个非常非常非常非常非常非常非常非常非常非常非常非常非常非常长的副标题测试"
        
        result = template_service.generate_cover(
            template_name="简约文字",
            title=long_title,
            subtitle=long_subtitle,
            output_path=output_path
        )
        
        assert result is not None
        assert os.path.exists(output_path)
    
    def test_empty_text_handling(self, template_service, temp_dir):
        """测试空文本处理"""
        output_path = os.path.join(temp_dir, "empty_test.jpg")
        
        result = template_service.generate_cover(
            template_name="简约文字",
            title="",
            subtitle="",
            output_path=output_path
        )
        
        assert result is not None
        assert os.path.exists(output_path)
    
    def test_template_config_validation(self):
        """测试模板配置验证"""
        template = CoverTemplate(
            name="测试模板",
            category="测试",
            style_type="test",
            config={
                "background_color": "#ffffff",
                "text_color": "#000000",
                "font_size": 24,
                "invalid_key": "should_be_ignored"
            }
        )
        
        assert template.name == "测试模板"
        assert template.category == "测试"
        assert isinstance(template.config, dict)
        assert "background_color" in template.config
    
    def test_color_validation(self, template_service, temp_dir):
        """测试颜色值验证"""
        output_path = os.path.join(temp_dir, "color_test.jpg")
        
        # 测试无效颜色值
        with pytest.raises(ValueError):
            template_service.generate_cover(
                template_name="简约文字",
                title="测试",
                subtitle="测试",
                custom_colors={"text_color": "invalid_color"},
                output_path=output_path
            )
    
    def test_font_size_validation(self, template_service, temp_dir):
        """测试字体大小验证"""
        output_path = os.path.join(temp_dir, "font_size_test.jpg")
        
        # 测试无效字体大小
        with pytest.raises(ValueError):
            template_service.generate_cover(
                template_name="简约文字",
                title="测试",
                subtitle="测试",
                custom_font_size=5,  # 太小
                output_path=output_path
            )
    
    def test_batch_template_generation(self, template_service, temp_dir):
        """测试批量模板生成"""
        templates = ["简约文字", "渐变背景", "卡片风格", "小清新", "商务风格"]
        results = []
        
        for template_name in templates:
            output_path = os.path.join(temp_dir, f"batch_{template_name}.jpg")
            
            result = template_service.generate_cover(
                template_name=template_name,
                title="批量测试",
                subtitle="模板对比",
                output_path=output_path
            )
            
            assert result is not None
            assert os.path.exists(output_path)
            results.append(result)
        
        assert len(results) == len(templates)
    
    def test_image_quality_validation(self, template_service, temp_dir):
        """测试图片质量验证"""
        output_path = os.path.join(temp_dir, "quality_test.jpg")
        
        result = template_service.generate_cover(
            template_name="简约文字",
            title="质量测试",
            subtitle="高清输出",
            output_path=output_path,
            quality=95
        )
        
        assert result is not None
        assert os.path.exists(output_path)
        
        # 验证图片质量
        with Image.open(output_path) as img:
            assert img.format == 'JPEG'
            assert img.size == (1080, 1080)
    
    def test_template_performance(self, template_service, temp_dir):
        """测试模板生成性能"""
        import time
        
        output_path = os.path.join(temp_dir, "performance_test.jpg")
        
        start_time = time.time()
        
        result = template_service.generate_cover(
            template_name="简约文字",
            title="性能测试",
            subtitle="快速生成",
            output_path=output_path
        )
        
        end_time = time.time()
        
        assert result is not None
        assert os.path.exists(output_path)
        assert (end_time - start_time) < 10  # 生成时间应小于10秒

if __name__ == '__main__':
    pytest.main([__file__, '-v'])