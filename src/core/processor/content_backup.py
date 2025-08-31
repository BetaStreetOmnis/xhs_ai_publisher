#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备用内容生成器 - 当主API不可用时的备选方案
"""

import json
import random
from PyQt5.QtCore import QThread, pyqtSignal


class BackupContentGenerator(QThread):
    """备用内容生成器"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, input_text, header_title, author, generate_btn):
        super().__init__()
        self.input_text = input_text
        self.header_title = header_title
        self.author = author
        self.generate_btn = generate_btn

    def run(self):
        """生成备用内容"""
        try:
            print("🔄 主API不可用，使用备用内容生成器...")
            
            # 更新按钮状态
            self.generate_btn.setText("⏳ 本地生成中...")
            self.generate_btn.setEnabled(False)

            # 基于输入内容生成标题和内容
            title = self._generate_title()
            content = self._generate_content()
            
            # 生成示例图片URL（实际项目中可以替换为真实的图片生成服务）
            cover_image = self._generate_placeholder_image("封面图")
            content_images = [
                self._generate_placeholder_image(f"内容图{i+1}") 
                for i in range(random.randint(2, 4))
            ]

            result = {
                'title': title,
                'content': content,
                'cover_image': cover_image,
                'content_images': content_images,
                'input_text': self.input_text
            }

            print(f"✅ 备用内容生成成功: {title}")
            self.finished.emit(result)

        except Exception as e:
            error_msg = f"备用内容生成失败: {str(e)}"
            print(f"❌ {error_msg}")
            self.error.emit(error_msg)
        finally:
            # 恢复按钮状态
            self.generate_btn.setText("✨ 生成内容")
            self.generate_btn.setEnabled(True)

    def _generate_title(self):
        """生成标题"""
        if not self.header_title:
            self.header_title = "精彩分享"
        
        # 基于输入内容的关键词生成标题
        keywords = self.input_text.split()[:3]  # 取前3个词作为关键词
        
        title_templates = [
            f"{self.header_title}：{' '.join(keywords)}的深度解析",
            f"关于{' '.join(keywords)}，你需要知道这些",
            f"{self.header_title} | {' '.join(keywords)}完全指南",
            f"深度好文：{' '.join(keywords)}的那些事",
            f"{self.header_title}分享：{' '.join(keywords)}实用攻略"
        ]
        
        return random.choice(title_templates)

    def _generate_content(self):
        """生成内容"""
        # 基于输入文本生成结构化内容
        content_parts = [
            f"📝 关于「{self.input_text}」的分享",
            "",
            "🔍 核心要点：",
            f"• {self.input_text}是一个值得深入了解的话题",
            "• 通过系统学习可以获得更好的效果",
            "• 实践和理论相结合是关键",
            "",
            "💡 实用建议：",
            "• 保持持续学习的态度",
            "• 多与同行交流分享经验",
            "• 关注最新的发展趋势",
            "",
            "🎯 小结：",
            f"希望这篇关于{self.input_text}的分享对大家有帮助！",
            "",
            f"✍️ 作者：{self.author or '小红书AI助手'}",
            "",
            "#学习分享 #干货内容 #实用攻略"
        ]
        
        return "\n".join(content_parts)

    def _generate_placeholder_image(self, title):
        """生成占位图片URL"""
        # 使用占位图服务
        width = random.randint(400, 800)
        height = random.randint(400, 600)
        
        # 使用更可靠的占位图服务（移除有SSL问题的via.placeholder.com）
        placeholder_services = [
            f"https://picsum.photos/{width}/{height}?random={random.randint(1, 1000)}",
            f"https://dummyimage.com/{width}x{height}/4ECDC4/FFFFFF&text={title}",
            f"https://placehold.co/{width}x{height}/png?text={title}"
        ]
        
        return random.choice(placeholder_services) 