from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class StyleType(Enum):
    """风格类型枚举"""
    CUTE = "cute"
    CLEAN = "clean"
    PROFESSIONAL = "professional"
    TRENDY = "trendy"
    WARM = "warm"
    ELEGANT = "elegant"
    MINIMAL = "minimal"
    VINTAGE = "vintage"

@dataclass
class StyleConfig:
    """风格配置"""
    name: str
    description: str
    colors: List[str]
    fonts: List[str]
    layout: str
    elements: List[str]
    mood: str
    target_audience: List[str]

class StyleSelector:
    """小红书风格选择器"""
    
    def __init__(self):
        self.styles = self._initialize_styles()
        
    def _initialize_styles(self) -> Dict[StyleType, StyleConfig]:
        """初始化风格配置"""
        return {
            StyleType.CUTE: StyleConfig(
                name="可爱风",
                description="甜美可爱风格，适合少女心内容",
                colors=["#FFB6C1", "#FFC0CB", "#FFE4E1", "#FFF0F5", "#FF69B4"],
                fonts=["方正兰亭黑", "思源黑体", "站酷快乐体"],
                layout="圆角边框，气泡文字，手绘元素",
                elements=["爱心", "星星", "蝴蝶结", "小动物", "花朵"],
                mood="甜美、温馨、治愈",
                target_audience=["学生", "少女", "年轻女性"]
            ),
            
            StyleType.CLEAN: StyleConfig(
                name="简约风",
                description="现代简约风格，留白设计",
                colors=["#FFFFFF", "#F5F5F5", "#E0E0E0", "#333333", "#666666"],
                fonts=["思源黑体", "方正兰亭黑", "微软雅黑"],
                layout="网格布局，大量留白，极简线条",
                elements=["直线", "几何图形", "留白"],
                mood="清爽、专业、高效",
                target_audience=["上班族", "学生", "小资"]
            ),
            
            StyleType.PROFESSIONAL: StyleConfig(
                name="专业风",
                description="商务专业风格，适合职场内容",
                colors=["#1A1A1A", "#333333", "#666666", "#999999", "#E6E6E6"],
                fonts=["思源黑体", "方正兰亭黑", "Arial"],
                layout="对称布局，层次分明，专业排版",
                elements=["图标", "数据可视化", "表格"],
                mood="专业、权威、可信",
                target_audience=["职场人士", "商务人士", "专业人士"]
            ),
            
            StyleType.TRENDY: StyleConfig(
                name="潮流风",
                description="时尚潮流风格，ins感",
                colors=["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FECA57"],
                fonts=["Futura", "Helvetica", "思源黑体"],
                layout="非对称布局，动态元素，视觉冲击",
                elements=["渐变", "霓虹灯效果", "几何图形", "抽象元素"],
                mood="时尚、前卫、个性",
                target_audience=["年轻人", "时尚达人", "博主"]
            ),
            
            StyleType.WARM: StyleConfig(
                name="温暖风",
                description="温馨治愈风格，家庭感",
                colors=["#FFE4B5", "#DEB887", "#F4A460", "#D2691E", "#CD853F"],
                fonts=["方正兰亭黑", "思源宋体", "楷体"],
                layout="柔和曲线，温暖色调，舒适布局",
                elements=["木纹", "布料纹理", "手绘元素"],
                mood="温馨、舒适、治愈",
                target_audience=["宝妈", "家庭用户", "治愈系爱好者"]
            ),
            
            StyleType.ELEGANT: StyleConfig(
                name="优雅风",
                description="高端优雅风格，轻奢感",
                colors=["#000000", "#FFFFFF", "#C0C0C0", "#D4AF37", "#B8860B"],
                fonts=["Didot", "Bodoni", "方正兰亭黑"],
                layout="对称平衡，精致细节，高贵质感",
                elements=["金属质感", "丝绸纹理", "珠宝元素"],
                mood="高贵、优雅、精致",
                target_audience=["高端用户", "小资", "成熟女性"]
            ),
            
            StyleType.MINIMAL: StyleConfig(
                name="极简风",
                description="极致简约，少即是多",
                colors=["#FFFFFF", "#000000", "#808080"],
                fonts=["Helvetica", "思源黑体", "无衬线字体"],
                layout="极简布局，单一焦点，极致留白",
                elements=["单一线条", "纯色背景", "极简图标"],
                mood="纯粹、安静、禅意",
                target_audience=["设计师", "极简主义者", "高端用户"]
            ),
            
            StyleType.VINTAGE: StyleConfig(
                name="复古风",
                description="怀旧复古风格，经典重现",
                colors=["#8B4513", "#D2691E", "#CD853F", "#DEB887", "#F5DEB3"],
                fonts=["宋体", "楷体", "Times New Roman"],
                layout="复古排版，做旧效果，怀旧元素",
                elements=["旧纸张纹理", "复古图案", "手写体"],
                mood="怀旧、经典、文艺",
                target_audience=["文艺青年", "复古爱好者", "历史爱好者"]
            )
        }
    
    def select_style(self, content_analysis: Dict, user_preference: Optional[str] = None) -> StyleType:
        """根据内容分析和用户偏好选择风格"""
        
        # 如果用户有明确偏好，优先使用
        if user_preference:
            for style_type in StyleType:
                if style_type.value == user_preference:
                    return style_type
        
        # 根据内容主题选择风格
        topics = content_analysis.get('topics', [])
        audience = content_analysis.get('target_audience', '年轻女性')
        sentiment = content_analysis.get('sentiment', 'neutral')
        
        # 主题到风格的映射
        topic_style_mapping = {
            '美妆': StyleType.CUTE,
            '穿搭': StyleType.TRENDY,
            '美食': StyleType.WARM,
            '旅行': StyleType.CLEAN,
            '家居': StyleType.WARM,
            '数码': StyleType.PROFESSIONAL,
            '学习': StyleType.CLEAN,
            '健身': StyleType.PROFESSIONAL
        }
        
        # 受众到风格的映射
        audience_style_mapping = {
            '学生': StyleType.CUTE,
            '上班族': StyleType.PROFESSIONAL,
            '宝妈': StyleType.WARM,
            '小资': StyleType.ELEGANT,
            '年轻女性': StyleType.TRENDY,
            '设计师': StyleType.MINIMAL,
            '文艺青年': StyleType.VINTAGE
        }
        
        # 综合评分选择风格
        style_scores = {style: 0 for style in StyleType}
        
        # 主题权重
        for topic in topics:
            if topic in topic_style_mapping:
                style_scores[topic_style_mapping[topic]] += 3
        
        # 受众权重
        if audience in audience_style_mapping:
            style_scores[audience_style_mapping[audience]] += 2
        
        # 情感权重
        sentiment_styles = {
            'positive': [StyleType.CUTE, StyleType.TRENDY, StyleType.WARM],
            'negative': [StyleType.MINIMAL, StyleType.CLEAN],
            'neutral': [StyleType.CLEAN, StyleType.PROFESSIONAL]
        }
        
        if sentiment in sentiment_styles:
            for style in sentiment_styles[sentiment]:
                style_scores[style] += 1
        
        # 选择得分最高的风格
        return max(style_scores, key=style_scores.get)
    
    def get_style_config(self, style_type: StyleType) -> StyleConfig:
        """获取风格配置"""
        return self.styles[style_type]
    
    def get_compatible_styles(self, topics: List[str], audience: str) -> List[StyleType]:
        """获取兼容的风格列表"""
        compatible_styles = []
        
        for style_type in StyleType:
            config = self.styles[style_type]
            
            # 检查受众匹配
            if audience in config.target_audience:
                compatible_styles.append(style_type)
                continue
            
            # 检查主题匹配
            for topic in topics:
                if topic in ['美妆', '穿搭', '美食', '旅行', '家居', '数码', '学习', '健身']:
                    # 简化匹配逻辑
                    if style_type in [StyleType.CUTE, StyleType.TRENDY, StyleType.CLEAN]:
                        if style_type not in compatible_styles:
                            compatible_styles.append(style_type)
        
        return compatible_styles if compatible_styles else list(StyleType)[:3]
    
    def get_color_palette(self, style_type: StyleType) -> List[str]:
        """获取颜色调色板"""
        return self.styles[style_type].colors
    
    def get_style_description(self, style_type: StyleType) -> Dict[str, str]:
        """获取风格描述"""
        config = self.styles[style_type]
        return {
            'name': config.name,
            'description': config.description,
            'mood': config.mood,
            'target_audience': ', '.join(config.target_audience)
        }