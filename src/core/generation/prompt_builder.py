from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json

@dataclass
class PromptTemplate:
    """提示词模板"""
    name: str
    description: str
    template: str
    parameters: Dict[str, Any]
    examples: List[str]

class PromptBuilder:
    """小红书AI图片生成提示词构建器"""
    
    def __init__(self):
        self.templates = self._initialize_templates()
        self.style_keywords = self._initialize_style_keywords()
        self.composition_rules = self._initialize_composition_rules()
    
    def _initialize_templates(self) -> Dict[str, PromptTemplate]:
        """初始化提示词模板"""
        return {
            'cover': PromptTemplate(
                name="封面图模板",
                description="小红书封面图专用模板",
                template="小红书{style}封面图，标题\"{title}\"，{theme}主题，{color_scheme}配色，{elements}元素，{mood}氛围，竖版9:16比例，高清画质，{additional}",
                parameters={
                    'style': ['可爱风', '简约风', '专业风', '潮流风', '温暖风'],
                    'color_scheme': ['粉色系', '莫兰迪色系', '暖色系', '冷色系'],
                    'elements': ['爱心', '花朵', '几何图形', '文字排版', '装饰元素'],
                    'mood': ['甜美', '清新', '专业', '时尚', '温馨']
                },
                examples=[
                    "小红书可爱风封面图，标题\"春日美妆分享\"，美妆主题，粉色系配色，爱心花朵元素，甜美氛围，竖版9:16比例，高清画质，少女心爆棚",
                    "小红书简约风封面图，标题\"职场穿搭指南\"，穿搭主题，莫兰迪色系配色，几何图形元素，清新氛围，竖版9:16比例，高清画质"
                ]
            ),
            
            'content': PromptTemplate(
                name="内容页模板",
                description="小红书内容页专用模板",
                template="小红书{style}内容页，{title}主题，{layout}排版，{color_scheme}配色，{elements}元素，清晰易读，竖版比例，{additional}",
                parameters={
                    'style': ['简约', '清新', '专业', '时尚'],
                    'layout': ['网格布局', '瀑布流', '对称布局', '杂志风'],
                    'color_scheme': ['同色系', '对比色', '渐变色', '黑白灰'],
                    'elements': ['图标', '分割线', '文字框', '装饰图案']
                },
                examples=[
                    "小红书简约内容页，护肤步骤分享主题，网格布局排版，同色系配色，图标元素，清晰易读，竖版比例",
                    "小红书清新内容页，旅行攻略主题，杂志风排版，渐变色配色，装饰图案元素，清晰易读，竖版比例"
                ]
            ),
            
            'product': PromptTemplate(
                name="产品展示模板",
                description="产品展示专用模板",
                template="{product}产品展示图，{style}风格，{background}背景，{lighting}光线，{angle}角度，{color_scheme}配色，突出{features}特点，{additional}",
                parameters={
                    'style': ['简约', '时尚', '高端', '生活化'],
                    'background': ['纯色背景', '渐变背景', '场景背景', '虚化背景'],
                    'lighting': ['自然光', '柔光', '聚光灯', '逆光'],
                    'angle': ['正面', '45度角', '俯视', '特写']
                },
                examples=[
                    "口红产品展示图，简约风格，纯色背景，柔光光线，45度角，粉色系配色，突出质感特点",
                    "护肤品产品展示图，高端风格，渐变背景，聚光灯光线，特写角度，金色系配色，突出奢华特点"
                ]
            )
        }
    
    def _initialize_style_keywords(self) -> Dict[str, List[str]]:
        """初始化风格关键词"""
        return {
            'cute': ['可爱', '甜美', '少女心', '马卡龙', '粉嫩', '软萌', '治愈', '温馨'],
            'clean': ['简约', '干净', '清爽', '留白', '极简', '现代', '几何', '线条'],
            'professional': ['专业', '商务', '高端', '质感', '精致', '权威', '可信', '稳重'],
            'trendy': ['潮流', '时尚', 'ins风', '流行', '个性', '前卫', '酷感', '现代'],
            'warm': ['温暖', '治愈', '舒适', '家庭', '柔和', '自然', '亲切', '安心'],
            'elegant': ['优雅', '高贵', '精致', '奢华', '典雅', '品味', '气质', '高端'],
            'minimal': ['极简', '纯粹', '安静', '禅意', '留白', '克制', '本质', '纯净'],
            'vintage': ['复古', '怀旧', '经典', '文艺', '做旧', '历史感', '老派', '传统']
        }
    
    def _initialize_composition_rules(self) -> Dict[str, Any]:
        """初始化构图规则"""
        return {
            'cover_rules': {
                'aspect_ratio': '9:16',
                'safe_area': {'top': 0.2, 'bottom': 0.15, 'left': 0.1, 'right': 0.1},
                'title_placement': ['top', 'center', 'bottom'],
                'elements_limit': 5,
                'color_contrast': 'medium',
                'text_readability': 'high'
            },
            'content_rules': {
                'aspect_ratio': '9:16',
                'sections': 3,
                'text_ratio': 0.3,
                'image_ratio': 0.7,
                'spacing': 'comfortable',
                'alignment': 'center'
            }
        }
    
    def build_prompt(self, 
                    content_analysis: Dict,
                    style_config: Dict,
                    image_type: str = 'cover',
                    custom_params: Optional[Dict] = None) -> str:
        """构建完整的AI图片生成提示词"""
        
        # 获取基础模板
        template = self.templates.get(image_type, self.templates['cover'])
        
        # 构建参数
        params = self._build_parameters(content_analysis, style_config, custom_params)
        
        # 填充模板
        prompt = template.template.format(**params)
        
        # 添加质量要求
        quality_prompt = self._add_quality_requirements(image_type)
        
        # 添加技术参数
        technical_prompt = self._add_technical_specs(image_type)
        
        return f"{prompt}, {quality_prompt}, {technical_prompt}"
    
    def _build_parameters(self, 
                         content_analysis: Dict,
                         style_config: Dict,
                         custom_params: Optional[Dict] = None) -> Dict[str, str]:
        """构建模板参数"""
        params = {}
        
        # 基础参数
        params['title'] = content_analysis.get('title', '分享内容')
        params['style'] = style_config.get('name', '简约风')
        params['color_scheme'] = content_analysis.get('color_scheme', '粉色系')
        
        # 主题参数
        topics = content_analysis.get('topics', ['生活'])
        params['theme'] = '、'.join(topics)
        
        # 元素参数
        keywords = content_analysis.get('keywords', [])[:3]
        params['elements'] = '、'.join(keywords) if keywords else '装饰元素'
        
        # 氛围参数
        sentiment = content_analysis.get('sentiment', 'neutral')
        mood_mapping = {
            'positive': '温馨',
            'negative': '冷静',
            'neutral': '清新'
        }
        params['mood'] = mood_mapping.get(sentiment, '清新')
        
        # 布局参数
        layout_mapping = {
            'cover': '居中构图',
            'content': '网格布局',
            'product': '三分法构图'
        }
        params['layout'] = layout_mapping.get('cover', '居中构图')
        
        # 自定义参数
        if custom_params:
            params.update(custom_params)
        
        # 额外参数
        additional_parts = []
        
        # 根据受众添加元素
        audience = content_analysis.get('target_audience', '年轻女性')
        if audience == '学生':
            additional_parts.append('平价实用')
        elif audience == '上班族':
            additional_parts.append('职场适用')
        elif audience == '宝妈':
            additional_parts.append('家庭友好')
        
        params['additional'] = '，'.join(additional_parts) if additional_parts else '高清质感'
        
        return params
    
    def _add_quality_requirements(self, image_type: str) -> str:
        """添加质量要求"""
        quality_specs = {
            'cover': '4K分辨率，高清画质，专业摄影，精致细节，商业级质量',
            'content': '清晰易读，层次分明，专业排版，高质量渲染',
            'product': '产品质感突出，细节清晰，专业拍摄，商业摄影水准'
        }
        return quality_specs.get(image_type, '高清画质，专业水准')
    
    def _add_technical_specs(self, image_type: str) -> str:
        """添加技术规格"""
        technical_specs = {
            'cover': '竖版9:16比例，适合小红书封面，无水印，干净背景',
            'content': '竖版9:16比例，适合小红书内容页，清晰文字，易读布局',
            'product': '产品展示专用，多角度可选，专业布光，纯色背景'
        }
        return technical_specs.get(image_type, '适合社交媒体分享')
    
    def optimize_for_platform(self, prompt: str, platform: str = 'xiaohongshu') -> str:
        """针对平台优化提示词"""
        platform_specs = {
            'xiaohongshu': '小红书风格，少女向，精致美观，适合分享，竖版9:16',
            'weibo': '微博风格，简洁明了，适合转发，横竖版皆可',
            'douyin': '抖音风格，年轻化，视觉冲击，竖版9:16',
            'instagram': 'ins风，国际化，简约高级，方版或竖版'
        }
        
        platform_text = platform_specs.get(platform, '')
        return f"{prompt}, {platform_text}"
    
    def generate_variations(self, 
                          base_prompt: str,
                          count: int = 3,
                          variation_type: str = 'style') -> List[str]:
        """生成提示词变体"""
        variations = []
        
        if variation_type == 'style':
            styles = list(self.style_keywords.keys())[:count]
            for style in styles:
                keywords = self.style_keywords[style]
                variation = base_prompt.replace(
                    '简约风', 
                    f"{self.style_keywords[style][0]}风"
                )
                variations.append(variation)
        
        elif variation_type == 'color':
            colors = ['粉色系', '蓝色系', '绿色系', '黄色系', '紫色系']
            for color in colors[:count]:
                variation = base_prompt.replace('粉色系', color)
                variations.append(variation)
        
        elif variation_type == 'composition':
            compositions = ['居中构图', '三分法', '对角线构图', '对称构图']
            for comp in compositions[:count]:
                variation = base_prompt.replace('居中构图', comp)
                variations.append(variation)
        
        return variations
    
    def validate_prompt(self, prompt: str) -> Dict[str, Any]:
        """验证提示词质量"""
        validation_result = {
            'is_valid': True,
            'score': 0,
            'issues': [],
            'suggestions': []
        }
        
        # 检查长度
        if len(prompt) < 20:
            validation_result['issues'].append('提示词过短')
            validation_result['score'] -= 20
        elif len(prompt) > 200:
            validation_result['issues'].append('提示词过长')
            validation_result['score'] -= 10
        else:
            validation_result['score'] += 20
        
        # 检查关键词
        essential_keywords = ['小红书', '高清', '竖版', '9:16']
        found_keywords = [kw for kw in essential_keywords if kw in prompt]
        if len(found_keywords) >= 2:
            validation_result['score'] += 30
        else:
            validation_result['suggestions'].append('建议添加小红书、高清、竖版等关键词')
        
        # 检查风格描述
        style_keywords = ['可爱', '简约', '专业', '时尚', '温暖', '优雅', '极简', '复古']
        has_style = any(style in prompt for style in style_keywords)
        if has_style:
            validation_result['score'] += 20
        else:
            validation_result['suggestions'].append('建议明确指定视觉风格')
        
        # 检查质量要求
        quality_words = ['高清', '4K', '专业', '精致', '高质量']
        has_quality = any(quality in prompt for quality in quality_words)
        if has_quality:
            validation_result['score'] += 20
        else:
            validation_result['suggestions'].append('建议添加质量要求')
        
        # 最终验证
        if validation_result['score'] < 60:
            validation_result['is_valid'] = False
        
        return validation_result
    
    def get_template_examples(self, template_name: str) -> List[str]:
        """获取模板示例"""
        template = self.templates.get(template_name)
        return template.examples if template else []
    
    def save_custom_template(self, name: str, template: PromptTemplate) -> None:
        """保存自定义模板"""
        self.templates[name] = template
    
    def get_all_templates(self) -> List[str]:
        """获取所有模板名称"""
        return list(self.templates.keys())