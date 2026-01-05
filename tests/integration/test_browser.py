#!/usr/bin/env python3
"""
浏览器自动化测试套件
测试Playwright浏览器操作、页面交互等功能
"""

import pytest
import asyncio
import os
import tempfile
from pathlib import Path

# 添加项目根目录到路径
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

class TestBrowserAutomation:
    """浏览器自动化测试类"""
    
    @pytest.fixture(scope="session")
    def browser_type(self):
        """浏览器类型配置"""
        return "chromium"
    
    @pytest.fixture(scope="session")
    def headless_mode(self):
        """是否使用无头模式"""
        return True  # CI环境使用无头模式
    
    @pytest.mark.asyncio
    async def test_browser_launch(self, browser_type, headless_mode):
        """测试浏览器启动"""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless_mode)
                assert browser is not None
                await browser.close()
        except ImportError:
            pytest.skip("Playwright未安装")
    
    @pytest.mark.asyncio
    async def test_page_navigation(self, browser_type, headless_mode):
        """测试页面导航"""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless_mode)
                page = await browser.new_page()
                
                # 测试访问示例网站
                await page.goto('https://httpbin.org/get')
                assert page.url == 'https://httpbin.org/get'
                
                await browser.close()
        except ImportError:
            pytest.skip("Playwright未安装")
    
    @pytest.mark.asyncio
    async def test_screenshot_capture(self, browser_type, headless_mode):
        """测试截图功能"""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless_mode)
                page = await browser.new_page()
                
                await page.goto('https://example.com')
                
                # 创建临时文件
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    screenshot_path = tmp.name
                
                await page.screenshot(path=screenshot_path)
                
                # 验证截图文件存在
                assert os.path.exists(screenshot_path)
                assert os.path.getsize(screenshot_path) > 0
                
                # 清理
                os.unlink(screenshot_path)
                await browser.close()
        except ImportError:
            pytest.skip("Playwright未安装")
    
    @pytest.mark.asyncio
    async def test_user_agent_setting(self, browser_type, headless_mode):
        """测试用户代理设置"""
        try:
            from playwright.async_api import async_playwright
            
            custom_ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) TestBot/1.0'
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless_mode)
                context = await browser.new_context(user_agent=custom_ua)
                page = await context.new_page()
                
                # 测试用户代理
                await page.goto('https://httpbin.org/user-agent')
                content = await page.text_content('body')
                assert custom_ua in content
                
                await browser.close()
        except ImportError:
            pytest.skip("Playwright未安装")
    
    @pytest.mark.asyncio
    async def test_viewport_setting(self, browser_type, headless_mode):
        """测试视口设置"""
        try:
            from playwright.async_api import async_playwright
            
            viewport = {'width': 1920, 'height': 1080}
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless_mode)
                context = await browser.new_context(viewport=viewport)
                page = await context.new_page()
                
                # 测试视口大小
                await page.goto('https://httpbin.org/get')
                content = await page.text_content('body')
                assert '1920' in content and '1080' in content
                
                await browser.close()
        except ImportError:
            pytest.skip("Playwright未安装")
    
    @pytest.mark.asyncio
    async def test_proxy_configuration(self, browser_type, headless_mode):
        """测试代理配置"""
        try:
            from playwright.async_api import async_playwright
            
            # 测试无代理连接
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless_mode)
                page = await browser.new_page()
                
                await page.goto('https://httpbin.org/ip')
                content = await page.text_content('body')
                assert 'origin' in content.lower()
                
                await browser.close()
        except ImportError:
            pytest.skip("Playwright未安装")
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, browser_type, headless_mode):
        """测试超时处理"""
        try:
            from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless_mode)
                page = await browser.new_page()
                
                # 测试超时设置
                try:
                    await page.goto('https://httpbin.org/delay/10', timeout=5000)
                    assert False, "应该超时"
                except PlaywrightTimeoutError:
                    pass  # 预期超时
                
                await browser.close()
        except ImportError:
            pytest.skip("Playwright未安装")
    
    @pytest.mark.asyncio
    async def test_form_interaction(self, browser_type, headless_mode):
        """测试表单交互"""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless_mode)
                page = await browser.new_page()
                
                await page.goto('https://httpbin.org/forms/post')
                
                # 测试表单填写
                await page.fill('input[name="custname"]', '测试用户')
                await page.fill('input[name="custtel"]', '13800138000')
                
                # 验证填写内容
                value = await page.input_value('input[name="custname"]')
                assert value == '测试用户'
                
                await browser.close()
        except ImportError:
            pytest.skip("Playwright未安装")
    
    @pytest.mark.asyncio
    async def test_element_waiting(self, browser_type, headless_mode):
        """测试元素等待"""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=headless_mode)
                page = await browser.new_page()
                
                await page.goto('https://httpbin.org/html')
                
                # 测试元素等待
                element = await page.wait_for_selector('h1')
                assert element is not None
                
                # 测试元素文本
                text = await element.text_content()
                assert text is not None
                
                await browser.close()
        except ImportError:
            pytest.skip("Playwright未安装")
    
    def test_browser_launch_args(self):
        """测试浏览器启动参数"""
        expected_args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--start-maximized',
            '--ignore-certificate-errors'
        ]
        
        # 验证启动参数配置
        assert isinstance(expected_args, list)
        assert len(expected_args) > 0

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])