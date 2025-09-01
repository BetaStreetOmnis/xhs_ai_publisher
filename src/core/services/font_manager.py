"""
字体管理器
处理字体加载和回退方案
"""

import os
from PIL import ImageFont

class FontManager:
    """字体管理器"""
    
    def __init__(self):
        self.fonts_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'fonts')
        self.ensure_fonts()
    
    def ensure_fonts(self):
        """确保字体文件存在"""
        os.makedirs(self.fonts_dir, exist_ok=True)
        
        # 创建字体映射
        self.font_map = {
            'chinese': {
                'regular': self.get_font_path('SourceHanSansCN-Regular.otf'),
                'bold': self.get_font_path('SourceHanSansCN-Bold.otf'),
                'light': self.get_font_path('SourceHanSansCN-Light.otf')
            },
            'system': {
                'regular': self.get_system_font(),
                'bold': self.get_system_font(),
                'light': self.get_system_font()
            }
        }
    
    def get_font_path(self, font_name: str) -> str:
        """获取字体文件路径"""
        font_path = os.path.join(self.fonts_dir, font_name)
        
        # 如果字体文件不存在，使用系统字体
        if not os.path.exists(font_path):
            return self.get_system_font()
        
        return font_path
    
    def get_system_font(self) -> str:
        """获取系统字体路径"""
        system_fonts = [
            # macOS 中文字体
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
            # Windows 中文字体
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/simsun.ttc",
            "C:/Windows/Fonts/msyh.ttc",
            # Linux 中文字体
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
        ]
        
        for font in system_fonts:
            if os.path.exists(font):
                return font
        
        # 使用PIL默认字体
        return None
    
    def get_font(self, font_type: str = 'chinese', style: str = 'regular', size: int = 24):
        """获取字体对象"""
        try:
            font_path = self.font_map.get(font_type, self.font_map['system']).get(style)
            if font_path and os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except Exception as e:
            print(f"加载字体失败: {e}")
        
        # 使用系统字体或默认字体
        try:
            system_font = self.get_system_font()
            if system_font:
                return ImageFont.truetype(system_font, size)
        except:
            pass
        
        # 使用默认字体
        return ImageFont.load_default()
    
    def get_available_fonts(self) -> dict:
        """获取可用字体列表"""
        fonts = {}
        
        # 检查中文字体
        for style, path in self.font_map['chinese'].items():
            if path and os.path.exists(path):
                fonts[f"中文字体-{style}"] = path
        
        # 检查系统字体
        system_font = self.get_system_font()
        if system_font:
            fonts["系统字体"] = system_font
        
        return fonts

# 创建全局实例
font_manager = FontManager()