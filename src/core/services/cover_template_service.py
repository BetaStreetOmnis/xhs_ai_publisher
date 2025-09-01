import os
import json
import time
from typing import List, Dict, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from sqlalchemy.orm import sessionmaker
from src.core.models.cover_template import CoverTemplate, Base
from src.core.database_manager import database_manager

class CoverTemplateService:
    """封面模板服务类"""
    
    def __init__(self):
        self.template_dir = os.path.join(os.path.expanduser('~'), '.xhs_system', 'templates')
        self.thumbnail_dir = os.path.join(self.template_dir, 'thumbnails')
        self.fonts_dir = os.path.join(self.template_dir, 'fonts')
        
        # 确保目录存在
        os.makedirs(self.template_dir, exist_ok=True)
        os.makedirs(self.thumbnail_dir, exist_ok=True)
        os.makedirs(self.fonts_dir, exist_ok=True)
        
        # 初始化数据库表
        self._init_database()
        
        # 初始化默认模板
        self._init_default_templates()
    
    def _init_database(self):
        """初始化数据库表"""
        try:
            # 使用现有的数据库引擎
            engine = database_manager.engine
            if engine:
                # 创建模板表
                Base.metadata.create_all(engine, tables=[CoverTemplate.__table__])
                print("✅ 封面模板表初始化完成")
        except Exception as e:
            print(f"❌ 封面模板表初始化失败: {str(e)}")
    
    def _init_default_templates(self):
        """初始化默认模板"""
        try:
            # 检查是否已有模板
            if self.get_templates_count() > 0:
                return
            
            # 加载新的模板库
            template_file = os.path.join("templates", "cover_templates_library.json")
            if os.path.exists(template_file):
                with open(template_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 将新模板格式转换为旧格式
                for template in data["templates"]:
                    template_config = {
                        'background_color': template.get('bg_color', '#FFFFFF'),
                        'text_config': template.get('text_config', {}),
                        'elements': template.get('elements', {}),
                        'size': template.get('size', [1080, 1080])
                    }
                    
                    self.create_template(
                        name=template['name'],
                        category=template['category'],
                        style_type='new_template',
                        description=f"{template['category']}风格模板",
                        config=template_config,
                        is_default=True
                    )
            
            print("✅ 新模板库初始化完成")
            
        except Exception as e:
            print(f"❌ 新模板库初始化失败: {str(e)}")
            # 回退到旧模板
            self._init_legacy_templates()
    
    def _init_legacy_templates(self):
        """初始化旧版模板（兼容）"""
        try:
            # 创建默认模板配置
            default_templates = [
                {
                    'name': '简约文字',
                    'category': '文字类',
                    'style_type': 'text_simple',
                    'description': '简约的纯文字封面，适合知识分享类内容',
                    'config': {
                        'background_color': '#ffffff',
                        'text_color': '#333333',
                        'font_size': 48,
                        'font_weight': 'bold',
                        'text_align': 'center',
                        'padding': 40
                    }
                },
                {
                    'name': '渐变背景',
                    'category': '渐变类',
                    'style_type': 'gradient_modern',
                    'description': '现代感渐变背景，适合时尚美妆类内容',
                    'config': {
                        'gradient_start': '#667eea',
                        'gradient_end': '#764ba2',
                        'text_color': '#ffffff',
                        'font_size': 44,
                        'font_weight': 'bold',
                        'text_align': 'center',
                        'padding': 40,
                        'shadow': True
                    }
                },
                {
                    'name': '卡片风格',
                    'category': '卡片类',
                    'style_type': 'card_style',
                    'description': '卡片式设计，适合教程攻略类内容',
                    'config': {
                        'background_color': '#f8f9fa',
                        'card_color': '#ffffff',
                        'text_color': '#2c3e50',
                        'accent_color': '#3498db',
                        'font_size': 42,
                        'card_radius': 20,
                        'shadow': True,
                        'padding': 30
                    }
                },
                {
                    'name': '小清新',
                    'category': '清新类',
                    'style_type': 'fresh_style',
                    'description': '小清新风格，适合生活分享类内容',
                    'config': {
                        'background_color': '#fef9e7',
                        'text_color': '#8b4513',
                        'accent_color': '#90ee90',
                        'font_size': 40,
                        'border_color': '#90ee90',
                        'border_width': 3,
                        'padding': 35
                    }
                },
                {
                    'name': '商务风格',
                    'category': '商务类',
                    'style_type': 'business_style',
                    'description': '专业商务风格，适合职场干货类内容',
                    'config': {
                        'background_color': '#2c3e50',
                        'text_color': '#ffffff',
                        'accent_color': '#f39c12',
                        'font_size': 46,
                        'font_weight': 'bold',
                        'line_height': 1.2,
                        'padding': 40
                    }
                }
            ]
            
            # 添加默认模板到数据库
            for template_data in default_templates:
                self.create_template(**template_data)
            
            print("✅ 旧版模板初始化完成")
            
        except Exception as e:
            print(f"❌ 旧版模板初始化失败: {str(e)}")
    
    def create_template(self, name: str, category: str, style_type: str, 
                       description: str = "", config: Dict = None, 
                       is_default: bool = False) -> Optional[int]:
        """创建新模板"""
        try:
            session = database_manager.get_session_direct()
            template = CoverTemplate(
                name=name,
                category=category,
                style_type=style_type,
                description=description,
                config=config or {},
                is_default=is_default
            )
            
            session.add(template)
            session.commit()
            template_id = template.id
            session.close()
            
            # 生成缩略图
            self._generate_thumbnail(template_id, config or {})
            
            return template_id
            
        except Exception as e:
            print(f"❌ 创建模板失败: {str(e)}")
            try:
                session.rollback()
                session.close()
            except:
                pass
            return None
    
    def get_templates(self, category: str = None) -> List[Dict]:
        """获取模板列表"""
        try:
            session = database_manager.get_session_direct()
            query = session.query(CoverTemplate).filter_by(is_active=True)
            if category:
                query = query.filter_by(category=category)
            
            templates = query.order_by(CoverTemplate.is_default.desc(), 
                                     CoverTemplate.created_at.desc()).all()
            
            result = [template.to_dict() for template in templates]
            session.close()
            return result
            
        except Exception as e:
            print(f"❌ 获取模板列表失败: {str(e)}")
            return []
    
    def get_template(self, template_id: int) -> Optional[Dict]:
        """获取单个模板"""
        try:
            session = database_manager.get_session()
            if not session:
                return None
            
            template = session.query(CoverTemplate).filter_by(
                id=template_id, is_active=True).first()
            
            result = template.to_dict() if template else None
            session.close()
            return result
            
        except Exception as e:
            print(f"❌ 获取模板失败: {str(e)}")
            return None
    
    def get_categories(self) -> List[str]:
        """获取所有模板分类"""
        try:
            session = database_manager.get_session()
            if not session:
                return []
            
            categories = session.query(CoverTemplate.category).filter_by(
                is_active=True).distinct().all()
            
            result = [cat[0] for cat in categories]
            session.close()
            return result
            
        except Exception as e:
            print(f"❌ 获取分类失败: {str(e)}")
            return []
    
    def get_templates_count(self) -> int:
        """获取模板总数"""
        try:
            session = database_manager.get_session()
            if not session:
                return 0
            
            count = session.query(CoverTemplate).filter_by(is_active=True).count()
            session.close()
            return count
            
        except Exception as e:
            print(f"❌ 获取模板数量失败: {str(e)}")
            return 0
    
    def delete_template(self, template_id: int) -> bool:
        """删除模板（软删除）"""
        try:
            session = database_manager.get_session()
            if not session:
                return False
            
            template = session.query(CoverTemplate).filter_by(id=template_id).first()
            if template:
                template.is_active = False
                session.commit()
                session.close()
                return True
            
            session.close()
            return False
            
        except Exception as e:
            print(f"❌ 删除模板失败: {str(e)}")
            return False
    
    def _generate_thumbnail(self, template_id: int, config: Dict):
        """生成模板缩略图"""
        try:
            # 创建缩略图 (200x200)
            thumbnail = Image.new('RGB', (200, 200), 'white')
            draw = ImageDraw.Draw(thumbnail)
            
            # 根据样式类型生成不同的缩略图
            style_type = config.get('style_type', 'text_simple')
            
            if style_type == 'gradient_modern':
                self._draw_gradient_thumbnail(draw, thumbnail, config)
            elif style_type == 'card_style':
                self._draw_card_thumbnail(draw, thumbnail, config)
            elif style_type == 'fresh_style':
                self._draw_fresh_thumbnail(draw, thumbnail, config)
            elif style_type == 'business_style':
                self._draw_business_thumbnail(draw, thumbnail, config)
            else:
                self._draw_simple_thumbnail(draw, thumbnail, config)
            
            # 保存缩略图
            thumbnail_path = os.path.join(self.thumbnail_dir, f'template_{template_id}.png')
            thumbnail.save(thumbnail_path)
            
            # 更新数据库中的缩略图路径
            try:
                session = database_manager.get_session_direct()
                template = session.query(CoverTemplate).filter_by(id=template_id).first()
                if template:
                    template.thumbnail_path = thumbnail_path
                    session.commit()
                session.close()
            except Exception as e:
                print(f"❌ 更新缩略图路径失败: {str(e)}")
            
        except Exception as e:
            print(f"❌ 生成缩略图失败: {str(e)}")
    
    def _draw_simple_thumbnail(self, draw, image, config):
        """绘制简约风格缩略图"""
        bg_color = config.get('background_color', '#ffffff')
        text_color = config.get('text_color', '#333333')
        
        # 填充背景
        draw.rectangle([0, 0, 200, 200], fill=bg_color)
        
        # 绘制示例文字
        try:
            font = ImageFont.truetype("Arial", 24)
        except:
            font = ImageFont.load_default()
        
        text = "模板\n预览"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (200 - text_width) // 2
        y = (200 - text_height) // 2
        draw.text((x, y), text, fill=text_color, font=font, align='center')
    
    def _draw_gradient_thumbnail(self, draw, image, config):
        """绘制渐变风格缩略图"""
        # 简化版渐变效果
        start_color = config.get('gradient_start', '#667eea')
        end_color = config.get('gradient_end', '#764ba2')
        
        # 创建渐变背景（简化版）
        for y in range(200):
            ratio = y / 200
            # 简单的颜色插值
            r1, g1, b1 = int(start_color[1:3], 16), int(start_color[3:5], 16), int(start_color[5:7], 16)
            r2, g2, b2 = int(end_color[1:3], 16), int(end_color[3:5], 16), int(end_color[5:7], 16)
            
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            
            color = f'#{r:02x}{g:02x}{b:02x}'
            draw.line([(0, y), (200, y)], fill=color)
        
        # 添加文字
        try:
            font = ImageFont.truetype("Arial", 20)
        except:
            font = ImageFont.load_default()
        
        text = "渐变模板"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = (200 - text_width) // 2
        y = 85
        draw.text((x, y), text, fill='white', font=font)
    
    def _draw_card_thumbnail(self, draw, image, config):
        """绘制卡片风格缩略图"""
        bg_color = config.get('background_color', '#f8f9fa')
        card_color = config.get('card_color', '#ffffff')
        
        # 背景
        draw.rectangle([0, 0, 200, 200], fill=bg_color)
        
        # 卡片
        draw.rounded_rectangle([20, 30, 180, 170], radius=15, fill=card_color)
        
        # 装饰线
        accent_color = config.get('accent_color', '#3498db')
        draw.rectangle([30, 40, 170, 45], fill=accent_color)
        
        # 文字
        try:
            font = ImageFont.truetype("Arial", 18)
        except:
            font = ImageFont.load_default()
        
        draw.text((40, 60), "卡片模板", fill='#2c3e50', font=font)
        draw.text((40, 85), "示例文字", fill='#7f8c8d', font=font)
    
    def _draw_fresh_thumbnail(self, draw, image, config):
        """绘制小清新风格缩略图"""
        bg_color = config.get('background_color', '#fef9e7')
        border_color = config.get('border_color', '#90ee90')
        
        # 背景
        draw.rectangle([0, 0, 200, 200], fill=bg_color)
        
        # 边框
        border_width = config.get('border_width', 3)
        for i in range(border_width):
            draw.rectangle([i, i, 200-i-1, 200-i-1], outline=border_color)
        
        # 装饰元素
        draw.ellipse([160, 20, 180, 40], fill=border_color)
        draw.ellipse([20, 160, 40, 180], fill=border_color)
        
        # 文字
        try:
            font = ImageFont.truetype("Arial", 18)
        except:
            font = ImageFont.load_default()
        
        text_color = config.get('text_color', '#8b4513')
        draw.text((50, 90), "小清新", fill=text_color, font=font)
        draw.text((60, 115), "模板", fill=text_color, font=font)
    
    def _draw_business_thumbnail(self, draw, image, config):
        """绘制商务风格缩略图"""
        bg_color = config.get('background_color', '#2c3e50')
        accent_color = config.get('accent_color', '#f39c12')
        
        # 背景
        draw.rectangle([0, 0, 200, 200], fill=bg_color)
        
        # 装饰线条
        draw.rectangle([0, 0, 200, 8], fill=accent_color)
        draw.rectangle([0, 192, 200, 200], fill=accent_color)
        
        # 文字
        try:
            font = ImageFont.truetype("Arial", 20)
        except:
            font = ImageFont.load_default()
        
        draw.text((60, 85), "商务", fill='white', font=font)
        draw.text((60, 110), "模板", fill='white', font=font)
    
    def generate_cover(self, template_id: int, title: str, subtitle: str = "", 
                      background_image: str = None) -> Optional[str]:
        """根据模板生成封面"""
        try:
            template = self.get_template(template_id)
            if not template:
                return None
            
            config = template['config']
            style_type = template['style_type']
            
            # 创建封面图片 (1080x1080 小红书标准尺寸)
            cover = Image.new('RGB', (1080, 1080), 'white')
            
            # 根据样式类型调用不同的生成方法
            if style_type == 'text_simple':
                cover = self._generate_simple_cover(cover, title, subtitle, config)
            elif style_type == 'gradient_modern':
                cover = self._generate_gradient_cover(cover, title, subtitle, config)
            elif style_type == 'card_style':
                cover = self._generate_card_cover(cover, title, subtitle, config)
            elif style_type == 'fresh_style':
                cover = self._generate_fresh_cover(cover, title, subtitle, config)
            elif style_type == 'business_style':
                cover = self._generate_business_cover(cover, title, subtitle, config)
            
            # 如果有背景图片，合成处理
            if background_image and os.path.exists(background_image):
                cover = self._apply_background_image(cover, background_image, config)
            
            # 保存生成的封面
            timestamp = int(time.time())
            cover_path = os.path.join(self.template_dir, f'cover_{timestamp}.jpg')
            cover.save(cover_path, 'JPEG', quality=95)
            
            return cover_path
            
        except Exception as e:
            print(f"❌ 生成封面失败: {str(e)}")
            return None
    
    def _generate_simple_cover(self, image, title, subtitle, config):
        """生成简约文字封面"""
        draw = ImageDraw.Draw(image)
        
        # 背景色
        bg_color = config.get('background_color', '#ffffff')
        draw.rectangle([0, 0, 1080, 1080], fill=bg_color)
        
        # 加载字体
        font_size = config.get('font_size', 48)
        try:
            title_font = ImageFont.truetype("Arial", font_size)
            subtitle_font = ImageFont.truetype("Arial", font_size - 12)
        except:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
        
        text_color = config.get('text_color', '#333333')
        padding = config.get('padding', 40)
        
        # 绘制标题
        self._draw_wrapped_text(draw, title, title_font, text_color, 
                               padding, 400, 1080 - padding * 2)
        
        # 绘制副标题
        if subtitle:
            self._draw_wrapped_text(draw, subtitle, subtitle_font, text_color,
                                   padding, 600, 1080 - padding * 2)
        
        return image

    def generate_from_template(self, template: Dict, text_content: Dict, output_dir: str = None) -> Dict:
        """根据新模板格式生成封面"""
        try:
            if output_dir is None:
                output_dir = os.path.join(self.template_dir, 'generated')
            os.makedirs(output_dir, exist_ok=True)
            
            # 创建封面图片
            size = template.get('size', [1080, 1080])
            cover = Image.new('RGB', tuple(size), 'white')
            draw = ImageDraw.Draw(cover)
            
            # 设置背景
            self._draw_template_background(cover, draw, template)
            
            # 绘制文字
            self._draw_template_text(cover, draw, template, text_content)
            
            # 绘制装饰元素
            self._draw_template_elements(cover, draw, template)
            
            # 保存图片
            timestamp = int(time.time())
            cover_path = os.path.join(output_dir, f'cover_{timestamp}.png')
            cover.save(cover_path, 'PNG', quality=95)
            
            return {
                'cover_path': cover_path,
                'template_id': template.get('id'),
                'template_name': template.get('name'),
                'text_content': text_content
            }
            
        except Exception as e:
            print(f"❌ 从模板生成封面失败: {str(e)}")
            return None
    
    def _draw_template_background(self, cover, draw, template):
        """绘制模板背景"""
        size = template.get('size', [1080, 1080])
        
        # 渐变背景
        if 'bg_gradient' in template:
            start_color = template['bg_gradient'][0]
            end_color = template['bg_gradient'][1]
            
            for y in range(size[1]):
                ratio = y / size[1]
                r1, g1, b1 = int(start_color[1:3], 16), int(start_color[3:5], 16), int(start_color[5:7], 16)
                r2, g2, b2 = int(end_color[1:3], 16), int(end_color[3:5], 16), int(end_color[5:7], 16)
                
                r = int(r1 + (r2 - r1) * ratio)
                g = int(g1 + (g2 - g1) * ratio)
                b = int(b1 + (b2 - b1) * ratio)
                
                color = (r, g, b)
                draw.line([(0, y), (size[0], y)], fill=color)
        else:
            # 纯色背景
            bg_color = template.get('bg_color', '#FFFFFF')
            draw.rectangle([0, 0, size[0], size[1]], fill=bg_color)
    
    def _draw_template_text(self, cover, draw, template, text_content):
        """绘制模板文字"""
        text_config = template.get('text_config', {})
        
        # 绘制主标题
        if 'main_title' in text_config and text_content.get('main_title'):
            self._draw_template_single_text(
                cover, draw, text_content['main_title'], text_config['main_title']
            )
        
        # 绘制副标题
        if 'subtitle' in text_config and text_content.get('subtitle'):
            self._draw_template_single_text(
                cover, draw, text_content['subtitle'], text_config['subtitle']
            )
        
        # 绘制标签
        if 'tags' in text_config and text_content.get('tags'):
            tags = text_content['tags']
            if isinstance(tags, str):
                tags = tags.split()
            
            self._draw_template_tags(
                cover, draw, tags, text_config['tags']
            )
    
    def _draw_template_single_text(self, cover, draw, text, config):
        """绘制单个文本"""
        try:
            # 加载中文字体
            font_path = self._get_chinese_font()
            font_size = config.get('font_size', 48)
            font = ImageFont.truetype(font_path, font_size)
            
            # 计算文本位置
            pos = config.get('pos', [50, 50])
            max_width = config.get('max_width', 980)
            color = config.get('color', '#000000')
            
            # 自动换行
            lines = self._wrap_text(text, font, max_width)
            line_height = font_size + 10
            
            # 计算起始Y位置
            total_height = len(lines) * line_height
            start_y = pos[1] - total_height // 2
            
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                
                # 居中对齐
                if config.get('text_align') == 'center':
                    x = pos[0] + (max_width - text_width) // 2
                else:
                    x = pos[0]
                
                y = start_y + i * line_height
                draw.text((x, y), line, fill=color, font=font)
                
        except Exception as e:
            print(f"❌ 绘制文本失败: {str(e)}")
    
    def _draw_template_tags(self, cover, draw, tags, config):
        """绘制标签"""
        try:
            font_path = self._get_chinese_font()
            font_size = config.get('font_size', 36)
            font = ImageFont.truetype(font_path, font_size)
            
            pos = config.get('pos', [50, 900])
            spacing = config.get('spacing', 20)
            tag_bg_color = config.get('tag_bg_color', '#F5F5F5')
            tag_padding = config.get('tag_padding', [15, 8])
            
            x_offset = pos[0]
            for tag in tags:
                if tag.strip():  # 跳过空标签
                    tag_text = f"#{tag.strip()}"
                    bbox = draw.textbbox((0, 0), tag_text, font=font)
                    tag_width = bbox[2] - bbox[0] + tag_padding[0] * 2
                    tag_height = bbox[3] - bbox[1] + tag_padding[1] * 2
                    
                    # 绘制标签背景
                    draw.rounded_rectangle(
                        [x_offset, pos[1], x_offset + tag_width, pos[1] + tag_height],
                        radius=5, fill=tag_bg_color
                    )
                    
                    # 绘制标签文字
                    text_x = x_offset + tag_padding[0]
                    text_y = pos[1] + tag_padding[1]
                    draw.text((text_x, text_y), tag_text, fill='#666666', font=font)
                    
                    x_offset += tag_width + spacing
                    
        except Exception as e:
            print(f"❌ 绘制标签失败: {str(e)}")
    
    def _draw_template_elements(self, cover, draw, template):
        """绘制装饰元素"""
        elements = template.get('elements', {})
        
        for key, element in elements.items():
            if isinstance(element, dict):
                self._draw_single_element(cover, draw, element)
            elif isinstance(element, list):
                for item in element:
                    self._draw_single_element(cover, draw, item)
    
    def _draw_single_element(self, cover, draw, element):
        """绘制单个装饰元素"""
        try:
            element_type = element.get('type', 'circle')
            
            if element_type == 'circle':
                pos = element.get('pos', [0, 0])
                size = element.get('size', [50, 50])
                color = element.get('color', '#000000')
                opacity = element.get('opacity', 1.0)
                
                # 创建圆形
                x, y = pos
                w, h = size
                draw.ellipse([x, y, x + w, y + h], fill=color)
                
            elif element_type == 'border':
                pos = element.get('pos', [0, 0])
                size = element.get('size', [100, 100])
                color = element.get('color', '#000000')
                width = element.get('width', 2)
                radius = element.get('radius', 0)
                
                if radius > 0:
                    draw.rounded_rectangle([pos[0], pos[1], pos[0] + size[0], pos[1] + size[1]], 
                                         radius=radius, outline=color, width=width)
                else:
                    draw.rectangle([pos[0], pos[1], pos[0] + size[0], pos[1] + size[1]], 
                                 outline=color, width=width)
                    
        except Exception as e:
            print(f"❌ 绘制装饰元素失败: {str(e)}")

    def _get_chinese_font(self):
        """获取中文字体"""
        chinese_fonts = [
            "/System/Library/Fonts/PingFang.ttc",  # macOS PingFang
            "/System/Library/Fonts/STHeiti Medium.ttc",  # macOS Heiti
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Linux
            "Arial.ttf"  # 回退字体
        ]
        
        for font_path in chinese_fonts:
            if os.path.exists(font_path):
                return font_path
        
        return "Arial.ttf"
    
    def _wrap_text(self, text, font, max_width):
        """文本自动换行"""
        if not text:
            return []
        
        lines = []
        paragraphs = text.split('\n')
        
        for paragraph in paragraphs:
            words = list(paragraph)  # 中文按字符分割
            current_line = ""
            
            for char in words:
                test_line = current_line + char
                bbox = font.getbbox(test_line)
                if bbox[2] - bbox[0] <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = char
            
            if current_line:
                lines.append(current_line)
        
        return lines

    def _generate_gradient_cover(self, image, title, subtitle, config):
        """生成渐变背景封面"""
        draw = ImageDraw.Draw(image)
        
        # 创建渐变背景
        start_color = config.get('gradient_start', '#667eea')
        end_color = config.get('gradient_end', '#764ba2')
        
        for y in range(1080):
            ratio = y / 1080
            r1, g1, b1 = int(start_color[1:3], 16), int(start_color[3:5], 16), int(start_color[5:7], 16)
            r2, g2, b2 = int(end_color[1:3], 16), int(end_color[3:5], 16), int(end_color[5:7], 16)
            
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            
            color = (r, g, b)
            draw.line([(0, y), (1080, y)], fill=color)
        
        # 添加文字（带阴影效果）
        font_size = config.get('font_size', 44)
        try:
            title_font = ImageFont.truetype("Arial", font_size)
        except:
            title_font = ImageFont.load_default()
        
        text_color = config.get('text_color', '#ffffff')
        padding = config.get('padding', 40)
        
        # 绘制阴影
        if config.get('shadow', True):
            self._draw_wrapped_text(draw, title, title_font, '#00000040',
                                   padding + 3, 403, 1080 - padding * 2)
        
        # 绘制文字
        self._draw_wrapped_text(draw, title, title_font, text_color,
                               padding, 400, 1080 - padding * 2)
        
        return image
    
    def _draw_wrapped_text(self, draw, text, font, color, x, y, max_width):
        """绘制自动换行文字"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # 绘制所有行
        line_height = font.size + 10
        total_height = len(lines) * line_height
        start_y = y - total_height // 2
        
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            line_x = x + (max_width - text_width) // 2
            line_y = start_y + i * line_height
            draw.text((line_x, line_y), line, fill=color, font=font)
    
    # 其他样式生成方法...
    def _generate_card_cover(self, image, title, subtitle, config):
        """生成卡片风格封面 - 简化实现"""
        draw = ImageDraw.Draw(image)
        bg_color = config.get('background_color', '#f8f9fa')
        draw.rectangle([0, 0, 1080, 1080], fill=bg_color)
        
        # 主卡片
        card_color = config.get('card_color', '#ffffff')
        draw.rounded_rectangle([100, 200, 980, 880], radius=30, fill=card_color)
        
        # 装饰条
        accent_color = config.get('accent_color', '#3498db')
        draw.rectangle([100, 200, 980, 250], fill=accent_color)
        
        # 文字
        try:
            font = ImageFont.truetype("Arial", 48)
        except:
            font = ImageFont.load_default()
        
        text_color = config.get('text_color', '#2c3e50')
        self._draw_wrapped_text(draw, title, font, text_color, 150, 450, 780)
        
        return image
    
    def _generate_fresh_cover(self, image, title, subtitle, config):
        """生成小清新风格封面 - 简化实现"""
        draw = ImageDraw.Draw(image)
        bg_color = config.get('background_color', '#fef9e7')
        draw.rectangle([0, 0, 1080, 1080], fill=bg_color)
        
        # 边框
        border_color = config.get('border_color', '#90ee90')
        border_width = config.get('border_width', 8)
        for i in range(border_width):
            draw.rectangle([i, i, 1080-i-1, 1080-i-1], outline=border_color)
        
        # 装饰圆点
        draw.ellipse([900, 150, 950, 200], fill=border_color)
        draw.ellipse([130, 900, 180, 950], fill=border_color)
        
        # 文字
        try:
            font = ImageFont.truetype("Arial", 46)
        except:
            font = ImageFont.load_default()
        
        text_color = config.get('text_color', '#8b4513')
        self._draw_wrapped_text(draw, title, font, text_color, 100, 500, 880)
        
        return image
    
    def _generate_business_cover(self, image, title, subtitle, config):
        """生成商务风格封面 - 简化实现"""
        draw = ImageDraw.Draw(image)
        bg_color = config.get('background_color', '#2c3e50')
        draw.rectangle([0, 0, 1080, 1080], fill=bg_color)
        
        # 顶部装饰条
        accent_color = config.get('accent_color', '#f39c12')
        draw.rectangle([0, 0, 1080, 20], fill=accent_color)
        draw.rectangle([0, 1060, 1080, 1080], fill=accent_color)
        
        # 侧边装饰
        draw.rectangle([0, 0, 20, 1080], fill=accent_color)
        draw.rectangle([1060, 0, 1080, 1080], fill=accent_color)
        
        # 文字
        try:
            font = ImageFont.truetype("Arial", 50)
        except:
            font = ImageFont.load_default()
        
        text_color = config.get('text_color', '#ffffff')
        self._draw_wrapped_text(draw, title, font, text_color, 80, 500, 920)
        
        return image
    
    def _apply_background_image(self, cover, bg_image_path, config):
        """应用背景图片"""
        try:
            bg_image = Image.open(bg_image_path)
            
            # 调整背景图片大小
            bg_image = bg_image.resize((1080, 1080), Image.LANCZOS)
            
            # 添加半透明遮罩
            opacity = config.get('background_opacity', 0.3)
            overlay = Image.new('RGBA', (1080, 1080), (255, 255, 255, int(255 * opacity)))
            bg_image = Image.alpha_composite(bg_image.convert('RGBA'), overlay)
            
            # 合成图片
            cover = Image.alpha_composite(bg_image, cover.convert('RGBA'))
            return cover.convert('RGB')
            
        except Exception as e:
            print(f"❌ 应用背景图片失败: {str(e)}")
            return cover


# 全局模板服务实例
cover_template_service = CoverTemplateService()