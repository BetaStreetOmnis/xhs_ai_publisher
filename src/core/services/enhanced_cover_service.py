"""
增强版封面生成服务
支持AI文字生成和动态贴图
"""

import os
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from typing import Dict, List, Optional, Tuple
import textwrap
from datetime import datetime
import uuid
from ..generation.cover_text_generator import CoverTextGenerator


class EnhancedCoverService:
    """增强版封面生成服务"""
    
    def __init__(self):
        self.cover_generator = CoverTextGenerator()
        from .font_manager import font_manager
        self.font_manager = font_manager
        
        self.templates_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'templates')
        self.output_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'output', 'covers')
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.templates_dir, exist_ok=True)
    
    def generate_ai_cover(self, content: str, template_type: str = "fashion", 
                         platform: str = "xiaohongshu", bg_image_path: str = None) -> Dict[str, str]:
        """
        使用AI生成封面文字并创建封面
        
        Args:
            content: 原始内容
            template_type: 模板类型
            platform: 平台类型
            bg_image_path: 背景图片路径
            
        Returns:
            包含封面信息的dict
        """
        
        # 1. 使用AI生成封面文字
        cover_text = self.cover_generator.generate_cover_text(
            content=content,
            platform=platform,
            style="attractive"
        )
        
        # 2. 根据模板类型选择样式配置
        template_config = self.get_template_config(template_type)
        
        # 3. 生成封面图片
        cover_path = self.create_cover_image(
            cover_text=cover_text,
            template_config=template_config,
            bg_image_path=bg_image_path
        )
        
        return {
            'cover_path': cover_path,
            'cover_text': cover_text,
            'template_type': template_type,
            'platform': platform,
            'created_at': datetime.now().isoformat()
        }
    
    def create_cover_image(self, cover_text: Dict[str, str], 
                          template_config: Dict, bg_image_path: str = None) -> str:
        """创建封面图片"""
        
        # 基础配置
        width, height = template_config.get('size', (1080, 1080))
        
        # 创建画布
        if bg_image_path and os.path.exists(bg_image_path):
            # 使用背景图片
            base_image = Image.open(bg_image_path).convert('RGBA')
            base_image = base_image.resize((width, height), Image.Resampling.LANCZOS)
        else:
            # 使用纯色背景
            bg_color = template_config.get('bg_color', '#f8f8f8')
            base_image = Image.new('RGBA', (width, height), bg_color)
        
        # 应用模板效果
        final_image = self.apply_template_effects(
            base_image, cover_text, template_config
        )
        
        # 保存文件
        filename = f"cover_{uuid.uuid4().hex[:8]}.png"
        output_path = os.path.join(self.output_dir, filename)
        final_image.save(output_path, 'PNG', quality=95)
        
        return output_path
    
    def apply_template_effects(self, base_image: Image.Image, 
                             cover_text: Dict[str, str], 
                             template_config: Dict) -> Image.Image:
        """应用模板效果"""
        
        draw = ImageDraw.Draw(base_image)
        width, height = base_image.size
        
        # 获取文字配置
        text_config = template_config.get('text_config', {})
        
        # 1. 主标题
        main_title = cover_text.get('main_title', '')
        if main_title:
            self.draw_text_with_shadow(
                draw=draw,
                text=main_title,
                position=text_config.get('main_title_pos', (50, 100)),
                font_size=text_config.get('main_title_size', 80),
                color=text_config.get('main_title_color', '#333333'),
                max_width=width - 100
            )
        
        # 2. 副标题
        subtitle = cover_text.get('subtitle', '')
        if subtitle:
            self.draw_text_with_shadow(
                draw=draw,
                text=subtitle,
                position=text_config.get('subtitle_pos', (50, 220)),
                font_size=text_config.get('subtitle_size', 40),
                color=text_config.get('subtitle_color', '#666666'),
                max_width=width - 100
            )
        
        # 3. 标签
        tags = cover_text.get('tags', [])
        if tags:
            self.draw_tags(draw, tags, template_config, width, height)
        
        # 4. Emoji
        emojis = cover_text.get('emojis', [])
        if emojis:
            self.draw_emojis(draw, emojis, template_config, width, height)
        
        # 5. 装饰元素
        if template_config.get('decorations'):
            self.draw_decorations(draw, template_config, width, height)
        
        return base_image
    
    def draw_text_with_shadow(self, draw: ImageDraw.Draw, text: str, 
                            position: Tuple[int, int], font_size: int, 
                            color: str, max_width: int):
        """绘制带阴影的文字"""
        
        try:
            font = self.font_manager.get_font('chinese', 'bold' if font_size > 50 else 'regular', font_size)
        except:
            font = ImageFont.load_default()
        
        x, y = position
        
        # 绘制阴影
        shadow_offset = 2
        draw.text((x + shadow_offset, y + shadow_offset), text, 
                 font=font, fill='#00000080')
        
        # 绘制主文字
        draw.text((x, y), text, font=font, fill=color)
    
    def draw_tags(self, draw: ImageDraw.Draw, tags: List[str], 
                  template_config: Dict, width: int, height: int):
        """绘制标签"""
        
        tag_config = template_config.get('tag_config', {})
        start_y = tag_config.get('start_y', height - 150)
        tag_height = tag_config.get('height', 40)
        tag_margin = tag_config.get('margin', 10)
        
        try:
            font = self.font_manager.get_font('chinese', 'regular', 24)
        except:
            font = ImageFont.load_default()
        
        x = 50
        y = start_y
        
        for tag in tags[:3]:  # 最多显示3个标签
            tag_text = str(tag)
            if not tag_text.startswith('#'):
                tag_text = '#' + tag_text
            
            # 计算标签宽度
            bbox = font.getbbox(tag_text)
            tag_width = bbox[2] - bbox[0] + 20
            
            # 绘制标签背景
            draw.rounded_rectangle(
                [x, y, x + tag_width, y + tag_height],
                radius=15,
                fill='#FF2442'  # 小红书红色
            )
            
            # 绘制标签文字
            draw.text((x + 10, y + 8), tag_text, font=font, fill='white')
            
            x += tag_width + tag_margin
    
    def draw_emojis(self, draw: ImageDraw.Draw, emojis: List[str], 
                    template_config: Dict, width: int, height: int):
        """绘制emoji"""
        
        emoji_config = template_config.get('emoji_config', {})
        position = emoji_config.get('position', (width - 100, 50))
        font_size = emoji_config.get('size', 60)
        
        try:
            emoji_font = ImageFont.truetype(self.font_configs['emoji'], font_size)
        except:
            emoji_font = ImageFont.load_default()
        
        x, y = position
        emoji_text = ''.join(emojis[:2])  # 最多显示2个emoji
        
        # 绘制emoji背景
        draw.rounded_rectangle(
            [x-10, y-10, x + font_size * len(emoji_text) + 10, y + font_size + 10],
            radius=15,
            fill='#FFFFFFCC'
        )
        
        # 绘制emoji
        draw.text((x, y), emoji_text, font=emoji_font, fill='black')
    
    def draw_decorations(self, draw: ImageDraw.Draw, template_config: Dict, 
                        width: int, height: int):
        """绘制装饰元素"""
        
        decorations = template_config.get('decorations', [])
        
        for decoration in decorations:
            if decoration['type'] == 'line':
                draw.line(decoration['points'], fill=decoration['color'], 
                         width=decoration.get('width', 2))
            elif decoration['type'] == 'circle':
                draw.ellipse(decoration['bbox'], outline=decoration['color'], 
                           width=decoration.get('width', 2))
    
    def get_template_config(self, template_type: str) -> Dict:
        """获取模板配置"""
        
        templates = {
            "fashion": {
                "name": "时尚模板",
                "size": (1080, 1080),
                "bg_color": "#FFF5F5",
                "text_config": {
                    "main_title_pos": (80, 120),
                    "main_title_size": 90,
                    "main_title_color": "#FF2442",
                    "subtitle_pos": (80, 240),
                    "subtitle_size": 45,
                    "subtitle_color": "#666666"
                },
                "tag_config": {
                    "start_y": 800,
                    "height": 50,
                    "margin": 15
                },
                "emoji_config": {
                    "position": (920, 80),
                    "size": 80
                },
                "decorations": [
                    {"type": "line", "points": [(80, 200), (1000, 200)], "color": "#FF2442", "width": 3}
                ]
            },
            "lifestyle": {
                "name": "生活模板",
                "size": (1080, 1080),
                "bg_color": "#F8F9FF",
                "text_config": {
                    "main_title_pos": (60, 100),
                    "main_title_size": 85,
                    "main_title_color": "#333333",
                    "subtitle_pos": (60, 220),
                    "subtitle_size": 40,
                    "subtitle_color": "#666666"
                },
                "tag_config": {
                    "start_y": 850,
                    "height": 45,
                    "margin": 12
                },
                "emoji_config": {
                    "position": (900, 100),
                    "size": 70
                }
            },
            "beauty": {
                "name": "美妆模板",
                "size": (1080, 1080),
                "bg_color": "#FFF0F8",
                "text_config": {
                    "main_title_pos": (70, 150),
                    "main_title_size": 80,
                    "main_title_color": "#E91E63",
                    "subtitle_pos": (70, 250),
                    "subtitle_size": 35,
                    "subtitle_color": "#888888"
                },
                "tag_config": {
                    "start_y": 780,
                    "height": 40,
                    "margin": 10
                },
                "emoji_config": {
                    "position": (880, 120),
                    "size": 65
                }
            }
        }
        
        return templates.get(template_type, templates["lifestyle"])
    
    def batch_generate_covers(self, content: str, template_types: List[str] = None) -> List[Dict[str, str]]:
        """批量生成不同风格的封面"""
        
        if template_types is None:
            template_types = ["fashion", "lifestyle", "beauty"]
        
        results = []
        
        for template_type in template_types:
            try:
                cover_result = self.generate_ai_cover(
                    content=content,
                    template_type=template_type
                )
                results.append(cover_result)
            except Exception as e:
                print(f"生成{template_type}风格封面失败: {e}")
        
        return results
    
    def save_template(self, template_name: str, template_config: Dict) -> str:
        """保存模板配置"""
        
        template_path = os.path.join(self.templates_dir, f"{template_name}.json")
        
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template_config, f, ensure_ascii=False, indent=2)
        
        return template_path
    
    def load_template(self, template_name: str) -> Optional[Dict]:
        """加载模板配置"""
        
        template_path = os.path.join(self.templates_dir, f"{template_name}.json")
        
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None
    
    def get_available_templates(self) -> List[str]:
        """获取可用模板列表"""
        
        templates = []
        if os.path.exists(self.templates_dir):
            for file in os.listdir(self.templates_dir):
                if file.endswith('.json'):
                    templates.append(file[:-5])  # 去掉.json后缀
        
        return templates


# 创建全局实例
enhanced_cover_service = EnhancedCoverService()