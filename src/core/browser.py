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
                        phone = (action.get('phone') or "").strip()
                        if not phone:
                            raise ValueError("手机号不能为空")

                        # 根据手机号匹配/创建用户，并作为当前用户
                        try:
                            from src.core.services.user_service import user_service
                        except Exception:
                            user_service = None

                        current_user = None
                        if user_service:
                            current_user = user_service.get_user_by_phone(phone)
                            if current_user:
                                user_service.switch_user(current_user.id)
                            else:
                                normalized_phone = "".join([c for c in phone if c.isdigit()]) or phone
                                username_base = f"user_{normalized_phone}"
                                username = username_base
                                suffix = 1
                                while user_service.get_user_by_username(username):
                                    username = f"{username_base}_{suffix}"
                                    suffix += 1
                                current_user = user_service.create_user(
                                    username=username,
                                    phone=phone,
                                    display_name=phone,
                                    set_current=True,
                                )

                        # 如果已存在浏览器会话，先关闭避免残留进程导致“偶发启动失败”
                        if self.poster:
                            try:
                                await self.poster.close(force=True)
                            except Exception:
                                pass
                            self.poster = None

                        # 读取当前用户的默认环境（代理/指纹）
                        browser_env = None
                        try:
                            from src.core.services.browser_environment_service import browser_environment_service

                            if current_user:
                                browser_env = browser_environment_service.get_default_environment(current_user.id)
                                if not browser_env:
                                    browser_environment_service.create_preset_environments(current_user.id)
                                    browser_env = browser_environment_service.get_default_environment(current_user.id)
                        except Exception:
                            browser_env = None

                        self.poster = XiaohongshuPoster(
                            user_id=(current_user.id if current_user else None),
                            browser_environment=browser_env,
                        )
                        await self.poster.initialize()
                        await self.poster.login(phone)

                        if user_service and current_user:
                            user_service.update_login_status(current_user.id, True)

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
                        # 登录阶段失败时，尽量释放浏览器资源，避免后续启动不稳定
                        try:
                            if self.poster:
                                await self.poster.close(force=True)
                        except Exception:
                            pass
                        finally:
                            self.poster = None

                        # 登录失败：更新数据库状态（不影响错误上报）
                        try:
                            from src.core.services.user_service import user_service

                            phone = (action.get('phone') or "").strip()
                            if phone:
                                u = user_service.get_user_by_phone(phone)
                                if u:
                                    user_service.update_login_status(u.id, False)
                        except Exception:
                            pass

                        msg = str(e)
                        if "Executable doesn't exist" in msg:
                            msg += "\n\n可能原因：Playwright 浏览器未安装/被杀毒清理。"
                            msg += "\n解决："
                            msg += "\n  - macOS/Linux："
                            msg += "\n    PLAYWRIGHT_BROWSERS_PATH=\"$HOME/.xhs_system/ms-playwright\" python -m playwright install chromium"
                            msg += "\n  - Windows（PowerShell）："
                            msg += "\n    $env:PLAYWRIGHT_BROWSERS_PATH=\"$HOME\\.xhs_system\\ms-playwright\"; python -m playwright install chromium"
                        self.login_error.emit(msg)
                    elif action['type'] == 'preview':
                        self.preview_error.emit(str(e))
            # 使用异步sleep而不是QThread.msleep
            await asyncio.sleep(0.1)  # 避免CPU占用过高

    def stop(self):
        self.is_running = False
        # 确保浏览器资源被释放
        if self.poster and self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self.poster.close(force=True), self.loop)
