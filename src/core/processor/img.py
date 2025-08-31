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
                # 添加SSL验证跳过和更长的超时时间
                response = requests.get(url, verify=False, timeout=30)
                if response.status_code == 200:
                    # 保存图片
                    img_path = os.path.join(self.img_dir, f'{title}.jpg')
                    os.makedirs(os.path.dirname(img_path), exist_ok=True)

                    # 保存原始图片
                    with open(img_path, 'wb') as f:
                        f.write(response.content)

                    # 处理图片预览
                    image = Image.open(io.BytesIO(response.content))

                    # 计算缩放比例，保持宽高比
                    width, height = image.size
                    max_size = 360  # 调整预览图片的最大尺寸
                    scale = min(max_size/width, max_size/height)
                    new_width = int(width * scale)
                    new_height = int(height * scale)

                    # 缩放图片
                    image = image.resize((new_width, new_height), Image.LANCZOS)

                    # 创建白色背景
                    background = Image.new('RGB', (max_size, max_size), 'white')
                    # 将图片粘贴到中心位置
                    offset = ((max_size - new_width) // 2,
                              (max_size - new_height) // 2)
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
                else:
                    raise Exception(f"下载图片失败: HTTP {response.status_code}")

            except Exception as e:
                retries -= 1
                if retries > 0:
                    print(f"处理图片失败,还剩{retries}次重试: {str(e)}")
                    time.sleep(1)  # 重试前等待1秒
                else:
                    print(f"处理图片失败,重试次数已用完: {str(e)}")
                    return None, None
