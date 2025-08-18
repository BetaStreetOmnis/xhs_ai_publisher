import schedule
import threading
import time

class ScheduleTaskManager:
    """定时任务管理器"""
    
    def __init__(self, main_window):
        """初始化定时任务管理器
        :param main_window: 主窗口实例
        """
        self.schedule_thread = None
        self.running = True
        self.init_tasks()
        
    def init_tasks(self):
        """初始化定时任务"""
        # 设置每天固定时间清理日志
        # schedule.every().day.at("09:00").do(self.main_window.clear_log)
        # schedule.every().day.at("12:00").do(self.main_window.clear_log)
        # schedule.every().day.at("17:00").do(self.main_window.clear_log)
        
        # 启动定时任务线程
        self.start_schedule_thread()
        
    def run_schedule(self):
        """运行定时任务"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)
            
    def start_schedule_thread(self):
        """启动定时任务线程"""
        self.running = True
        self.schedule_thread = threading.Thread(
            target=self.run_schedule, 
            daemon=True
        )
        self.schedule_thread.start()
        
    def stop(self):
        """停止定时任务"""
        self.running = False
        if self.schedule_thread:
            self.schedule_thread.join()
            self.schedule_thread = None
