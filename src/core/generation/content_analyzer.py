import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class ContentAnalysis:
    """内容分析结果"""
    title: str
    topics: List[str]
    keywords: List[str]
    sentiment: str
    target_audience: str
    image_type: str  # 'cover' or 'content'
    color_scheme: str
    style_preference: str

class ContentAnalyzer:
    """小红书内容智能分析器"""
    
    def __init__(self):
        self.topic_keywords = {
            '美妆': ['口红', '粉底', '眼影', '化妆', '护肤', '面膜', '香水'],
            '穿搭': ['OOTD', '穿搭', '衣服', '鞋子', '包包', '配饰', '时尚'],
            '美食': ['美食', '餐厅', '甜品', '咖啡', '烘焙', '食谱', '探店'],
            '旅行': ['旅行', '酒店', '景点', '攻略', '拍照', '打卡', '度假'],
            '家居': ['装修', '家具', '收纳', '布置', '改造', 'ins风', '北欧'],
            '数码': ['手机', '电脑', '相机', '耳机', '测评', '开箱', '科技'],
            '学习': ['学习', '考试', '考研', '留学', '笔记', '效率', '书籍'],
            '健身': ['健身', '瑜伽', '减肥', '运动', '健身房', '健康', '塑形']
        }
        
        self.sentiment_keywords = {
            'positive': ['喜欢', '推荐', '好用', '好看', '好吃', '开心', '满意', '爱', '棒', '赞'],
            'negative': ['不好', '失望', '踩雷', '吐槽', '难用', '难看', '难吃', '后悔', '坑', '差'],
            'neutral': ['分享', '记录', '日常', '普通', '一般', '介绍', '测评', '体验']
        }
        
        self.audience_mapping = {
            '学生': ['学生', '校园', '宿舍', '平价', '性价比', '学生党'],
            '上班族': ['职场', '通勤', '办公室', 'OL', '商务', '简约'],
            '宝妈': ['宝宝', '妈妈', '育儿', '母婴', '家庭', '温馨'],
            '小资': ['精致', '品质', '高端', '轻奢', '氛围感', 'ins风']
        }
    
    def analyze_text(self, text: str, image_type: str = 'cover') -> ContentAnalysis:
        """分析文本内容"""
        text = text.strip()
        
        # 提取标题
        title = self._extract_title(text)
        
        # 识别主题
        topics = self._identify_topics(text)
        
        # 提取关键词
        keywords = self._extract_keywords(text, topics)
        
        # 分析情感
        sentiment = self._analyze_sentiment(text)
        
        # 确定目标受众
        target_audience = self._identify_audience(text)
        
        # 确定配色方案
        color_scheme = self._determine_color_scheme(topics, sentiment)
        
        # 确定风格偏好
        style_preference = self._determine_style(text, topics, target_audience)
        
        return ContentAnalysis(
            title=title,
            topics=topics,
            keywords=keywords,
            sentiment=sentiment,
            target_audience=target_audience,
            image_type=image_type,
            color_scheme=color_scheme,
            style_preference=style_preference
        )
    
    def _extract_title(self, text: str) -> str:
        """提取标题"""
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) <= 30:
                # 检查是否包含话题标签
                if line.startswith('#') or any(keyword in line for topic_keywords in self.topic_keywords.values() for keyword in topic_keywords):
                    return line
        
        # 如果没有合适的标题，取前20个字符
        return text[:20].strip() + '...' if len(text) > 20 else text
    
    def _identify_topics(self, text: str) -> List[str]:
        """识别主题"""
        text_lower = text.lower()
        topics = []
        
        for topic, keywords in self.topic_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    if topic not in topics:
                        topics.append(topic)
                    break
        
        return topics if topics else ['生活']
    
    def _extract_keywords(self, text: str, topics: List[str]) -> List[str]:
        """提取关键词"""
        keywords = []
        
        # 从主题关键词中提取
        for topic in topics:
            if topic in self.topic_keywords:
                topic_keywords = self.topic_keywords[topic]
                for keyword in topic_keywords:
                    if keyword in text and keyword not in keywords:
                        keywords.append(keyword)
        
        # 提取话题标签
        hashtags = re.findall(r'#([^#\s]+)', text)
        keywords.extend(hashtags)
        
        # 提取表情符号
        emojis = re.findall(r'[😀-😿🥰-🥺🤗-🤯🧐-🧿]', text)
        keywords.extend(emojis)
        
        return keywords[:8]  # 限制关键词数量
    
    def _analyze_sentiment(self, text: str) -> str:
        """分析情感倾向"""
        text_lower = text.lower()
        
        sentiment_scores = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        for sentiment, keywords in self.sentiment_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    sentiment_scores[sentiment] += 1
        
        # 根据得分确定情感
        max_sentiment = max(sentiment_scores, key=sentiment_scores.get)
        
        # 如果所有得分都很低，默认为中性
        if max(sentiment_scores.values()) == 0:
            return 'neutral'
        
        return max_sentiment
    
    def _identify_audience(self, text: str) -> str:
        """识别目标受众"""
        text_lower = text.lower()
        audience_scores = {}
        
        for audience, keywords in self.audience_mapping.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    score += 1
            if score > 0:
                audience_scores[audience] = score
        
        # 返回得分最高的受众
        if audience_scores:
            return max(audience_scores, key=audience_scores.get)
        
        # 根据内容类型推测
        if any(word in text_lower for word in ['学生', '宿舍', '校园']):
            return '学生'
        elif any(word in text_lower for word in ['职场', '通勤', '办公室']):
            return '上班族'
        elif any(word in text_lower for word in ['宝宝', '育儿', '妈妈']):
            return '宝妈'
        else:
            return '年轻女性'
    
    def _determine_color_scheme(self, topics: List[str], sentiment: str) -> str:
        """确定配色方案"""
        color_schemes = {
            '美妆': '粉色系',
            '穿搭': '莫兰迪色系',
            '美食': '暖色系',
            '旅行': '清新蓝绿系',
            '家居': '简约黑白灰',
            '数码': '科技蓝紫系',
            '学习': '清新绿系',
            '健身': '活力橙色系'
        }
        
        # 根据主题确定配色
        for topic in topics:
            if topic in color_schemes:
                return color_schemes[topic]
        
        # 根据情感确定配色
        sentiment_colors = {
            'positive': '暖色系',
            'negative': '冷色系',
            'neutral': '中性色系'
        }
        
        return sentiment_colors.get(sentiment, '粉色系')
    
    def _determine_style(self, text: str, topics: List[str], audience: str) -> str:
        """确定风格偏好"""
        # 根据受众确定风格
        audience_styles = {
            '学生': 'cute',
            '上班族': 'clean',
            '宝妈': 'warm',
            '小资': 'professional',
            '年轻女性': 'trendy'
        }
        
        if audience in audience_styles:
            return audience_styles[audience]
        
        # 根据主题确定风格
        topic_styles = {
            '美妆': 'cute',
            '穿搭': 'trendy',
            '美食': 'warm',
            '旅行': 'clean',
            '家居': 'clean',
            '数码': 'professional',
            '学习': 'clean',
            '健身': 'professional'
        }
        
        for topic in topics:
            if topic in topic_styles:
                return topic_styles[topic]
        
        return 'clean'
    
    def get_suggestions(self, analysis: ContentAnalysis) -> Dict[str, str]:
        """获取优化建议"""
        suggestions = {}
        
        # 标题建议
        if len(analysis.title) < 10:
            suggestions['title'] = '标题可以更丰富一些，增加关键词'
        
        # 关键词建议
        if len(analysis.keywords) < 3:
            suggestions['keywords'] = '建议增加更多相关关键词'
        
        # 风格建议
        if analysis.style_preference == 'cute' and '美妆' not in analysis.topics:
            suggestions['style'] = '可爱风格可能更适合美妆类内容'
        
        # 配色建议
        if analysis.color_scheme == '粉色系' and '数码' in analysis.topics:
            suggestions['color'] = '数码类内容更适合科技蓝紫系配色'
        
        return suggestions