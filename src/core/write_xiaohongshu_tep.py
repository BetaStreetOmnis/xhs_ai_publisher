# 小红书的自动发稿
from playwright.async_api import async_playwright
import time
import json
import os
import sys
import logging
import asyncio
from PyQt5.QtWidgets import QInputDialog, QLineEdit
from PyQt5.QtCore import QObject, pyqtSignal, QMetaObject, Qt, QThread, pyqtSlot
from PyQt5.QtWidgets import QApplication
log_path = os.path.expanduser('~/Desktop/xhsai_error.log')
logging.basicConfig(filename=log_path, level=logging.DEBUG)

class VerificationCodeHandler(QObject):
    code_received = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.code = None
        self.dialog = None
        
    async def get_verification_code(self):
        # 确保在主线程中执行
        if QApplication.instance().thread() != QThread.currentThread():
            # 如果不在主线程，使用moveToThread移动到主线程
            self.moveToThread(QApplication.instance().thread())
            # 使用invokeMethod确保在主线程中执行
            QMetaObject.invokeMethod(self, "_show_dialog", Qt.ConnectionType.BlockingQueuedConnection)
        else:
            # 如果已经在主线程，直接执行
            self._show_dialog()
        
        # 等待代码输入完成
        while self.code is None:
            await asyncio.sleep(0.1)
            
        return self.code
    
    @pyqtSlot()
    def _show_dialog(self):
        code, ok = QInputDialog.getText(None, "验证码", "请输入验证码:", QLineEdit.EchoMode.Normal)
        if ok:
            self.code = code
            self.code_received.emit(code)
        else:
            self.code = ""

