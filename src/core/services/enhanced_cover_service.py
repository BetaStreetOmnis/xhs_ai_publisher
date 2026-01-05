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
        
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        self.templates_dir = os.path.join(project_root, "templates")
        self.output_dir = os.path.join(project_root, "output", "covers")
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.templates_dir, exist_ok=True)
    
    def generate_ai_cover(
        self,
        content: str,
        template_type: str = "fashion",
        platform: str = "xiaohongshu",
        bg_image_path: str = None,
        cover_text_override: Optional[Dict] = None,
    ) -> Dict[str, str]:
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
        
        # 1. 生成封面文字（优先使用外部传入的文案，避免“规则标题”影响效果）
        if isinstance(cover_text_override, dict) and cover_text_override:
            cover_text = cover_text_override
            cover_text.setdefault("main_title", "")
            cover_text.setdefault("subtitle", "")
            cover_text.setdefault("tags", [])
            cover_text.setdefault("emojis", [])
        else:
            cover_text = self.cover_generator.generate_cover_text(
                content=content,
                platform=platform,
                style="attractive",
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
    
    def create_cover_image(
        self,
        cover_text: Dict[str, str],
        template_config: Dict,
        bg_image_path: str = None,
        output_path: Optional[str] = None,
    ) -> str:
        """创建封面图片"""
        
        # 基础配置
        width, height = template_config.get('size', (1080, 1080))
        bg_fit = (template_config.get("bg_fit") or "cover").strip().lower()
        
        # 创建画布
        if bg_image_path and os.path.exists(bg_image_path):
            # 使用背景图片
            base_image = Image.open(bg_image_path).convert('RGBA')
            if bg_fit in {"contain", "letterbox", "fit"}:
                base_image = self._resize_to_contain(base_image, (width, height))
            else:
                base_image = self._resize_to_cover(base_image, (width, height))
        else:
            # 使用纯色背景
            bg_color = template_config.get('bg_color', '#f8f8f8')
            base_image = Image.new('RGBA', (width, height), bg_color)
        
        # 应用模板效果
        final_image = self.apply_template_effects(
            base_image, cover_text, template_config
        )
        
        # 保存文件
        if output_path is None:
            filename = f"cover_{uuid.uuid4().hex[:8]}.png"
            output_path = os.path.join(self.output_dir, filename)
        else:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        final_image.save(output_path, 'PNG', quality=95)
        
        return output_path

    @staticmethod
    def _resize_to_cover(img: Image.Image, target_size: Tuple[int, int]) -> Image.Image:
        """等比缩放并居中裁剪，避免拉伸变形。"""
        dst_w, dst_h = target_size
        src_w, src_h = img.size

        if src_w <= 0 or src_h <= 0:
            return img.resize((dst_w, dst_h), Image.Resampling.LANCZOS)

        scale = max(dst_w / src_w, dst_h / src_h)
        new_w = max(1, int(round(src_w * scale)))
        new_h = max(1, int(round(src_h * scale)))
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        left = max(0, (new_w - dst_w) // 2)
        top = max(0, (new_h - dst_h) // 2)
        return resized.crop((left, top, left + dst_w, top + dst_h))

    @staticmethod
    def _resize_to_contain(img: Image.Image, target_size: Tuple[int, int]) -> Image.Image:
        """等比缩放并居中留边（letterbox），避免裁剪模板边框。"""
        dst_w, dst_h = target_size
        src_w, src_h = img.size

        if src_w <= 0 or src_h <= 0:
            return img.resize((dst_w, dst_h), Image.Resampling.LANCZOS)

        scale = min(dst_w / src_w, dst_h / src_h)
        new_w = max(1, int(round(src_w * scale)))
        new_h = max(1, int(round(src_h * scale)))
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        try:
            center_color = img.getpixel((src_w // 2, src_h // 2))
        except Exception:
            center_color = (245, 245, 245, 255)

        if isinstance(center_color, int):
            center_color = (center_color, center_color, center_color, 255)
        elif isinstance(center_color, tuple) and len(center_color) == 3:
            center_color = (*center_color, 255)
        elif isinstance(center_color, tuple) and len(center_color) >= 4:
            center_color = center_color[:4]
        else:
            center_color = (245, 245, 245, 255)

        canvas = Image.new("RGBA", (dst_w, dst_h), center_color)
        paste_x = (dst_w - new_w) // 2
        paste_y = (dst_h - new_h) // 2
        if resized.mode == "RGBA":
            canvas.paste(resized, (paste_x, paste_y), resized)
        else:
            canvas.paste(resized, (paste_x, paste_y))
        return canvas
    
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
                max_width=text_config.get('main_title_max_width', width - 100),
                align=text_config.get('main_title_align', 'left'),
                stroke_width=int(text_config.get('main_title_stroke_width', 0) or 0),
                stroke_fill=text_config.get('main_title_stroke_color', '#FFFFFF'),
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
                max_width=text_config.get('subtitle_max_width', width - 100),
                align=text_config.get('subtitle_align', 'left'),
                stroke_width=int(text_config.get('subtitle_stroke_width', 0) or 0),
                stroke_fill=text_config.get('subtitle_stroke_color', '#FFFFFF'),
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
    
    def draw_text_with_shadow(
        self,
        draw: ImageDraw.Draw,
        text: str,
        position: Tuple[int, int],
        font_size: int,
        color: str,
        max_width: int,
        align: str = "left",
        stroke_width: int = 0,
        stroke_fill: str = "#FFFFFF",
    ):
        """绘制带阴影/描边的文字（自动换行）。"""
        
        try:
            font = self.font_manager.get_font('chinese', 'bold' if font_size > 50 else 'regular', font_size)
        except:
            font = ImageFont.load_default()
        
        x, y = position

        def _wrap(text_value: str) -> List[str]:
            text_value = (text_value or "").strip()
            if not text_value:
                return []

            lines: List[str] = []
            current = ""
            for ch in text_value:
                test = current + ch
                bbox = draw.textbbox((0, 0), test, font=font)
                width = bbox[2] - bbox[0]
                if width > max_width and current:
                    lines.append(current)
                    current = ch
                else:
                    current = test
            if current:
                lines.append(current)
            return lines

        lines = _wrap(text)
        if not lines:
            return

        line_h = int(round(font_size * 1.25))
        shadow_offset = 2

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            if align == "center":
                draw_x = x + max(0, (max_width - text_w) // 2)
            elif align == "right":
                draw_x = x + max(0, max_width - text_w)
            else:
                draw_x = x

            # 阴影（先画一层增加可读性）
            draw.text(
                (draw_x + shadow_offset, y + shadow_offset),
                line,
                font=font,
                fill="#00000080",
            )

            # 主文字（可选描边）
            draw.text(
                (draw_x, y),
                line,
                font=font,
                fill=color,
                stroke_width=max(0, int(stroke_width or 0)),
                stroke_fill=stroke_fill or "#FFFFFF",
            )
            y += line_h
    
    def draw_tags(self, draw: ImageDraw.Draw, tags: List[str], 
                  template_config: Dict, width: int, height: int):
        """绘制标签"""
        
        tag_config = template_config.get('tag_config', {})
        start_y = tag_config.get('start_y', height - 150)
        tag_height = tag_config.get('height', 40)
        tag_margin = tag_config.get('margin', 10)
        tag_bg_color = tag_config.get("bg_color", "#FF2442")
        tag_text_color = tag_config.get("text_color", "white")
        tag_font_size = int(tag_config.get("font_size", 24) or 24)
        
        try:
            font = self.font_manager.get_font('chinese', 'regular', tag_font_size)
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
                fill=tag_bg_color
            )
            
            # 绘制标签文字
            draw.text((x + 10, y + 8), tag_text, font=font, fill=tag_text_color)
            
            x += tag_width + tag_margin
    
    def draw_emojis(self, draw: ImageDraw.Draw, emojis: List[str], 
                    template_config: Dict, width: int, height: int):
        """绘制emoji"""
        
        emoji_config = template_config.get('emoji_config', {})
        position = emoji_config.get('position', (width - 100, 50))
        font_size = emoji_config.get('size', 60)
        
        try:
            emoji_font = self.font_manager.get_font('system', 'regular', font_size)
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

        # 优先加载文件模板：templates/{template_type}_template.json
        template_file = os.path.join(self.templates_dir, f"{template_type}_template.json")
        if os.path.exists(template_file):
            try:
                with open(template_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data or {}
            except Exception:
                pass

        templates = {
            "xauto_showcase": {
                "name": "系统模板（Showcase）",
                "size": (1080, 1440),
                "bg_color": "#ffffff",
                "bg_fit": "contain",
                "text_config": {
                    "main_title_pos": (80, 380),
                    "main_title_size": 92,
                    "main_title_color": "#111111",
                    "main_title_align": "center",
                    "main_title_max_width": 920,
                    "main_title_stroke_width": 10,
                    "main_title_stroke_color": "#FFFFFF",
                    "subtitle_pos": (80, 560),
                    "subtitle_size": 44,
                    "subtitle_color": "#2f2f2f",
                    "subtitle_align": "center",
                    "subtitle_max_width": 920,
                    "subtitle_stroke_width": 8,
                    "subtitle_stroke_color": "#FFFFFF",
                },
                "tag_config": {
                    "start_y": 1320,
                    "height": 56,
                    "margin": 14,
                    "bg_color": "#FF2442",
                    "text_color": "white",
                    "font_size": 28,
                },
                "emoji_config": {
                    "position": (880, 80),
                    "size": 80,
                },
            },
            "xauto_cover": {
                "name": "系统封面模板",
                "size": (1080, 1440),
                "bg_color": "#ffffff",
                "bg_fit": "contain",
                "text_config": {
                    "main_title_pos": (80, 340),
                    "main_title_size": 96,
                    "main_title_color": "#111111",
                    "main_title_align": "center",
                    "main_title_max_width": 920,
                    "main_title_stroke_width": 10,
                    "main_title_stroke_color": "#FFFFFF",
                    "subtitle_pos": (80, 520),
                    "subtitle_size": 46,
                    "subtitle_color": "#2f2f2f",
                    "subtitle_align": "center",
                    "subtitle_max_width": 920,
                    "subtitle_stroke_width": 8,
                    "subtitle_stroke_color": "#FFFFFF",
                },
                "tag_config": {
                    "start_y": 1240,
                    "height": 56,
                    "margin": 14,
                    "bg_color": "#FF2442",
                    "text_color": "white",
                    "font_size": 28,
                },
                "emoji_config": {
                    "position": (880, 120),
                    "size": 80,
                },
            },
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
            ,
            "food": {
                "name": "美食模板",
                "size": (1080, 1080),
                "bg_color": "#FFF8E1",
                "text_config": {
                    "main_title_pos": (70, 140),
                    "main_title_size": 82,
                    "main_title_color": "#FF6F00",
                    "subtitle_pos": (70, 255),
                    "subtitle_size": 38,
                    "subtitle_color": "#6D4C41",
                },
                "tag_config": {"start_y": 820, "height": 46, "margin": 12},
                "emoji_config": {"position": (880, 95), "size": 70},
                "decorations": [
                    {"type": "line", "points": [(70, 215), (1010, 215)], "color": "#FF6F00", "width": 3}
                ],
            },
            "travel": {
                "name": "旅行模板",
                "size": (1080, 1080),
                "bg_color": "#E3F2FD",
                "text_config": {
                    "main_title_pos": (60, 120),
                    "main_title_size": 84,
                    "main_title_color": "#1565C0",
                    "subtitle_pos": (60, 240),
                    "subtitle_size": 40,
                    "subtitle_color": "#455A64",
                },
                "tag_config": {"start_y": 840, "height": 46, "margin": 12},
                "emoji_config": {"position": (900, 90), "size": 72},
                "decorations": [
                    {"type": "circle", "bbox": [(48, 60), (140, 152)], "color": "#1565C0", "width": 2}
                ],
            },
        }
        
        return templates.get(template_type, templates["lifestyle"])

    def get_available_cover_templates(self) -> List[Dict[str, str]]:
        """获取可用封面模板（文件模板优先）。"""
        results: List[Dict[str, str]] = []

        if not self.templates_dir or not os.path.isdir(self.templates_dir):
            return results

        for filename in sorted(os.listdir(self.templates_dir)):
            if not filename.endswith("_template.json"):
                continue
            path = os.path.join(self.templates_dir, filename)
            template_type = filename[: -len("_template.json")]
            name = template_type
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
                name = data.get("name") or name
            except Exception:
                pass
            results.append({"type": template_type, "name": name, "path": path})

        # 如果目录里没有模板文件，则回退到内置模板列表
        if not results:
            for template_type in ("fashion", "lifestyle", "beauty", "food", "travel"):
                config = self.get_template_config(template_type) or {}
                results.append({"type": template_type, "name": config.get("name") or template_type, "path": ""})

        return results

    def generate_template_preview(self, template_type: str) -> str:
        """生成模板预览图（覆盖写入）。"""
        template_config = self.get_template_config(template_type) or {}
        template_name = template_config.get("name") or template_type

        preview_dir = os.path.join(self.output_dir, "_previews")
        preview_path = os.path.join(preview_dir, f"{template_type}.png")

        cover_text = {
            "main_title": template_name,
            "subtitle": "预览效果",
            "tags": ["模板", "预览", "封面"],
            "emojis": ["✨", "🔥"],
        }

        return self.create_cover_image(
            cover_text=cover_text,
            template_config=template_config,
            bg_image_path=None,
            output_path=preview_path,
        )
    
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
