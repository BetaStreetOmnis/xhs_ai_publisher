import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class BrowserConfig:
    """浏览器配置"""
    headless: bool = False
    timeout: int = 30000
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


@dataclass
class WebConfig:
    """Web服务配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    reload: bool = True


@dataclass
class XiaohongshuConfig:
    """小红书配置"""
    base_url: str = "https://creator.xiaohongshu.com"
    login_url: str = "https://creator.xiaohongshu.com/login"
    max_retry_times: int = 3
    upload_timeout: int = 60000
    
    # 选择器配置
    selectors: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.selectors is None:
            self.selectors = {
                "phone_input": "//input[@placeholder='手机号']",
                "code_input": "//input[@placeholder='验证码']",
                "send_code_btn": [".css-uyobdj", ".css-1vfl29", "//button[text()='发送验证码']"],
                "login_btn": ".beer-login-btn",
                "publish_btn": [
                    ".publish-video .btn",
                    "button:has-text('发布笔记')",
                    ".btn:text('发布笔记')",
                    "//div[contains(@class, 'btn')][contains(text(), '发布笔记')]"
                ],
                "creator_tab": ".creator-tab",
                "upload_button": ".upload-button",
                "upload_input": ".upload-input",
                "title_input": [
                    "input.d-text[placeholder='填写标题会有更多赞哦～']",
                    "input.d-text",
                    "input[placeholder='填写标题会有更多赞哦～']",
                    "input.title"
                ],
                "content_input": [
                    "[contenteditable='true']:nth-child(2)",
                    ".note-content",
                    "[data-placeholder='添加正文']",
                    "[role='textbox']"
                ]
            }


@dataclass
class AppConfig:
    """应用配置"""
    app_name: str = "XHS_AI_Publisher"
    version: str = "1.0.0"
    data_dir: str = None
    log_level: str = "INFO"
    
    def __post_init__(self):
        if self.data_dir is None:
            home_dir = Path.home()
            self.data_dir = str(home_dir / '.xhs_system')


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._get_default_config_file()
        self.browser = BrowserConfig()
        self.web = WebConfig()
        self.xiaohongshu = XiaohongshuConfig()
        self.app = AppConfig()
        
        # 加载配置文件
        self.load_config()
    
    def _get_default_config_file(self) -> str:
        """获取默认配置文件路径"""
        home_dir = Path.home()
        config_dir = home_dir / '.xhs_system'
        config_dir.mkdir(exist_ok=True)
        return str(config_dir / 'config.json')
    
    def load_config(self) -> None:
        """从文件加载配置"""
        if not os.path.exists(self.config_file):
            self.save_config()
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 更新配置
            if 'browser' in config_data:
                self.browser = BrowserConfig(**config_data['browser'])
            
            if 'web' in config_data:
                self.web = WebConfig(**config_data['web'])
            
            if 'xiaohongshu' in config_data:
                xhs_data = config_data['xiaohongshu']
                # 处理嵌套的selectors字典
                if 'selectors' in xhs_data:
                    selectors = xhs_data.pop('selectors')
                    self.xiaohongshu = XiaohongshuConfig(**xhs_data)
                    self.xiaohongshu.selectors = selectors
                else:
                    self.xiaohongshu = XiaohongshuConfig(**xhs_data)
            
            if 'app' in config_data:
                self.app = AppConfig(**config_data['app'])
                
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            # 使用默认配置
    
    def save_config(self) -> None:
        """保存配置到文件"""
        try:
            config_data = {
                'browser': asdict(self.browser),
                'web': asdict(self.web),
                'xiaohongshu': asdict(self.xiaohongshu),
                'app': asdict(self.app)
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get_selector(self, key: str) -> Any:
        """获取选择器配置"""
        return self.xiaohongshu.selectors.get(key)
    
    def update_selector(self, key: str, value: Any) -> None:
        """更新选择器配置"""
        self.xiaohongshu.selectors[key] = value
        self.save_config()


# 全局配置实例
config = ConfigManager() 