import io
import time
from PyQt5.QtCore import QThread, pyqtSignal

import os
import requests

from PyQt5.QtGui import QPixmap, QImage


from PIL import Image


class ImageProcessorThread(QThread):
    finished = pyqtSignal(list, list)  # 发送图片路径列表和图片信息列表
    error = pyqtSignal(str)

    PREVIEW_WIDTH = 360
    PREVIEW_HEIGHT = 480

    def __init__(self, cover_image_url, content_image_urls):
        super().__init__()
        self.cover_image_url = cover_image_url
        self.content_image_urls = content_image_urls
        # 获取用户主目录
        img_dir = os.path.join(os.path.expanduser('~'), '.xhs_system')
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)

        # 配置文件路径
        self.img_dir = os.path.join(img_dir, 'imgs')

    def run(self):
        try:
            images = []
            image_list = []

            # 并发处理所有图片
            from concurrent.futures import ThreadPoolExecutor

            def process_image_with_title(args):
                url, title = args
                return self.process_image(url, title)

            with ThreadPoolExecutor(max_workers=4) as executor:
                # 创建有序的future列表
                futures = []

                # 添加封面图任务
                if self.cover_image_url:
                    future = executor.submit(process_image_with_title,
                                             (self.cover_image_url, "封面图"))
                    futures.append((-1, future))  # 用-1确保封面图排在最前

                # 添加内容图任务
                for i, url in enumerate(self.content_image_urls):
                    future = executor.submit(process_image_with_title,
                                             (url, f"内容图{i+1}"))
                    futures.append((i, future))

                # 按照原始顺序处理结果
                for i, future in sorted(futures, key=lambda x: x[0]):
                    img_path, pixmap_info = future.result()
                    if img_path and pixmap_info:
                        images.append(img_path)
                        image_list.append(pixmap_info)

            self.finished.emit(images, image_list)
        except Exception as e:
            self.error.emit(str(e))

    def process_image(self, url, title):
        retries = 3
        while retries > 0:
            try:
                local_path = self._resolve_local_path(url)
                if local_path:
                    with open(local_path, 'rb') as f:
                        content = f.read()
                else:
                    # 添加SSL验证跳过和更长的超时时间
                    response = requests.get(url, verify=False, timeout=30)
                    if response.status_code != 200:
                        raise Exception(f"下载图片失败: HTTP {response.status_code}")
                    content = response.content

                # 保存图片（尽量保持真实格式，避免 PNG 内容写成 .jpg）
                ext = self._guess_image_extension(local_path, content)
                img_path = os.path.join(self.img_dir, f'{title}{ext}')
                os.makedirs(os.path.dirname(img_path), exist_ok=True)

                # 保存原始图片（保持现有行为：覆盖同名文件）
                with open(img_path, 'wb') as f:
                    f.write(content)

                # 处理图片预览
                image = Image.open(io.BytesIO(content))

                # 计算缩放比例，保持宽高比
                width, height = image.size
                target_w = self.PREVIEW_WIDTH
                target_h = self.PREVIEW_HEIGHT
                scale = min(target_w / width, target_h / height)
                new_width = int(width * scale)
                new_height = int(height * scale)

                # 缩放图片
                image = image.resize((new_width, new_height), Image.LANCZOS)

                # 创建白色背景
                background = Image.new('RGB', (target_w, target_h), 'white')
                # 将图片粘贴到中心位置
                offset = ((target_w - new_width) // 2, (target_h - new_height) // 2)
                background.paste(image, offset)

                # 转换为QPixmap
                img_bytes = io.BytesIO()
                background.save(img_bytes, format='PNG')
                img_data = img_bytes.getvalue()

                qimage = QImage.fromData(img_data)
                pixmap = QPixmap.fromImage(qimage)

                if pixmap.isNull():
                    raise Exception("无法创建有效的图片预览")

                return img_path, {'pixmap': pixmap, 'title': title}

            except Exception as e:
                retries -= 1
                if retries > 0:
                    print(f"处理图片失败,还剩{retries}次重试: {str(e)}")
                    time.sleep(1)  # 重试前等待1秒
                else:
                    print(f"处理图片失败,重试次数已用完: {str(e)}")
                    return None, None

    @staticmethod
    def _guess_image_extension(local_path, content: bytes) -> str:
        if isinstance(local_path, str) and local_path:
            ext = os.path.splitext(local_path)[1].lower()
            if ext in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
                return ext

        if not isinstance(content, (bytes, bytearray)):
            return ".jpg"

        head = bytes(content[:16])
        if head.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"
        if head.startswith(b"\xff\xd8"):
            return ".jpg"
        if head.startswith(b"RIFF") and len(content) >= 12 and bytes(content[8:12]) == b"WEBP":
            return ".webp"
        return ".jpg"

    def _resolve_local_path(self, url):
        """支持直接传入本地图片路径（用于离线/本地生成图片）。"""
        if not url:
            return None

        if not isinstance(url, str):
            return None

        if url.startswith("file://"):
            candidate = url[len("file://"):]
        else:
            candidate = url

        candidate = os.path.expanduser(candidate)
        if os.path.exists(candidate) and os.path.isfile(candidate):
            return candidate

        return None
