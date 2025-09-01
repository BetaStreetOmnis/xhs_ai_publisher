#!/usr/bin/env python3
"""
小红书AI图片生成集成测试
测试内容：
1. API密钥管理测试
2. AI提供商工厂测试
3. Kimi API适配器测试
4. Qwen API适配器测试
5. 内容分析器测试
6. 风格选择器测试
7. 提示词构建器测试
8. 端到端集成测试
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch
from typing import Dict, List

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.ai_integration.api_key_manager import APIKeyManager
from src.core.ai_integration.ai_provider_factory import AIProviderFactory
from src.core.ai_integration.kimi_adapter import KimiAdapter
from src.core.ai_integration.qwen_adapter import QwenAdapter
from src.core.generation.content_analyzer import ContentAnalyzer, ContentAnalysis
from src.core.generation.style_selector import StyleSelector, StyleType
from src.core.generation.prompt_builder import PromptBuilder

class TestAPIKeyManager:
    """测试API密钥管理器"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.manager = APIKeyManager()
        # 清理测试数据
        if os.path.exists(self.manager.keys_file):
            os.remove(self.manager.keys_file)
    
    def test_add_key(self):
        """测试添加密钥"""
        result = self.manager.add_key('kimi', 'test_key', 'sk-test123')
        assert result is True
        
        keys = self.manager.list_keys()
        assert 'kimi' in keys
        assert 'test_key' in keys['kimi']
    
    def test_get_key(self):
        """测试获取密钥"""
        self.manager.add_key('kimi', 'test_key', 'sk-test123')
        key = self.manager.get_key('kimi', 'test_key')
        assert key == 'sk-test123'
    
    def test_list_keys(self):
        """测试列出密钥"""
        self.manager.add_key('kimi', 'key1', 'sk-test1')
        self.manager.add_key('kimi', 'key2', 'sk-test2')
        self.manager.add_key('qwen', 'key3', 'sk-test3')
        
        keys = self.manager.list_keys()
        assert len(keys['kimi']) == 2
        assert len(keys['qwen']) == 1
    
    def test_remove_key(self):
        """测试删除密钥"""
        self.manager.add_key('kimi', 'test_key', 'sk-test123')
        result = self.manager.remove_key('kimi', 'test_key')
        assert result is True
        
        keys = self.manager.list_keys()
        assert 'test_key' not in keys.get('kimi', [])

class TestAIProviderFactory:
    """测试AI提供商工厂"""
    
    def test_list_providers(self):
        """测试列出提供商"""
        providers = AIProviderFactory.list_providers()
        assert 'kimi' in providers
        assert 'qwen' in providers
        assert 'name' in providers['kimi']
        assert 'description' in providers['qwen']
    
    def test_create_provider(self):
        """测试创建提供商实例"""
        # 使用mock避免真实API调用
        with patch('src.core.ai_integration.kimi_adapter.KimiAdapter.__init__') as mock_init:
            mock_init.return_value = None
            provider = AIProviderFactory.create_provider('kimi', 'test-key')
            assert provider is not None
            mock_init.assert_called_once_with('test-key')
    
    def test_invalid_provider(self):
        """测试无效提供商"""
        with pytest.raises(ValueError):
            AIProviderFactory.create_provider('invalid', 'test-key')

class TestKimiAdapter:
    """测试Kimi API适配器"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.adapter = KimiAdapter('test-key')
    
    def test_init(self):
        """测试初始化"""
        assert self.adapter.api_key == 'test-key'
        assert 'Authorization' in self.adapter.headers
    
    @patch('requests.post')
    def test_generate_image_success(self, mock_post):
        """测试成功生成图片"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'url': 'http://example.com/image.jpg', 'revised_prompt': 'test prompt'}]
        }
        mock_post.return_value = mock_response
        
        result = self.adapter.generate_image('test prompt')
        assert result['success'] is True
        assert 'url' in result
    
    @patch('requests.post')
    def test_generate_image_api_error(self, mock_post):
        """测试API错误"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = 'Bad Request'
        mock_post.return_value = mock_response
        
        result = self.adapter.generate_image('test prompt')
        assert result['success'] is False
        assert 'error' in result
    
    def test_build_xiaohongshu_prompt(self):
        """测试构建小红书提示词"""
        prompt = self.adapter.build_xiaohongshu_prompt('cover', '美妆分享')
        assert '小红书封面图' in prompt
        assert '美妆分享' in prompt

class TestQwenAdapter:
    """测试Qwen API适配器"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.adapter = QwenAdapter('test-key')
    
    def test_init(self):
        """测试初始化"""
        assert self.adapter.api_key == 'test-key'
        assert 'Authorization' in self.adapter.headers
    
    @patch('requests.post')
    def test_generate_image_success(self, mock_post):
        """测试成功生成图片"""
        # 模拟初始响应
        mock_post_response = Mock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {'output': {'task_id': 'test-task-123'}}
        
        # 模拟轮询响应
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            'output': {
                'task_status': 'SUCCEEDED',
                'results': [{'url': 'http://example.com/image.jpg'}]
            }
        }
        
        with patch('requests.get', return_value=mock_get_response):
            mock_post.return_value = mock_post_response
            result = self.adapter.generate_image('test prompt')
            assert result['success'] is True
            assert 'url' in result
    
    def test_build_xiaohongshu_prompt(self):
        """测试构建小红书提示词"""
        prompt = self.adapter.build_xiaohongshu_prompt('cover', '穿搭分享')
        assert '小红书封面图' in prompt
        assert '穿搭分享' in prompt

