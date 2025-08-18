from PyQt5.QtCore import QThread, pyqtSignal
import asyncio

from src.core.write_xiaohongshu import XiaohongshuPoster


class BrowserThread(QThread):
    # 添加信号
    login_status_changed = pyqtSignal(str, bool)  # 用于更新登录按钮状态
    preview_status_changed = pyqtSignal(str, bool)  # 用于更新预览按钮状态
    login_success = pyqtSignal(object)  # 用于传递poster对象
    login_error = pyqtSignal(str)  # 用于传递错误信息
    preview_success = pyqtSignal()  # 用于通知预览成功
    preview_error = pyqtSignal(str)  # 用于传递预览错误信息

    def __init__(self):
        super().__init__()
        self.poster = None
        self.action_queue = []
        self.is_running = True
        self.loop = None

    def run(self):
        # 创建新的事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # 在事件循环中运行主循环
        self.loop.run_until_complete(self.async_run())
        
        # 关闭事件循环
        self.loop.close()
        
    async def async_run(self):
        """异步主循环"""
        while self.is_running:
            if self.action_queue:
                action = self.action_queue.pop(0)
                try:
                    if action['type'] == 'login':
                        self.poster = XiaohongshuPoster()
                        await self.poster.initialize()
                        await self.poster.login(action['phone'])
                        self.login_success.emit(self.poster)
                    elif action['type'] == 'preview' and self.poster:
                        await self.poster.post_article(
                            action['title'],
                            action['content'],
                            action['images']
                        )
                        self.preview_success.emit()
                except Exception as e:
                    if action['type'] == 'login':
                        self.login_error.emit(str(e))
                    elif action['type'] == 'preview':
                        self.preview_error.emit(str(e))
            # 使用异步sleep而不是QThread.msleep
            await asyncio.sleep(0.1)  # 避免CPU占用过高

    def stop(self):
        self.is_running = False
        # 确保浏览器资源被释放
        if self.poster and self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.poster.close(force=True), self.loop)
