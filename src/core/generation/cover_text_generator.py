"""
AI封面文字生成器
根据内容自动生成适合的封面标题和文案
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from ..ai_integration.ai_provider_factory import AIProviderFactory


class CoverTextGenerator:
    """AI封面文字生成器"""
    
    def __init__(self):
        # 暂时使用模拟AI服务，实际使用时需要配置API密钥
        self.ai_provider = None
    
    def generate_cover_text(self, content: str, platform: str = "xiaohongshu", 
                          style: str = "attractive", target_audience: str = "年轻女性") -> Dict[str, str]:
        """
        生成封面文字
        
        Args:
            content: 原始内容文本
            platform: 平台类型 (xiaohongshu, douyin, weibo等)
            style: 文案风格 (attractive, professional, cute, luxury等)
            target_audience: 目标受众
            
        Returns:
            包含封面文字的dict: {
                'main_title': 主标题,
                'subtitle': 副标题,
                'tags': 标签列表,
                'emojis': 推荐emoji
            }
        """
        
        # 暂时使用回退生成策略，实际使用时需要配置AI服务
        return self._fallback_generation(content, style)
    
    def _build_prompt(self, content: str, platform: str, style: str, target_audience: str) -> str:
        """构建AI提示词"""
        
        platform_guides = {
            "xiaohongshu": "小红书用户喜欢真实分享、生活化表达，标题要有代入感和实用性",
            "douyin": "抖音用户喜欢简洁有力、有冲击力的标题，适合短视频节奏",
            "weibo": "微博用户喜欢话题性强、有争议性的标题"
        }
        
        style_guides = {
            "attractive": "吸引人、有冲击力，使用emoji和热门词汇",
            "professional": "专业权威，使用行业术语和数据支撑",
            "cute": "可爱俏皮，使用网络流行语和表情",
            "luxury": "高端奢华，突出品质和独特性"
        }
        
        prompt = f"""
        请为以下内容生成适合{platform}平台的封面文字：
        
        内容：{content[:500]}...
        
        要求：
        1. 主标题：{style_guides.get(style, '吸引人')}，15字以内
        2. 副标题：补充说明，20字以内
        3. 标签：3-5个相关标签，带#
        4. emoji：2-4个合适的emoji
        
        平台特点：{platform_guides.get(platform, '通用')}
        目标受众：{target_audience}
        
        请返回JSON格式：
        {{
            "main_title": "主标题",
            "subtitle": "副标题",
            "tags": ["#标签1", "#标签2", "#标签3"],
            "emojis": ["emoji1", "emoji2"]
        }}
        """
        
        return prompt
    
    def _parse_response(self, response: str) -> Dict[str, str]:
        """解析AI响应"""
        
        try:
            # 尝试解析JSON
            data = json.loads(response.strip())
            return {
                'main_title': data.get('main_title', ''),
                'subtitle': data.get('subtitle', ''),
                'tags': data.get('tags', []),
                'emojis': data.get('emojis', [])
            }
        except:
            # 如果解析失败，尝试从文本中提取
            return self._extract_from_text(response)
    
    def _extract_from_text(self, text: str) -> Dict[str, str]:
        """从文本中提取信息"""
        lines = text.strip().split('\n')
        
        # 提取标题（通常在第一行）
        main_title = lines[0].strip() if lines else "精彩内容"
        if len(main_title) > 15:
            main_title = main_title[:15]
        
        # 提取副标题（第二行或剩余内容）
        subtitle = ""
        if len(lines) > 1:
            subtitle = lines[1].strip()
            if len(subtitle) > 20:
                subtitle = subtitle[:20]
        
        # 提取标签
        tags = re.findall(r'#[\u4e00-\u9fa5\w]+', text)
        if not tags:
            tags = ["#分享", "#生活"]
        
        # 提取emoji
        emojis = re.findall(r'[😀-🙏🌀-🗿🚀-🛿]', text)
        if not emojis:
            emojis = ["✨", "🔥"]
        
        return {
            'main_title': main_title,
            'subtitle': subtitle,
            'tags': tags[:5],
            'emojis': emojis[:4]
        }
    
    def _fallback_generation(self, content: str, style: str) -> Dict[str, str]:
        """回退生成策略"""
        
        # 从内容中提取关键词
        keywords = self._extract_keywords(content)
        
        templates = {
            "attractive": {
                "main_title": f"{keywords[0] if keywords else '超实用'}分享！",
                "subtitle": f"{keywords[1] if len(keywords) > 1 else '不看后悔'}",
                "tags": ["#干货", "#分享", f"#{keywords[0] if keywords else '生活'}"],
                "emojis": ["✨", "🔥"]
            },
            "professional": {
                "main_title": f"{keywords[0] if keywords else '专业'}指南",
                "subtitle": f"{keywords[1] if len(keywords) > 1 else '深度解析'}",
                "tags": ["#知识", "#干货", f"#{keywords[0] if keywords else '专业'}"],
                "emojis": ["📚", "💡"]
            },
            "cute": {
                "main_title": f"{keywords[0] if keywords else '可爱'}到爆！",
                "subtitle": f"{keywords[1] if len(keywords) > 1 else '少女心爆棚'}",
                "tags": ["#可爱", "#日常", f"#{keywords[0] if keywords else '分享'}"],
                "emojis": ["💖", "🎀"]
            },
            "luxury": {
                "main_title": f"{keywords[0] if keywords else '高端'}生活",
                "subtitle": f"{keywords[1] if len(keywords) > 1 else '品质之选'}",
                "tags": ["#品质", "#生活", f"#{keywords[0] if keywords else '精致'}"],
                "emojis": ["💎", "✨"]
            }
        }
        
        return templates.get(style, templates["attractive"])
    
    def _extract_keywords(self, content: str) -> List[str]:
        """从内容中提取关键词"""
        # 简单的关键词提取逻辑
        # 实际项目中可以使用jieba分词或更复杂的NLP技术
        
        content = content[:200]  # 限制长度
        
        # 常见关键词词典
        keywords_dict = {
            "护肤": ["护肤", "保养", "皮肤", "面膜", "精华"],
            "美妆": ["化妆", "口红", "眼影", "粉底", "美妆"],
            "穿搭": ["穿搭", "衣服", "时尚", "搭配", "OOTD"],
            "美食": ["美食", "料理", "餐厅", "食谱", "吃货"],
            "旅行": ["旅行", "旅游", "攻略", "景点", "酒店"],
            "健身": ["健身", "减肥", "运动", "瑜伽", "塑形"],
            "学习": ["学习", "考试", "复习", "笔记", "干货"],
            "职场": ["职场", "工作", "简历", "面试", "升职"]
        }
        
        matched_keywords = []
        for category, words in keywords_dict.items():
            for word in words:
                if word in content:
                    matched_keywords.append(category)
                    break
        
        return matched_keywords[:3] if matched_keywords else ["生活", "分享"]
    
    def optimize_for_platform(self, text: str, platform: str) -> str:
        """针对平台优化文字"""
        
        platform_limits = {
            "xiaohongshu": {"title": 20, "subtitle": 30},
            "douyin": {"title": 15, "subtitle": 20},
            "weibo": {"title": 30, "subtitle": 50}
        }
        
        limits = platform_limits.get(platform, {"title": 20, "subtitle": 30})
        
        # 根据平台限制截断文字
        if len(text) > limits["title"]:
            text = text[:limits["title"]-1] + "…"
        
        return text
    
    def generate_batch_texts(self, content: str, count: int = 5) -> List[Dict[str, str]]:
        """批量生成多个封面文字方案"""
        
        results = []
        styles = ["attractive", "professional", "cute", "luxury"]
        
        for i in range(count):
            style = styles[i % len(styles)]
            text = self.generate_cover_text(content, style=style)
            text["style"] = style
            results.append(text)
        
        return results