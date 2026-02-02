# 小红书的自动发稿
from playwright.async_api import async_playwright
import time
import json
import os
import sys
import subprocess
import logging
import asyncio
from glob import glob
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
    def __init__(self, user_id: int = None, browser_environment=None):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.verification_handler = VerificationCodeHandler()
        self.loop = None
        self.user_id = user_id
        self.browser_environment = browser_environment
        # 不再在初始化时调用 initialize，而是让调用者显式调用

    def _get_env_value(self, key, default=None):
        env = self.browser_environment
        if env is None:
            return default
        if isinstance(env, dict):
            return env.get(key, default)
        return getattr(env, key, default)

    def _get_user_storage_dir(self) -> str:
        home_dir = os.path.expanduser('~')
        base_dir = os.path.join(home_dir, '.xhs_system')
        if self.user_id is None:
            return base_dir
        return os.path.join(base_dir, "users", str(self.user_id))

    def _build_playwright_proxy(self):
        if not self.browser_environment:
            return None

        proxy_enabled = bool(self._get_env_value("proxy_enabled", False))
        proxy_type = (self._get_env_value("proxy_type") or "").strip()
        if not proxy_enabled or not proxy_type or proxy_type == "direct":
            return None

        host = self._get_env_value("proxy_host")
        port = self._get_env_value("proxy_port")
        if not host or not port:
            return None

        scheme = proxy_type
        if scheme == "https":
            scheme = "http"

        proxy = {"server": f"{scheme}://{host}:{int(port)}"}
        username = self._get_env_value("proxy_username")
        password = self._get_env_value("proxy_password")
        if username:
            proxy["username"] = str(username)
        if password:
            proxy["password"] = str(password)
        return proxy

    def _build_context_options(self):
        options = {"permissions": ["geolocation"]}

        ua = self._get_env_value("user_agent")
        if ua:
            options["user_agent"] = ua

        try:
            vw = int(self._get_env_value("viewport_width", 0) or 0)
            vh = int(self._get_env_value("viewport_height", 0) or 0)
            if vw > 0 and vh > 0:
                options["viewport"] = {"width": vw, "height": vh}
        except Exception:
            pass

        try:
            sw = int(self._get_env_value("screen_width", 0) or 0)
            sh = int(self._get_env_value("screen_height", 0) or 0)
            if sw > 0 and sh > 0:
                options["screen"] = {"width": sw, "height": sh}
        except Exception:
            pass

        locale = self._get_env_value("locale")
        if locale:
            options["locale"] = locale

        tz = self._get_env_value("timezone")
        if tz:
            options["timezone_id"] = tz

        lat = self._get_env_value("geolocation_latitude")
        lng = self._get_env_value("geolocation_longitude")
        if lat and lng:
            try:
                options["geolocation"] = {"latitude": float(lat), "longitude": float(lng)}
            except Exception:
                pass

        return options

    def _candidate_ms_playwright_dirs(self):
        """返回可能存在 Playwright 浏览器缓存的目录列表（按优先级排序）。"""
        candidates = []

        home_dir = os.path.expanduser("~")

        # 项目自用目录（更不容易被系统清理）
        candidates.append(os.path.join(home_dir, ".xhs_system", "ms-playwright"))

        # Playwright 默认缓存目录
        if sys.platform == "win32":
            local_app_data = os.environ.get("LOCALAPPDATA") or os.path.join(home_dir, "AppData", "Local")
            candidates.append(os.path.join(local_app_data, "ms-playwright"))
        elif sys.platform == "darwin":
            candidates.append(os.path.join(home_dir, "Library", "Caches", "ms-playwright"))
        else:
            candidates.append(os.path.join(home_dir, ".cache", "ms-playwright"))

        # 打包版本：浏览器可能随应用一起带在 ms-playwright
        if getattr(sys, "frozen", False):
            if sys.platform == "win32":
                base_dir = getattr(sys, "_MEIPASS", None) or os.path.dirname(sys.executable)
                candidates.insert(0, os.path.join(base_dir, "ms-playwright"))
            elif sys.platform == "darwin":
                executable_dir = os.path.dirname(sys.executable)
                # DMG / .app 两种常见结构
                candidates.insert(0, os.path.join(executable_dir, "ms-playwright"))
                candidates.insert(0, os.path.join(executable_dir, "Contents", "MacOS", "ms-playwright"))

        # 去重并过滤不存在的目录
        seen = set()
        result = []
        for path in candidates:
            if not path or path in seen:
                continue
            seen.add(path)
            if os.path.exists(path):
                result.append(path)
        return result

    def _find_chromium_executable_under(self, root_dir: str):
        """在指定 ms-playwright 目录内查找 Chromium 可执行文件。"""
        if not root_dir or not os.path.exists(root_dir):
            return None

        if sys.platform == "win32":
            direct = os.path.join(root_dir, "chrome-win", "chrome.exe")
            if os.path.exists(direct):
                return direct

            candidates = glob(os.path.join(root_dir, "chromium-*", "chrome-win", "chrome.exe"))
            candidates.sort(reverse=True)
            for path in candidates:
                if os.path.exists(path):
                    return path

            for dirpath, _, filenames in os.walk(root_dir):
                if "chrome.exe" in filenames:
                    return os.path.join(dirpath, "chrome.exe")

        elif sys.platform == "darwin":
            candidates = glob(
                os.path.join(
                    root_dir,
                    "chromium-*",
                    "chrome-mac",
                    "Chromium.app",
                    "Contents",
                    "MacOS",
                    "Chromium",
                )
            )
            candidates.sort(reverse=True)
            for path in candidates:
                if os.path.exists(path):
                    return path

            for dirpath, _, filenames in os.walk(root_dir):
                if "Chromium" in filenames and dirpath.endswith(os.path.join("Contents", "MacOS")):
                    return os.path.join(dirpath, "Chromium")

        else:
            candidates = glob(os.path.join(root_dir, "chromium-*", "chrome-linux", "chrome"))
            candidates.sort(reverse=True)
            for path in candidates:
                if os.path.exists(path):
                    return path

            for dirpath, _, filenames in os.walk(root_dir):
                if "chrome" in filenames:
                    return os.path.join(dirpath, "chrome")

        return None

    def _find_playwright_chromium_executable(self):
        for root in self._candidate_ms_playwright_dirs():
            found = self._find_chromium_executable_under(root)
            if found:
                return found
        return None

    def _detect_windows_browser_channel(self):
        """检测系统安装的浏览器通道（避免 Playwright 缓存被清理导致无法启动）。"""
        if sys.platform != "win32":
            return None

        program_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        program_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
        local_app_data = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")

        chrome_paths = [
            os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(local_app_data, "Google", "Chrome", "Application", "chrome.exe"),
        ]
        if any(os.path.exists(p) for p in chrome_paths):
            return "chrome"

        edge_paths = [
            os.path.join(program_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(program_files, "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(local_app_data, "Microsoft", "Edge", "Application", "msedge.exe"),
        ]
        if any(os.path.exists(p) for p in edge_paths):
            return "msedge"

        return None

    def _is_missing_executable_error(self, err) -> bool:
        if not err:
            return False
        msg = str(err)
        keywords = [
            "Executable doesn't exist",
            "executable doesn't exist",
            "chromium",
            "browserType.launch",
        ]
        if "Executable doesn't exist" in msg or "executable doesn't exist" in msg:
            return True
        # 一些本地化/兼容错误文案
        if ("找不到" in msg or "不存在" in msg) and "Executable" in msg:
            return True
        # 兜底：出现 chromium 且无法找到可执行文件时也尝试修复
        return "chromium" in msg and ("not found" in msg.lower() or "不存在" in msg or "找不到" in msg)

    def _get_playwright_browsers_path(self) -> str:
        return os.environ.get(
            "PLAYWRIGHT_BROWSERS_PATH",
            os.path.join(os.path.expanduser("~"), ".xhs_system", "ms-playwright"),
        )

    async def _auto_install_playwright_chromium(self) -> bool:
        """检测到 Playwright 浏览器缺失时尝试自动安装（打包版不执行）。"""
        if getattr(sys, "frozen", False):
            return False

        browsers_path = self._get_playwright_browsers_path()
        try:
            os.makedirs(browsers_path, exist_ok=True)
        except Exception:
            pass

        env = os.environ.copy()
        env.setdefault("PLAYWRIGHT_BROWSERS_PATH", browsers_path)
        if sys.platform == "win32":
            env.setdefault("PLAYWRIGHT_DOWNLOAD_HOST", "https://npmmirror.com/mirrors/playwright")

        cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
        print("🔧 检测到浏览器缺失，尝试自动安装 Playwright Chromium（可能需要几分钟）...")

        def _run():
            return subprocess.run(cmd, capture_output=True, text=True, env=env)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        try:
            if loop:
                result = await loop.run_in_executor(None, _run)
            else:
                result = _run()
        except Exception as e:
            print(f"❌ 自动安装失败: {e}")
            return False

        if result.returncode == 0:
            print("✅ Playwright Chromium 自动安装完成")
            return True

        stderr = (result.stderr or "").strip()
        if stderr:
            print(f"❌ 自动安装失败: {stderr[:800]}")
        return False
	        
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
                # 部分机器/环境启动较慢，适当拉长超时避免“偶发启动失败”
                'timeout': 60_000,
                'args': [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-infobars',
                    '--start-maximized',
                    '--ignore-certificate-errors',
                    '--ignore-ssl-errors',
                    # '--disable-web-security',  # 会影响持久化 profile/远程调试；且可能触发站点异常
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows',
                    '--memory-pressure-off',
                    '--max_old_space_size=4096'
                ]
            }

            proxy = self._build_playwright_proxy()
            if proxy:
                launch_args["proxy"] = proxy

            executable_path = None
            channel = None

            # macOS：优先使用系统 Chrome（更稳定），否则尝试 Playwright 缓存
            if sys.platform == "darwin":
                system_chrome_paths = [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "/Applications/Chromium.app/Contents/MacOS/Chromium",
                ]
                for chrome_path in system_chrome_paths:
                    if os.path.exists(chrome_path):
                        executable_path = chrome_path
                        print(f"使用系统Chrome: {chrome_path}")
                        break

            # 优先尝试 Playwright 已下载/随包附带的 Chromium
            if not executable_path:
                executable_path = self._find_playwright_chromium_executable()
                if executable_path:
                    print(f"使用Playwright Chromium: {executable_path}")

            # Windows：如果 Playwright 缓存缺失，退回使用系统 Chrome/Edge 通道
            if sys.platform == "win32" and not executable_path:
                channel = self._detect_windows_browser_channel()
                if channel:
                    print(f"使用系统浏览器通道: {channel}")

            launch_attempts = []
            if executable_path:
                try:
                    os.chmod(executable_path, 0o755)
                except Exception:
                    pass
                args_with_path = dict(launch_args)
                args_with_path["executable_path"] = executable_path
                launch_attempts.append(args_with_path)

            if channel:
                args_with_channel = dict(launch_args)
                args_with_channel["channel"] = channel
                launch_attempts.append(args_with_channel)

            # 最后尝试 Playwright 默认路径
            launch_attempts.append(dict(launch_args))

            last_error = None

            # 使用 Playwright 持久化上下文（非系统默认目录），用于稳定登录态/缓存。
            # 注意：Chrome/DevTools 不允许 remote debugging 直接使用系统默认 user-data-dir。
            # 因此这里使用独立目录：~/.xhs_system/chrome_profile_pm （可长期复用）。
            use_persistent_profile = True
            if use_persistent_profile:
                try:
                    persistent_dir = os.path.expanduser("~/.xhs_system/chrome_profile_pm")
                    os.makedirs(persistent_dir, exist_ok=True)

                    launch_args_persistent = dict(launch_args)
                    launch_args_persistent.setdefault("args", [])

                    # 精简/移除与真实 profile/远程调试冲突或可能触发站点异常的参数
                    def _filter_args(args):
                        blocked = {
                            "--disable-web-security",
                        }
                        return [a for a in args if a not in blocked]

                    launch_args_persistent["args"] = _filter_args(launch_args_persistent["args"])

                    # 用 channel=chrome（系统 Chrome），并通过 user_data_dir 持久化
                    launch_args_persistent.pop("executable_path", None)
                    launch_args_persistent.pop("channel", None)
                    launch_args_persistent["channel"] = "chrome"

                    if proxy:
                        launch_args_persistent["proxy"] = proxy

                    print(f"使用持久化 Playwright Profile: {persistent_dir}")
                    self.context = await self.playwright.chromium.launch_persistent_context(
                        user_data_dir=persistent_dir,
                        **launch_args_persistent
                    )
                    self.browser = self.context.browser
                except Exception as e:
                    print(f"持久化 profile 启动失败，将回退到普通 launch: {e}")
                    self.context = None
                    self.browser = None

            # 回退：普通启动（非持久化）
            if not self.browser:
                for attempt in launch_attempts:
                    try:
                        self.browser = await self.playwright.chromium.launch(**attempt)
                        break
                    except Exception as e:
                        last_error = e
                        continue

            if not self.browser:
                # 自愈：Playwright 浏览器缺失时尝试自动安装再重试一次（开发/源码运行场景）
                if self._is_missing_executable_error(last_error) and await self._auto_install_playwright_chromium():
                    executable_path = self._find_playwright_chromium_executable()
                    launch_attempts_retry = []

                    if executable_path:
                        try:
                            os.chmod(executable_path, 0o755)
                        except Exception:
                            pass
                        args_with_path = dict(launch_args)
                        args_with_path["executable_path"] = executable_path
                        launch_attempts_retry.append(args_with_path)

                    if channel:
                        args_with_channel = dict(launch_args)
                        args_with_channel["channel"] = channel
                        launch_attempts_retry.append(args_with_channel)

                    launch_attempts_retry.append(dict(launch_args))

                    last_error = None
                    for attempt in launch_attempts_retry:
                        try:
                            self.browser = await self.playwright.chromium.launch(**attempt)
                            break
                        except Exception as e:
                            last_error = e

                if not self.browser:
                    raise last_error

            # 创建新的上下文（应用指纹/地理位置等）
            # 若上面已使用持久化上下文（self.context 已存在），这里就不要再 new_context。
            if not self.context:
                self.context = await self.browser.new_context(**self._build_context_options())
            
            # 复用/创建 page
            pages = self.context.pages if self.context else []
            if pages:
                self.page = pages[0]
            else:
                self.page = await self.context.new_page()
            
            # 注入stealth.min.js
            webgl_vendor = self._get_env_value("webgl_vendor") or "Intel Open Source Technology Center"
            webgl_renderer = self._get_env_value("webgl_renderer") or "Mesa DRI Intel(R) HD Graphics (SKL GT2)"
            platform = self._get_env_value("platform") or ""
            webgl_vendor_js = json.dumps(webgl_vendor, ensure_ascii=False)
            webgl_renderer_js = json.dumps(webgl_renderer, ensure_ascii=False)
            platform_js = json.dumps(platform, ensure_ascii=False)
            stealth_js = """
            (function(){
                const __xhs_webgl_vendor = %s;
                const __xhs_webgl_renderer = %s;
                const __xhs_platform = %s;

                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return __xhs_webgl_vendor;
                    }
                    if (parameter === 37446) {
                        return __xhs_webgl_renderer;
                    }
                    return getParameter.apply(this, arguments);
                };

                if (__xhs_platform) {
                    try {
                        Object.defineProperty(navigator, 'platform', { get: () => __xhs_platform });
                    } catch (e) {}
                }
                
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
            """ % (webgl_vendor_js, webgl_renderer_js, platform_js)
            await self.page.add_init_script(stealth_js)
            
            print("浏览器启动成功！")
            logging.debug("浏览器启动成功！")
            
            # 获取用户数据目录（多用户隔离 token/cookies）
            app_dir = self._get_user_storage_dir()
            os.makedirs(app_dir, exist_ok=True)

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
            # 直接导航到「发布图文」页面（避免误点到发布视频/主界面）
            publish_url = "https://creator.xiaohongshu.com/publish/publish?from=menu&target=image"
            print(f"导航到图文发布页: {publish_url}")
            await self.page.goto(publish_url, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # 检查是否需要登录
            current_url = self.page.url
            if "login" in current_url:
                print("需要重新登录...")
                raise Exception("用户未登录，请先登录")

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

                    # 关键：先点击页面中央红色「上传图片」按钮，触发前端上传流程
                    print("尝试方法0(优先): 点击页面中央『上传图片』区域并通过 file chooser 选择文件")
                    try:
                        upload_btn_selector = "button:has-text('上传图片')"
                        input_selector = ".upload-input"
                        await self.page.wait_for_selector(upload_btn_selector, state="visible", timeout=20000)
                        await self.page.wait_for_selector(input_selector, state="attached", timeout=20000)

                        # 关键：让『上传图片』按钮收到一次“真实点击”（否则某些前端状态机不启动）
                        # 由于 input 覆盖在按钮上，会拦截点击，这里临时禁用 pointer-events 再点击按钮。
                        await self.page.evaluate("""() => {
                            const input = document.querySelector('.upload-input');
                            if (input) {
                                input.dataset._pe_backup = input.style.pointerEvents || '';
                                input.style.pointerEvents = 'none';
                            }
                        }""")

                        try:
                            # 先点击按钮让前端进入“开始上传”的状态（不期待 filechooser 事件）
                            await self.page.click(upload_btn_selector, timeout=15000)
                        finally:
                            await self.page.evaluate("""() => {
                                const input = document.querySelector('.upload-input');
                                if (input) {
                                    const bk = input.dataset._pe_backup;
                                    input.style.pointerEvents = bk || '';
                                    delete input.dataset._pe_backup;
                                }
                            }""")

                        # 再点击 input 触发系统文件选择器
                        async with self.page.expect_file_chooser(timeout=20000) as fc_info:
                            await self.page.click(input_selector, timeout=15000, force=True)
                        file_chooser = await fc_info.value
                        await file_chooser.set_files(images)

                        # 补发 input/change 事件，避免 UI 不刷新
                        try:
                            await self.page.dispatch_event(input_selector, "input")
                            await self.page.dispatch_event(input_selector, "change")
                        except Exception:
                            pass
                        try:
                            files_len = await self.page.evaluate("""() => {
                                const el = document.querySelector('.upload-input');
                                return el && el.files ? el.files.length : -1;
                            }""")
                            print(f" upload-input.files.length = {files_len}")
                        except Exception:
                            pass

                        upload_success = True
                        print(" 方法0成功: 真实点击上传图片按钮 + file chooser 设置文件")
                    except Exception as e:
                        print(f" 方法0(upload-input+file chooser) 失败: {e}")
                        if self.page:
                            await self.page.screenshot(path="debug_upload_button_click_failed.png")

                    # 兜底1：直接给 input[type=file] 设置文件（有些情况下仅 set_input_files 不会触发前端状态机，但仍作为兜底）
                    if not upload_success:
                        print("尝试方法1(兜底): 直接操作 '.upload-input' 使用 set_input_files")
                        try:
                            input_selector = ".upload-input"
                            await self.page.wait_for_selector(input_selector, state="attached", timeout=15000)
                            await self.page.set_input_files(input_selector, files=images, timeout=30000)
                            # 补发事件，避免 UI 不刷新
                            try:
                                await self.page.dispatch_event(input_selector, "input")
                                await self.page.dispatch_event(input_selector, "change")
                            except Exception:
                                pass
                            try:
                                files_len = await self.page.evaluate("""() => {
                                    const el = document.querySelector('.upload-input');
                                    return el && el.files ? el.files.length : -1;
                                }""")
                                print(f" upload-input.files.length = {files_len}")
                            except Exception:
                                pass
                            print(f"已通过 set_input_files 为 '{input_selector}' 设置文件: {images}")
                            upload_success = True
                        except Exception as e:
                            print(f" 方法1(set_input_files) 失败: {e}")
                            if self.page: await self.page.screenshot(path="debug_upload_set_input_files_failed.png")

                    # 兜底2：如果上述都没成功，再尝试点击拖拽提示区域
                    if not upload_success:
                        print("尝试方法2(兜底): 点击拖拽提示区域 ( '.drag-over' )")
                        try:
                            area_selector = ".drag-over"
                            await self.page.wait_for_selector(area_selector, state="visible", timeout=8000)
                            async with self.page.expect_file_chooser(timeout=15000) as fc_info:
                                await self.page.click(area_selector, timeout=8000)
                            file_chooser = await fc_info.value
                            await file_chooser.set_files(images)
                            upload_success = True
                            print(" 方法2成功: 通过 file chooser 设置文件")
                        except Exception as e:
                            print(f" 方法2失败: {e}")
                            if self.page: await self.page.screenshot(path="debug_upload_dragover_failed.png")

                    # 上传后：会自动进入文章编辑页（发布图文/标题/正文/发布按钮出现）
                    if upload_success:
                        try:
                            await asyncio.sleep(1)
                            # 先等一次可能的路由/网络（不要用 networkidle，容易卡）
                            try:
                                await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                            except Exception:
                                pass

                            editor_markers = [
                                "text=发布图文",
                                "text=图片编辑",
                                "text=正文内容",
                                "input[placeholder='填写标题会有更多赞哦～']",
                                "textarea[placeholder*='输入正文']",
                                "button:has-text('发布')",
                            ]

                            progressed = False
                            deadline = asyncio.get_event_loop().time() + 60
                            while asyncio.get_event_loop().time() < deadline:
                                for sel in editor_markers:
                                    try:
                                        el = await self.page.query_selector(sel)
                                        if el:
                                            progressed = True
                                            print(f"检测到进入编辑页: {sel}")
                                            break
                                    except Exception:
                                        continue
                                if progressed:
                                    break
                                await asyncio.sleep(0.5)

                            if not progressed:
                                print("⚠️ 选完图片后仍未进入编辑页（60s超时），已截图")
                                if self.page:
                                    await self.page.screenshot(path="debug_after_upload_not_progressed.png")
                        except Exception as e:
                            print(f"等待进入编辑页时发生错误: {e}")
                            if self.page:
                                await self.page.screenshot(path="debug_after_upload_wait_error.png")
                    
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
            
            # 选完图片后会自动进入文章编辑页（标题/正文/发布按钮出现）
            if images:
                print("等待进入文章编辑页...")
                editor_markers = [
                    "text=发布图文",
                    "text=正文内容",
                    "input[placeholder='填写标题会有更多赞哦～']",
                    "textarea[placeholder*='输入正文']",
                    "button:has-text('发布')"
                ]
                entered = False
                for sel in editor_markers:
                    try:
                        await self.page.wait_for_selector(sel, timeout=30000)
                        print(f"检测到编辑页标志: {sel}")
                        entered = True
                        break
                    except Exception:
                        continue
                if not entered and self.page:
                    print("⚠️ 未检测到进入编辑页，已截图")
                    await self.page.screenshot(path="debug_editor_not_entered.png")

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
                    "input[placeholder='填写标题会有更多赞哦～']",
                    "input[placeholder*='标题']",
                    "input.d-text[placeholder='填写标题会有更多赞哦～']",
                    "input.d-text",
                    "input.title",
                    ".note-editor-wrapper input",
                    ".edit-wrapper input",
                    "[data-placeholder='标题']"
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
                    "textarea[placeholder='输入正文描述，真诚有价值的分享令人温暖']",
                    "textarea[placeholder*='输入正文']",
                    "[data-placeholder='添加正文']",
                    ".note-content",
                    "[role='textbox']",
                    ".DraftEditor-root",
                    "[contenteditable='true']"
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

            # 自动点击发布
            print("尝试自动点击『发布』...")
            try:
                publish_selectors = [
                    "button:has-text('发布')",
                    ".el-button:has-text('发布')",
                    "text=发布"
                ]
                clicked = False
                for sel in publish_selectors:
                    try:
                        await self.page.wait_for_selector(sel, timeout=10000)
                        await self.page.click(sel, timeout=10000)
                        print(f"已点击发布按钮: {sel}")
                        clicked = True
                        break
                    except Exception:
                        continue
                if not clicked and self.page:
                    print("⚠️ 未能自动点击发布按钮，已截图")
                    await self.page.screenshot(path="debug_publish_click_failed.png")
            except Exception as e:
                print(f"自动点击发布失败: {e}")
                if self.page:
                    await self.page.screenshot(path="debug_publish_click_error.png")

            # 等待发布结果/页面提示（失败也截图）
            try:
                await asyncio.sleep(5)
                # 常见成功提示/跳转（尽量宽松）
                await self.page.wait_for_selector("text=发布成功", timeout=8000)
                print("检测到『发布成功』提示")
            except Exception:
                pass

            print("发布流程已执行（如未成功会保留截图供排查）")
            
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
