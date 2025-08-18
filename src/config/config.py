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
