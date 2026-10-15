#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备用内容生成器 - 当主API不可用时的备选方案
"""

import json
import random
import re
import time
import os
import uuid
from PyQt5.QtCore import QThread, pyqtSignal
from src.core.services.system_image_template_service import system_image_template_service


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
        self.info_reason = ""

    def run(self):
        """生成备用内容"""
        try:
            print("🔄 主API不可用，使用备用内容生成器...")
            
            # 更新按钮状态
            self.generate_btn.setText("⏳ 原文预览中...")
            self.generate_btn.setEnabled(False)

            # 无模型时只预览用户原文，不增加固定文案。
            title = self._generate_title()
            content, content_pages = self._generate_content_and_pages()
            
            # 优先使用系统模板图片生成（如 x-auto-publisher）；失败则回退到本地占位图
            cover_image = ""
            content_images = []
            try:
                generated = system_image_template_service.generate_post_images(
                    title=title,
                    content=content,
                    content_pages=content_pages,
                    page_count=max(1, len(content_pages)),
                )
                if generated:
                    cover_image, content_images = generated
            except Exception:
                cover_image = ""
                content_images = []

            if not cover_image or not content_images:
                # 生成本地占位图片（离线可用，避免外部图片服务不稳定）
                cover_image, content_images = self._generate_local_placeholder_images(title, count=max(1, len(content_pages)))

            result = {
                'title': title,
                'content': content,
                'cover_image': cover_image,
                'content_images': content_images,
                'content_pages': content_pages,
                'input_text': self.input_text,
                'generator': 'backup',
                'info_reason': self.info_reason or '模型不可用，当前为原文预览，未生成新文案'
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
        """Use a supplied heading or source opening without inventing a headline."""
        heading = str(self.header_title or "").strip()
        if heading:
            return heading[:20]
        source = str(self.input_text or "").strip()
        return source.splitlines()[0][:20] if source else "草稿预览"

    def _generate_content_and_pages(self):
        """Keep the source verbatim when no model is available; only paginate it."""
        content = str(self.input_text or "").strip()
        if not content:
            raise ValueError("请输入正文或参考素材后再预览")
        pages = [content[i:i + 400] for i in range(0, len(content), 400)]
        return content, pages

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

    def _generate_local_placeholder_images(self, title: str, count: int = 3):
        """生成本地占位图片，避免依赖外部图片服务。"""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except Exception as e:
            raise Exception(f"Pillow 未安装或不可用: {e}")

        base_dir = os.path.join(os.path.expanduser('~'), '.xhs_system', 'generated_imgs')
        os.makedirs(base_dir, exist_ok=True)

        def _make(path: str, label: str):
            width, height = 1080, 1440
            img = Image.new('RGB', (width, height), (245, 245, 245))
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
            text = f"{label}\n{(title or '').strip()[:40]}"
            draw.multiline_text((60, 80), text, fill=(30, 30, 30), font=font, spacing=10)
            img.save(path, format='JPEG', quality=90)

        unique = uuid.uuid4().hex[:8]
        ts = int(time.time())
        cover_path = os.path.join(base_dir, f'cover_{ts}_{unique}.jpg')
        _make(cover_path, "封面")

        content_paths = []
        for i in range(max(1, int(count))):
            p = os.path.join(base_dir, f'content_{i+1}_{ts}_{unique}.jpg')
            _make(p, f"内容图{i+1}")
            content_paths.append(p)

        return cover_path, content_paths
