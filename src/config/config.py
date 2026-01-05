import json
import os


class Config:
    """配置管理类"""

    def __init__(self):
        # 获取用户主目录
        home_dir = os.path.expanduser('~')
        # 创建应用配置目录
        app_config_dir = os.path.join(home_dir, '.xhs_system')
        if not os.path.exists(app_config_dir):
            os.makedirs(app_config_dir)

        # 配置文件路径
        self.config_file = os.path.join(app_config_dir, 'settings.json')

        self.default_config = {
            "app": "debug",
            "title_edit": {
                "author": "小红书",
                "title": "测试标题",
            },
            "phone": "18888888888",
        }
        self.load_config()

    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                # 确保所有默认配置项都存在
                self._ensure_default_config()
            else:
                self.config = self.default_config
                self.save_config()
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
            self.config = self.default_config
            self.save_config()

    def _ensure_default_config(self):
        """确保所有默认配置项都存在"""
        # 检查并添加缺失的顶级配置项
        for key, value in self.default_config.items():
            if key not in self.config:
                self.config[key] = value
        
        # 检查并添加缺失的嵌套配置项
        if 'title_edit' in self.config:
            for key, value in self.default_config['title_edit'].items():
                if key not in self.config['title_edit']:
                    self.config['title_edit'][key] = value
        else:
            self.config['title_edit'] = self.default_config['title_edit']
        
        # 保存更新后的配置
        self.save_config()

    def save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {str(e)}")

    def get_app_config(self):
        """获取app配置"""
        return self.config.get('app', self.default_config['app'])

    def update_app_config(self, app):
        """更新app配置"""
        self.config['app'] = app
        self.save_config()
        
    def get_phone_config(self):
        """获取手机号配置"""
        return self.config.get('phone', self.default_config['phone'])
        
    def update_phone_config(self, phone):
        """更新手机号配置"""
        self.config['phone'] = phone
        self.save_config()

    def get_title_config(self):
        """获取标题配置"""
        return self.config.get('title_edit', self.default_config['title_edit'])

    def update_title_config(self, title):
        """更新标题配置"""
        if 'title_edit' not in self.config:
            self.config['title_edit'] = {}
        self.config['title_edit']['title'] = title
        self.save_config()

    def update_author_config(self, author):
        """更新作者配置"""
        if 'title_edit' not in self.config:
            self.config['title_edit'] = {}
        self.config['title_edit']['author'] = author
        self.save_config()

    def get_schedule_config(self):
        """获取定时发布配置"""
        return self.config.get('schedule', {
            'enabled': False,
            'schedule_time': '',
            'interval_hours': 2,
            'max_posts': 10,
            'tasks': []
        })

    def update_schedule_config(self, schedule_config):
        """更新定时发布配置"""
        self.config['schedule'] = schedule_config
        self.save_config()

    def get_model_config(self):
        """获取模型配置"""
        return self.config.get('model', {
            'provider': 'OpenAI',
            'api_key': '',
            'api_key_name': 'default',
            'api_endpoint': 'https://api.openai.com/v1/chat/completions',
            'model_name': 'gpt-3.5-turbo',
            'prompt_template': 'xiaohongshu_default',
            'system_prompt': '你是一个小红书内容创作助手，帮助用户生成优质内容',
            'advanced': {
                'temperature': 0.7,
                'max_tokens': 1000,
                'timeout': 30
            }
        })    

    def get_provider_endpoints(self):
        """获取各提供商的默认端点"""
        return {
            'OpenAI': 'https://api.openai.com/v1/chat/completions',
            'Anthropic（Claude）': 'https://api.anthropic.com/v1/messages',
            '阿里云（通义千问）': 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
            '月之暗面（Kimi）': 'https://api.moonshot.cn/v1/chat/completions',
            '字节跳动（豆包）': 'https://ark.cn-beijing.volces.com/api/v3/chat/completions',
            '腾讯（混元）': 'https://api.lkeap.cloud.tencent.com/v1/chat/completions',
            '本地模型': 'http://localhost:1234/v1/chat/completions'
        }

    def update_model_config(self, model_config):
        """更新模型配置"""
        self.config['model'] = model_config
        self.save_config()

    def get_api_config(self):
        """获取API配置"""
        return self.config.get('api', {
            'xhs_api_key': '',
            'xhs_api_secret': '',
            'image_provider': '本地存储',
            'image_endpoint': '',
            'image_access_key': '',
            'image_secret_key': ''
        })

    def update_api_config(self, api_config):
        """更新API配置"""
        self.config['api'] = api_config
        self.save_config()

    def get_templates_config(self):
        """获取模板相关配置（文案模板/图片模板等）。"""
        return self.config.get(
            'templates',
            {
                # 系统图片模板目录（可指向 x-auto-publisher 的目录，或导入后的本地目录）
                'system_templates_dir': '',
                # 默认内容模板包（如 content_clean_blue）
                'default_content_pack': '',
                # 首页默认封面模板（showcase_*.png 的 stem，比如 showcase_social_quote_card_vibrant）
                'selected_cover_template_id': '',
                # 仅用于展示
                'selected_cover_template_display': '',
            },
        )

    def update_templates_config(self, templates_config):
        """更新模板相关配置"""
        self.config['templates'] = templates_config or {}
        self.save_config()
