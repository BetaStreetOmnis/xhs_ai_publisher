import logging
import os
import sys

from colorama import Fore, Style, just_fix_windows_console


class _ColoredFormatter(logging.Formatter):
    def __init__(self, fmt: str, datefmt: str, enable_color: bool):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.enable_color = bool(enable_color)

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        if not self.enable_color:
            return msg

        color = getattr(record, "xhs_color", "")
        if color == "green":
            prefix = Fore.GREEN
        elif color == "yellow":
            prefix = Fore.YELLOW
        elif color == "red":
            prefix = Fore.RED
        elif color == "blue":
            prefix = Fore.BLUE
        else:
            prefix = ""

        if not prefix:
            return msg

        return f"{prefix}{msg}{Style.RESET_ALL}"


class Logger:
    def __init__(self, log_dir='logs', is_console='debug'):
        try:
            just_fix_windows_console()
        except Exception:
            pass

        enable_color = False
        if is_console == "debug":
            try:
                enable_color = bool(getattr(sys.stderr, "isatty", lambda: False)()) and not os.environ.get("NO_COLOR")
            except Exception:
                enable_color = False

        # 设置日志文件路径
        home_dir = os.path.expanduser('~')
        app_log_dir = os.path.join(home_dir, '.xhs_system', 'logs')
        if not os.path.exists(app_log_dir):
            os.makedirs(app_log_dir)

        self.log_file = os.path.join(app_log_dir, 'xhs.log')

        # 创建日志目录
        if not os.path.exists(app_log_dir):
            os.makedirs(app_log_dir)

        # 创建logger实例
        self.logger = logging.getLogger('app')
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

        # 避免重复添加处理器（多次初始化会导致重复输出）
        if self.logger.handlers:
            return

        # 创建文件处理器
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(_ColoredFormatter(formatter._fmt, formatter.datefmt, enable_color))

        # 添加处理器
        self.logger.addHandler(file_handler)
        if is_console == "debug":
            self.logger.addHandler(console_handler)

    def success(self, message):
        """记录成功信息 - 绿色（仅控制台着色）"""
        self.logger.info(f"✅ {message}", extra={"xhs_color": "green"})

    def warning(self, message):
        """记录警告信息 - 黄色（仅控制台着色）"""
        self.logger.warning(f"⚠️ {message}", extra={"xhs_color": "yellow"})

    def error(self, message):
        """记录错误信息 - 红色（仅控制台着色）"""
        self.logger.error(f"❌ {message}", extra={"xhs_color": "red"})

    def info(self, message):
        """记录一般信息 - 蓝色（仅控制台着色）"""
        self.logger.info(f"ℹ️ {message}", extra={"xhs_color": "blue"})