class XiaohongshuPoster:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.verification_handler = VerificationCodeHandler()
        self.loop = None
        # 不再在初始化时调用 initialize，而是让调用者显式调用
        
    async def initialize(self):
        """初始化浏览器"""
        if self.playwright is not None:
            return
            
        try:
            print("开始初始化Playwright...")
            self.playwright = await async_playwright().start()

            # 获取可执行文件所在目录
            launch_args = {
                'headless': False,
                'args': [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-infobars',
                    '--start-maximized',
                    '--ignore-certificate-errors',
                    '--ignore-ssl-errors'
                ]
            }

            chromium_path = None

            if getattr(sys, 'frozen', False):
                # 如果是打包后的可执行文件
                executable_dir = os.path.dirname(sys.executable)
                logging.debug(f"executable_dir: {executable_dir}")
                if sys.platform == 'darwin':  # macOS系统
                    if 'XhsAi' in executable_dir:
                        # 如果在 DMG 中运行
                        browser_path = os.path.join(
                            executable_dir, "ms-playwright")
                    else:
                        # 如果已经安装到应用程序文件夹
                        browser_path = os.path.join(
                            executable_dir, "Contents", "MacOS", "ms-playwright")
                    logging.debug(f"浏览器路径: {browser_path}")
                    chromium_path = os.path.join(
                        browser_path, "chromium-1161/chrome-mac/Chromium.app/Contents/MacOS/Chromium")
                else:
                    # Windows系统
                    executable_dir = sys._MEIPASS
                    print(f"临时解压目录: {executable_dir}")
                    browser_path = os.path.join(executable_dir, "ms-playwright")
                    print(f"浏览器路径: {browser_path}")
                    chromium_path = os.path.join(
                        browser_path, "chrome-win", "chrome.exe")
                    logging.debug(f"Chromium 路径: {chromium_path}")
            logging.debug(f"Chromium 路径: {chromium_path}")
            if chromium_path:
                # 确保浏览器文件存在且有执行权限
                if os.path.exists(chromium_path):
                    os.chmod(chromium_path, 0o755)
                    launch_args['executable_path'] = chromium_path
                else:
                    raise Exception(f"浏览器文件不存在: {chromium_path}")

            # 获取默认的 Chromium 可执行文件路径
            self.browser = await self.playwright.chromium.launch(**launch_args)
            # 创建新的上下文时设置权限
            self.context = await self.browser.new_context(
                permissions=['geolocation']  # 自动允许位置信息访问
            )
            self.page = await self.context.new_page()
            
            # 注入stealth.min.js
            stealth_js = """
            (function(){
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Open Source Technology Center';
                    }
                    if (parameter === 37446) {
                        return 'Mesa DRI Intel(R) HD Graphics (SKL GT2)';
                    }
                    return getParameter.apply(this, arguments);
                };
                
                const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
                Element.prototype.getBoundingClientRect = function() {
                    const rect = originalGetBoundingClientRect.apply(this, arguments);
                    rect.width = Math.round(rect.width);
                    rect.height = Math.round(rect.height);
                    return rect;
                };
                
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh']
                });
                
                window.chrome = {
                    runtime: {}
                };
                
                // 禁用Service Worker注册以避免错误
                if ('serviceWorker' in navigator) {
                    const originalRegister = navigator.serviceWorker.register;
                    navigator.serviceWorker.register = function() {
                        return Promise.reject(new Error('Service Worker registration disabled'));
                    };
                    
                    // 也可以完全移除serviceWorker
                    Object.defineProperty(navigator, 'serviceWorker', {
                        get: () => undefined
                    });
                }
                
                // 捕获并忽略Service Worker相关错误
                window.addEventListener('error', function(e) {
                    if (e.message && e.message.includes('serviceWorker')) {
                        e.preventDefault();
                        return false;
                    }
                });
                
                // 捕获未处理的Promise拒绝（Service Worker相关）
                window.addEventListener('unhandledrejection', function(e) {
                    if (e.reason && e.reason.message && e.reason.message.includes('serviceWorker')) {
                        e.preventDefault();
                        return false;
                    }
                });
            })();
            """
            await self.page.add_init_script(stealth_js)
            
            print("浏览器启动成功！")
            logging.debug("浏览器启动成功！")
            
            # 获取用户主目录
            home_dir = os.path.expanduser('~')
            app_dir = os.path.join(home_dir, '.xhs_system')
            if not os.path.exists(app_dir):
                os.makedirs(app_dir)

            # 设置token和cookies文件路径
            self.token_file = os.path.join(app_dir, "xiaohongshu_token.json")
            self.cookies_file = os.path.join(app_dir, "xiaohongshu_cookies.json")
            self.token = self._load_token()
            await self._load_cookies()

        except Exception as e:
            print(f"初始化过程中出现错误: {str(e)}")
            logging.debug(f"初始化过程中出现错误: {str(e)}")
            await self.close(force=True)  # 确保资源被正确释放
            raise

    def _load_token(self):
        """从文件加载token"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    token_data = json.load(f)
                    # 检查token是否过期
                    if token_data.get('expire_time', 0) > time.time():
                        return token_data.get('token')
            except:
                pass
        return None

    def _save_token(self, token):
        """保存token到文件"""
        token_data = {
            'token': token,
            # token有效期设为30天
            'expire_time': time.time() + 30 * 24 * 3600
        }
        with open(self.token_file, 'w') as f:
            json.dump(token_data, f)

    async def _load_cookies(self):
        """从文件加载cookies"""
        if os.path.exists(self.cookies_file):
            try:
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                    # 确保cookies包含必要的字段
                    for cookie in cookies:
                        if 'domain' not in cookie:
                            cookie['domain'] = '.xiaohongshu.com'
                        if 'path' not in cookie:
                            cookie['path'] = '/'
                    await self.context.add_cookies(cookies)
            except Exception as e:
                logging.debug(f"加载cookies失败: {str(e)}")

    async def _save_cookies(self):
        """保存cookies到文件"""
        try:
            cookies = await self.context.cookies()
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f)
        except Exception as e:
            logging.debug(f"保存cookies失败: {str(e)}")

    async def login(self, phone, country_code="+86"):
        """登录小红书"""
        await self.ensure_browser()  # 确保浏览器已初始化
        # 如果token有效则直接返回
        if self.token:
            return

        # 尝试加载cookies进行登录
        await self.page.goto("https://creator.xiaohongshu.com/login", wait_until="networkidle")
        # 先清除所有cookies
        await self.context.clear_cookies()
        
        # 重新加载cookies
        await self._load_cookies()
        # 刷新页面并等待加载完成
        await self.page.reload(wait_until="networkidle")

        # 检查是否已经登录
        current_url = self.page.url
        if "login" not in current_url:
            print("使用cookies登录成功")
            self.token = self._load_token()
            await self._save_cookies()
            return
        else:
            # 清理无效的cookies
            await self.context.clear_cookies()
            
        # 如果cookies登录失败，则进行手动登录
        await self.page.goto("https://creator.xiaohongshu.com/login")
        await asyncio.sleep(1)

        # 输入手机号
        await self.page.fill("//input[@placeholder='手机号']", phone)

        await asyncio.sleep(2)
        # 点击发送验证码按钮
        try:
            await self.page.click(".css-uyobdj")
        except:
            try:
                await self.page.click(".css-1vfl29")
            except:
                try:
                    await self.page.click("//button[text()='发送验证码']")
                except:
                    print("无法找到发送验证码按钮")

        # 使用信号机制获取验证码
        verification_code = await self.verification_handler.get_verification_code()
        if verification_code:
            await self.page.fill("//input[@placeholder='验证码']", verification_code)

        # 点击登录按钮
        await self.page.click(".beer-login-btn")

        # 等待登录成功
        await asyncio.sleep(3)
        # 保存cookies
        await self._save_cookies()

    async def post_article(self, title, content, images=None):
        """发布文章
        Args:
            title: 文章标题
            content: 文章内容
            images: 图片路径列表
        """
        await self.ensure_browser()  # 确保浏览器已初始化
        print("点击发布按钮")
        # 点击发布按钮
        await self.page.click(".btn.el-tooltip__trigger.el-tooltip__trigger")

        # 切换到上传图文选项卡
        print("切换到上传图文选项卡...")
        try:
            # 等待选项卡加载
            await self.page.wait_for_selector(".creator-tab", timeout=10000)
            
            # 使用JavaScript直接获取第二个选项卡并点击
            await self.page.evaluate("""
                () => {
                    const tabs = document.querySelectorAll('.creator-tab');
                    if (tabs.length > 1) {
                        tabs[1].click();
                        return true;
                    }
                    return false;
                }
            """)
            print("使用JavaScript方法点击第二个选项卡")
            
            await asyncio.sleep(2)
        except Exception as e:
            print(f"切换选项卡失败: {e}")
            await self.page.screenshot(path="debug_tabs.png")

        # 上传图片
        if images:
            async with self.page.expect_file_chooser() as fc_info:
                await self.page.click(".upload-input")
            file_chooser = await fc_info.value
            await file_chooser.set_files(images)
            await asyncio.sleep(1)

        await asyncio.sleep(3)
        # 输入标题
        await self.page.fill(".d-text", title)

        # 输入内容
        print(content)
        await self.page.fill(".ql-editor", content)

        # 发布
        await asyncio.sleep(1)
        # await self.page.click(".el-button.publishBtn")

    async def close(self, force=False):
        """关闭浏览器
        Args:
            force: 是否强制关闭浏览器，默认为False
        """
        try:
            if force:
                if self.context:
                    await self.context.close()
                if self.browser:
                    await self.browser.close()
                if self.playwright:
                    await self.playwright.stop()
                self.playwright = None
                self.browser = None
                self.context = None
                self.page = None
        except Exception as e:
            logging.debug(f"关闭浏览器时出错: {str(e)}")

    async def ensure_browser(self):
        """确保浏览器已初始化"""
        if not self.playwright:
            await self.initialize()