class TestContentAnalyzer:
    """测试内容分析器"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.analyzer = ContentAnalyzer()
    
    def test_analyze_text_basic(self):
        """测试基础文本分析"""
        text = "今天分享一个超好看的口红，色号真的绝了！#美妆分享 #口红推荐"
        analysis = self.analyzer.analyze_text(text, 'cover')
        
        assert isinstance(analysis, ContentAnalysis)
        assert '美妆' in analysis.topics
        assert len(analysis.keywords) > 0
        assert analysis.sentiment in ['positive', 'negative', 'neutral']
    
    def test_identify_topics(self):
        """测试主题识别"""
        text = "这家咖啡店的环境真的太好了，适合拍照打卡"
        topics = self.analyzer._identify_topics(text)
        assert '美食' in topics
    
    def test_extract_keywords(self):
        """测试关键词提取"""
        text = "学生党必备平价好物分享 #学生党 #平价好物"
        topics = ['生活']
        keywords = self.analyzer._extract_keywords(text, topics)
        assert '学生党' in keywords
        assert '平价好物' in keywords
    
    def test_analyze_sentiment(self):
        """测试情感分析"""
        text = "这个口红真的太好用了，强烈推荐！"
        sentiment = self.analyzer._analyze_sentiment(text)
        assert sentiment == 'positive'
    
    def test_identify_audience(self):
        """测试受众识别"""
        text = "学生党宿舍好物分享，平价又好用"
        audience = self.analyzer._identify_audience(text)
        assert audience == '学生'

class TestStyleSelector:
    """测试风格选择器"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.selector = StyleSelector()
    
    def test_select_style_by_topics(self):
        """测试根据主题选择风格"""
        analysis = {
            'topics': ['美妆'],
            'target_audience': '学生',
            'sentiment': 'positive'
        }
        style = self.selector.select_style(analysis)
        assert style == StyleType.CUTE
    
    def test_select_style_by_audience(self):
        """测试根据受众选择风格"""
        analysis = {
            'topics': ['穿搭'],
            'target_audience': '上班族',
            'sentiment': 'neutral'
        }
        style = self.selector.select_style(analysis)
        assert style == StyleType.PROFESSIONAL
    
    def test_get_style_config(self):
        """测试获取风格配置"""
        config = self.selector.get_style_config(StyleType.CUTE)
        assert config.name == "可爱风"
        assert len(config.colors) > 0
    
    def test_compatible_styles(self):
        """测试兼容风格"""
        styles = self.selector.get_compatible_styles(['美妆'], '学生')
        assert len(styles) > 0
        assert StyleType.CUTE in styles

class TestPromptBuilder:
    """测试提示词构建器"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.builder = PromptBuilder()
    
    def test_build_prompt_cover(self):
        """测试构建封面提示词"""
        content_analysis = {
            'title': '春日美妆分享',
            'topics': ['美妆'],
            'keywords': ['口红', '美妆'],
            'sentiment': 'positive',
            'target_audience': '学生',
            'color_scheme': '粉色系'
        }
        
        style_config = {'name': '可爱风'}
        
        prompt = self.builder.build_prompt(
            content_analysis, 
            style_config, 
            'cover'
        )
        
        assert '小红书' in prompt
        assert '春日美妆分享' in prompt
        assert '粉色系' in prompt
    
    def test_build_prompt_content(self):
        """测试构建内容页提示词"""
        content_analysis = {
            'title': '护肤步骤详解',
            'topics': ['美妆'],
            'keywords': ['护肤', '步骤'],
            'sentiment': 'neutral',
            'target_audience': '上班族',
            'color_scheme': '莫兰迪色系'
        }
        
        style_config = {'name': '简约风'}
        
        prompt = self.builder.build_prompt(
            content_analysis,
            style_config,
            'content'
        )
        
        assert '小红书' in prompt
        assert '护肤步骤详解' in prompt
    
    def test_validate_prompt(self):
        """测试提示词验证"""
        valid_prompt = "小红书可爱风封面图，春日美妆分享，粉色系配色，高清画质，竖版9:16比例"
        result = self.builder.validate_prompt(valid_prompt)
        assert result['is_valid'] is True
        assert result['score'] >= 60
    
    def test_generate_variations(self):
        """测试生成变体"""
        base_prompt = "小红书简约风封面图，美妆分享，粉色系配色"
        variations = self.builder.generate_variations(base_prompt, 2)
        assert len(variations) == 2
        assert all('小红书' in v for v in variations)

class TestEndToEndIntegration:
    """端到端集成测试"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.analyzer = ContentAnalyzer()
        self.style_selector = StyleSelector()
        self.prompt_builder = PromptBuilder()
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        # 1. 分析内容
        text = "学生党平价口红推荐，超显白的色号分享！#美妆分享 #学生党必入"
        analysis = self.analyzer.analyze_text(text, 'cover')
        
        # 2. 选择风格
        style = self.style_selector.select_style({
            'topics': analysis.topics,
            'target_audience': analysis.target_audience,
            'sentiment': analysis.sentiment
        })
        
        # 3. 获取风格配置
        style_config = self.style_selector.get_style_config(style)
        
        # 4. 构建提示词
        prompt = self.prompt_builder.build_prompt(
            {
                'title': analysis.title,
                'topics': analysis.topics,
                'keywords': analysis.keywords,
                'sentiment': analysis.sentiment,
                'target_audience': analysis.target_audience,
                'color_scheme': analysis.color_scheme
            },
            {'name': style_config.name},
            'cover'
        )
        
        # 5. 验证提示词
        validation = self.prompt_builder.validate_prompt(prompt)
        
        # 断言结果
        assert analysis.topics  # 应该有识别的主题
        assert style  # 应该有选择的风格
        assert prompt  # 应该有生成的提示词
        assert validation['is_valid']  # 提示词应该是有效的

if __name__ == '__main__':
    pytest.main([__file__, '-v'])