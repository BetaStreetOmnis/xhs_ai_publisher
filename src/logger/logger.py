import logging
import os
from colorama import Fore, Style


class Logger:
    def __init__(self, log_dir='logs', is_console='debug'):
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
        console_handler.setFormatter(formatter)

        # 添加处理器
        self.logger.addHandler(file_handler)
        if is_console == "debug":
            self.logger.addHandler(console_handler)

    def success(self, message):
        """记录成功信息 - 绿色"""
        colored_message = f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}"
        self.logger.info(colored_message)

    def warning(self, message):
        """记录警告信息 - 黄色"""
        colored_message = f"{Fore.YELLOW}⚠️ {message}{Style.RESET_ALL}"
        self.logger.warning(colored_message)

    def error(self, message):
        """记录错误信息 - 红色"""
        colored_message = f"{Fore.RED}❌ {message}{Style.RESET_ALL}"
        self.logger.error(colored_message)

    def info(self, message):
        """记录一般信息 - 蓝色"""
        colored_message = f"{Fore.BLUE}ℹ️ {message}{Style.RESET_ALL}"
        self.logger.info(colored_message)
