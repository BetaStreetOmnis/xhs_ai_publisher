import logging
import os
from datetime import datetime
from typing import Optional

class Logger:
    """统一的日志管理器"""
    
    def __init__(self, name: str = "xiaohongshu", log_dir: str = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers(log_dir)
    
    def _setup_handlers(self, log_dir: Optional[str]):
        """设置日志处理器"""
        if log_dir is None:
            log_dir = os.path.expanduser('~/Desktop')
        
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 文件处理器
        log_file = os.path.join(log_dir, f"xhs_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def debug(self, message: str, **kwargs):
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, exc_info=None, **kwargs):
        self.logger.error(message, exc_info=exc_info, extra=kwargs)
    
    def critical(self, message: str, exc_info=None, **kwargs):
        self.logger.critical(message, exc_info=exc_info, extra=kwargs)

# 全局日志实例
logger = Logger() 