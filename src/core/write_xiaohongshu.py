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
                    '--ignore-ssl-errors',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows',
                    '--memory-pressure-off',
                    '--max_old_space_size=4096'
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

            # 尝试使用系统Chrome，如果失败再使用Chromium
            try:
                # 检查系统Chrome路径
                system_chrome_paths = [
                    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                    '/Applications/Chromium.app/Contents/MacOS/Chromium'
                ]
                
                chrome_found = False
                for chrome_path in system_chrome_paths:
                    if os.path.exists(chrome_path):
                        launch_args['executable_path'] = chrome_path
                        chrome_found = True
                        print(f"使用系统Chrome: {chrome_path}")
                        break
                
                if not chrome_found and chromium_path and os.path.exists(chromium_path):
                    launch_args['executable_path'] = chromium_path
                    print(f"使用打包Chromium: {chromium_path}")
                
                self.browser = await self.playwright.chromium.launch(**launch_args)
            except Exception as e:
                # 如果指定路径失败，移除executable_path让playwright使用默认路径
                print(f"指定路径启动失败: {e}")
                if 'executable_path' in launch_args:
                    del launch_args['executable_path']
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
        
        try:
            # 首先导航到创作者中心
            print("导航到创作者中心...")
            await self.page.goto("https://creator.xiaohongshu.com", wait_until="networkidle")
            await asyncio.sleep(3)
            
            # 检查是否需要登录
            current_url = self.page.url
            if "login" in current_url:
                print("需要重新登录...")
                raise Exception("用户未登录，请先登录")
            
            print("点击发布笔记按钮...")
            # 根据实际HTML结构点击发布按钮
            publish_selectors = [
                ".publish-video .btn",  # 根据日志显示这个选择器工作正常
                "button:has-text('发布笔记')",
                ".btn:text('发布笔记')",
                "//div[contains(@class, 'btn')][contains(text(), '发布笔记')]"
            ]
            
            publish_clicked = False
            for selector in publish_selectors:
                try:
                    print(f"尝试发布按钮选择器: {selector}")
                    await self.page.wait_for_selector(selector, timeout=5000)
                    await self.page.click(selector)
                    print(f"成功点击发布按钮: {selector}")
                    publish_clicked = True
                    break
                except Exception as e:
                    print(f"发布按钮选择器 {selector} 失败: {e}")
                    continue
            
            if not publish_clicked:
                await self.page.screenshot(path="debug_publish_button.png")
                raise Exception("无法找到发布按钮")
            
            await asyncio.sleep(3)

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

            # 等待页面切换完成
            await asyncio.sleep(3)
            # time.sleep(15) # 长时间同步阻塞，应避免，Playwright有自己的等待机制
            
            # 上传图片（如果有）
            print("--- 开始图片上传流程 ---")
            if images:
                print("--- 开始图片上传流程 ---")
                try:
                    # 等待上传区域关键元素（如上传按钮）出现
                    print("等待上传按钮 '.upload-button' 出现...")
                    await self.page.wait_for_selector(".upload-button", timeout=20000) 
                    await asyncio.sleep(1.5) # 短暂稳定延时

                    upload_success = False
                    
                    # --- 首选方法: 点击明确的 "上传图片" 按钮 ---
                    if not upload_success:
                        print("尝试首选方法: 点击 '.upload-button'")
                        try:
                            button_selector = ".upload-button"
                            await self.page.wait_for_selector(button_selector, state="visible", timeout=10000)
                            print(f"按钮 '{button_selector}' 可见，准备点击.")
                            
                            async with self.page.expect_file_chooser(timeout=15000) as fc_info:
                                await self.page.click(button_selector, timeout=7000)
                                print(f"已点击 '{button_selector}'. 等待文件选择器...")
                            
                            file_chooser = await fc_info.value
                            print(f"文件选择器已出现: {file_chooser}")
                            await file_chooser.set_files(images)
                            print(f"已通过文件选择器设置文件: {images}")
                            upload_success = True
                            print(" 首选方法成功: 点击 '.upload-button' 并设置文件")
                        except Exception as e:
                            print(f" 首选方法 (点击 '.upload-button') 失败: {e}")
                            if self.page: await self.page.screenshot(path="debug_upload_button_click_failed.png")

                    # --- 方法0.5 (新增): 点击拖拽区域的文字提示区 ---
                    if not upload_success:
                        print("尝试方法0.5: 点击拖拽提示区域 ( '.wrapper' 或 '.drag-over')")
                        try:
                            clickable_area_selectors = [".wrapper", ".drag-over"]
                            clicked_area_successfully = False
                            for area_selector in clickable_area_selectors:
                                try:
                                    print(f"尝试点击区域: '{area_selector}'")
                                    await self.page.wait_for_selector(area_selector, state="visible", timeout=5000)
                                    print(f"区域 '{area_selector}' 可见，准备点击.")
                                    async with self.page.expect_file_chooser(timeout=10000) as fc_info:
                                        await self.page.click(area_selector, timeout=5000)
                                        print(f"已点击区域 '{area_selector}'. 等待文件选择器...")
                                    file_chooser = await fc_info.value
                                    print(f"文件选择器已出现 (点击区域 '{area_selector}'): {file_chooser}")
                                    await file_chooser.set_files(images)
                                    print(f"已通过文件选择器 (点击区域 '{area_selector}') 设置文件: {images}")
                                    upload_success = True
                                    clicked_area_successfully = True
                                    print(f" 方法0.5成功: 点击区域 '{area_selector}' 并设置文件")
                                    break 
                                except Exception as inner_e:
                                    print(f"尝试点击区域 '{area_selector}' 失败: {inner_e}")
                            
                            if not clicked_area_successfully: 
                                print(f" 方法0.5 (点击拖拽提示区域) 所有内部尝试均失败")
                                if self.page: await self.page.screenshot(path="debug_upload_all_area_clicks_failed.png")
                                
                        except Exception as e: 
                            print(f"❌方法0.5 (点击拖拽提示区域) 步骤发生意外错误: {e}")
                            if self.page: await self.page.screenshot(path="debug_upload_method0_5_overall_failure.png")

                    # --- 方法1 (备选): 直接操作 .upload-input (使用 set_input_files) ---
                    if not upload_success:
                        print("尝试方法1: 直接操作 '.upload-input' 使用 set_input_files")
                        try:
                            input_selector = ".upload-input"
                            # 对于 set_input_files，元素不一定需要可见，但必须存在于DOM中
                            await self.page.wait_for_selector(input_selector, state="attached", timeout=5000)
                            print(f"找到 '{input_selector}'. 尝试通过 set_input_files 设置文件...")
                            await self.page.set_input_files(input_selector, files=images, timeout=10000)
                            print(f"已通过 set_input_files 为 '{input_selector}' 设置文件: {images}")
                            upload_success = True # 假设 set_input_files 成功即代表文件已选择
                            print(" 方法1成功: 直接通过 set_input_files 操作 '.upload-input'")
                        except Exception as e:
                            print(f" 方法1 (set_input_files on '.upload-input') 失败: {e}")
                            if self.page: await self.page.screenshot(path="debug_upload_input_set_files_failed.png")
                    
                    # --- 方法3 (备选): JavaScript直接触发隐藏的input点击 ---
                    if not upload_success:
                        print("尝试方法3: JavaScript点击隐藏的 '.upload-input'")
                        try:
                            input_selector = ".upload-input"
                            await self.page.wait_for_selector(input_selector, state="attached", timeout=5000)
                            print(f"找到 '{input_selector}'. 尝试通过JS点击...")
                            async with self.page.expect_file_chooser(timeout=10000) as fc_info:
                                await self.page.evaluate(f"document.querySelector('{input_selector}').click();")
                                print(f"已通过JS点击 '{input_selector}'. 等待文件选择器...")
                            file_chooser = await fc_info.value
                            print(f"文件选择器已出现 (JS点击): {file_chooser}")
                            await file_chooser.set_files(images)
                            print(f"已通过文件选择器 (JS点击后) 设置文件: {images}")
                            upload_success = True
                            print(" 方法3成功: JavaScript点击 '.upload-input' 并设置文件")
                        except Exception as e:
                            print(f"方法3 (JavaScript点击 '.upload-input') 失败: {e}")
                            if self.page: await self.page.screenshot(path="debug_upload_js_input_click_failed.png")

                    # --- 上传后检查 --- 
                    if upload_success:
                        print("图片已通过某种方法设置/点击，进入上传后检查流程，等待处理和预览...")
                        await asyncio.sleep(7)  # 增加等待时间，等待图片在前端处理和预览

                        upload_check_js = '''
                            () => {
                                const indicators = [
                                    '.img-card', '.image-preview', '.uploaded-image', 
                                    '.upload-success', '[class*="preview"]', 'img[src*="blob:"]',
                                    '.banner-img', '.thumbnail', '.upload-display-item',
                                    '.note-image-item', /*小红书笔记图片项*/
                                    '.preview-item', /*通用预览项*/
                                    '.gecko-modal-content img' /* 可能是某种弹窗内的预览 */
                                ];
                                let foundVisible = false;
                                console.log("JS: Checking for upload indicators...");
                                for (let selector of indicators) {
                                    const elements = document.querySelectorAll(selector);
                                    if (elements.length > 0) {
                                        for (let el of elements) {
                                            const rect = el.getBoundingClientRect();
                                            const style = getComputedStyle(el);
                                            if (rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0') {
                                                console.log("JS: Found visible indicator:", selector, el);
                                                foundVisible = true;
                                                break;
                                            }
                                        }
                                    }
                                    if (foundVisible) break;
                                }
                                console.log("JS: Upload indicator check result (foundVisible):", foundVisible);
                                return foundVisible;
                            }
                        '''
                        print("执行JS检查图片预览...")
                        upload_check_successful = await self.page.evaluate(upload_check_js)
                        
                        if upload_check_successful:
                            print(" 图片上传并处理成功 (检测到可见的预览元素)")
                        else:
                            print(" 图片可能未成功处理或预览未出现(JS检查失败)，请检查截图")
                            if self.page: await self.page.screenshot(path="debug_upload_preview_missing_after_js_check.png")
                    else:
                        print(" 所有主要的图片上传方法均失败。无法进行预览检查。")
                        if self.page: await self.page.screenshot(path="debug_upload_all_methods_failed_final.png")
                        
                except Exception as e:
                    print(f"整个图片上传过程出现严重错误: {e}")
                    import traceback
                    traceback.print_exc() 
                    if self.page: await self.page.screenshot(path="debug_image_upload_critical_error_outer.png")
            
            # 输入标题和内容
            print("--- 开始输入标题和内容 ---")
            await asyncio.sleep(5)  # 给更多时间让编辑界面加载
            # time.sleep(1000) # 已移除
            # # 尝试查找并点击编辑区域以激活它
            # try:
            #     await self.page.click(".editor-wrapper", timeout=5000)
            #     print("成功点击编辑区域")
            # except:
            #     print("尝试点击编辑区域失败")
            
            # 输入标题
            print("输入标题...")
            try:
                # 使用具体的标题选择器
                title_selectors = [
                    "input.d-text[placeholder='填写标题会有更多赞哦～']",
                    "input.d-text",
                    "input[placeholder='填写标题会有更多赞哦～']",
                    "input.title",
                    "[data-placeholder='标题']",
                    "[contenteditable='true']:first-child",
                    ".note-editor-wrapper input",
                    ".edit-wrapper input"
                ]
                
                title_filled = False
                for selector in title_selectors:
                    try:
                        print(f"尝试标题选择器: {selector}")
                        await self.page.wait_for_selector(selector, timeout=5000)
                        await self.page.fill(selector, title)
                        print(f"标题输入成功，使用选择器: {selector}")
                        title_filled = True
                        break
                    except Exception as e:
                        print(f"标题选择器 {selector} 失败: {e}")
                        continue
                
                if not title_filled:
                    # 尝试使用键盘快捷键输入
                    try:
                        await self.page.keyboard.press("Tab")
                        await self.page.keyboard.type(title)
                        print("使用键盘输入标题")
                    except Exception as e:
                        print(f"键盘输入标题失败: {e}")
                        print("无法输入标题")
                    
            except Exception as e:
                print(f"标题输入失败: {e}")

            # 输入内容
            print("输入内容...")
            try:
                # 尝试更多可能的内容选择器
                content_selectors = [
                    "[contenteditable='true']:nth-child(2)",
                    ".note-content",
                    "[data-placeholder='添加正文']",
                    "[role='textbox']",
                    ".DraftEditor-root"
                ]
                
                content_filled = False
                for selector in content_selectors:
                    try:
                        print(f"尝试内容选择器: {selector}")
                        await self.page.wait_for_selector(selector, timeout=5000)
                        await self.page.fill(selector, content)
                        print(f"内容输入成功，使用选择器: {selector}")
                        content_filled = True
                        break
                    except Exception as e:
                        print(f"内容选择器 {selector} 失败: {e}")
                        continue
                
                if not content_filled:
                    # 尝试使用键盘快捷键输入
                    try:
                        await self.page.keyboard.press("Tab")
                        await self.page.keyboard.press("Tab")
                        await self.page.keyboard.type(content)
                        print("使用键盘输入内容")
                    except Exception as e:
                        print(f"键盘输入内容失败: {e}")
                        print("无法输入内容")
                    
            except Exception as e:
                print(f"内容输入失败: {e}")

            # 等待用户手动发布
            print("请手动检查内容并点击发布按钮完成发布...")
            await asyncio.sleep(60) # 延长等待时间，给用户充分时间检查
            
        except Exception as e:
            print(f"发布文章时出错: {str(e)}")
            # 截图用于调试
            try:
                if self.page: # Check if page object exists before screenshot
                    await self.page.screenshot(path="error_screenshot.png")
                    print("已保存错误截图: error_screenshot.png")
            except:
                pass # Ignore screenshot errors
            raise

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


if __name__ == "__main__":
    async def main():
        poster = XiaohongshuPoster()
        try:
            print("开始初始化...")
            await poster.initialize()
            print("初始化完成")
            
            print("开始登录...")
            await poster.login("18810788888", "+86")
            print("登录完成")
            
            print("开始发布文章...")
            await poster.post_article("测试文章", "这是一个测试内容，用于验证自动发布功能。", [r"C:\Users\Administrator\Pictures\506d9fc834d786df28971fdfa27f5ae7.jpg"])  # 提供图片路径
            print("文章发布流程完成")
            
        except Exception as e:
            print(f"程序执行出错: {str(e)}")
            import traceback
            traceback.print_exc()
            # 截图调试
            try:
                if poster.page: # Check if page object exists before screenshot
                    await poster.page.screenshot(path="error_debug.png")
                    print("已保存错误截图: error_debug.png")
            except:
                pass # Ignore screenshot errors
        finally:
            print("等待10秒后关闭浏览器...")
            await asyncio.sleep(10)
            await poster.close(force=True)
            print("程序结束")
    
    asyncio.run(main())
