#!/usr/bin/env python3
"""
定时发布任务调度器
管理定时发布任务的创建、执行和监控
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class ScheduleTask:
    """定时任务类"""
    
    def __init__(self, task_id: str, content: str, schedule_time: datetime, 
                 title: str = "", images: List[str] = None):
        self.task_id = task_id
        self.content = content
        self.title = title
        self.images = images or []
        self.schedule_time = schedule_time
        self.status = "pending"  # pending, running, completed, failed
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.retry_count = 0
        self.max_retries = 3
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'content': self.content,
            'title': self.title,
            'images': self.images,
            'schedule_time': self.schedule_time.isoformat(),
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ScheduleTask':
        """从字典创建任务"""
        task = cls(
            task_id=data['task_id'],
            content=data['content'],
            schedule_time=datetime.fromisoformat(data['schedule_time']),
            title=data.get('title', ''),
            images=data.get('images', [])
        )
        task.status = data.get('status', 'pending')
        task.created_at = datetime.fromisoformat(data['created_at'])
        task.updated_at = datetime.fromisoformat(data['updated_at'])
        task.retry_count = data.get('retry_count', 0)
        task.max_retries = data.get('max_retries', 3)
        return task


class ScheduleManager(QObject):
    """定时发布管理器"""
    
    task_started = pyqtSignal(str)  # 任务开始信号
    task_completed = pyqtSignal(str)  # 任务完成信号
    task_failed = pyqtSignal(str, str)  # 任务失败信号
    
    def __init__(self):
        super().__init__()
        self.tasks: List[ScheduleTask] = []
        self.running = False
        self.check_interval = 60  # 每60秒检查一次
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_tasks)
        
        # 配置文件路径
        self.config_dir = os.path.expanduser('~/.xhs_system')
        self.tasks_file = os.path.join(self.config_dir, 'schedule_tasks.json')
        
        # 确保目录存在
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        
        self.load_tasks()
        self.start_scheduler()
    
    def load_tasks(self):
        """加载定时任务"""
        try:
            if os.path.exists(self.tasks_file):
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tasks = [ScheduleTask.from_dict(task_data) for task_data in data]
                logging.info(f"已加载 {len(self.tasks)} 个定时任务")
        except Exception as e:
            logging.error(f"加载定时任务失败: {str(e)}")
    
    def save_tasks(self):
        """保存定时任务"""
        try:
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump([task.to_dict() for task in self.tasks], 
                         f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"保存定时任务失败: {str(e)}")
    
    def add_task(self, content: str, schedule_time: datetime, 
                title: str = "", images: List[str] = None) -> str:
        """添加定时任务"""
        task_id = f"task_{int(time.time())}_{hash(content) % 10000}"
        task = ScheduleTask(task_id, content, schedule_time, title, images)
        
        self.tasks.append(task)
        self.save_tasks()
        
        logging.info(f"添加定时任务: {task_id} - {schedule_time}")
        return task_id
    
    def remove_task(self, task_id: str) -> bool:
        """移除定时任务"""
        for i, task in enumerate(self.tasks):
            if task.task_id == task_id:
                del self.tasks[i]
                self.save_tasks()
                logging.info(f"移除定时任务: {task_id}")
                return True
        return False
    
    def get_tasks(self) -> List[ScheduleTask]:
        """获取所有任务"""
        return self.tasks.copy()
    
    def get_pending_tasks(self) -> List[ScheduleTask]:
        """获取待执行的任务"""
        now = datetime.now()
        return [task for task in self.tasks 
                if task.status == "pending" and task.schedule_time <= now]
    
    def get_upcoming_tasks(self) -> List[ScheduleTask]:
        """获取即将执行的任务"""
        now = datetime.now()
        next_hour = now + timedelta(hours=1)
        return [task for task in self.tasks 
                if task.status == "pending" and 
                now <= task.schedule_time <= next_hour]
    
    def start_scheduler(self):
        """启动调度器"""
        if not self.running:
            self.running = True
            self.timer.start(self.check_interval * 1000)  # 转换为毫秒
            logging.info("定时发布调度器已启动")
    
    def stop_scheduler(self):
        """停止调度器"""
        self.running = False
        self.timer.stop()
        logging.info("定时发布调度器已停止")
    
    def check_tasks(self):
        """检查并执行到期任务"""
        if not self.running:
            return
        
        now = datetime.now()
        pending_tasks = self.get_pending_tasks()
        
        for task in pending_tasks:
            try:
                self.execute_task(task)
            except Exception as e:
                logging.error(f"执行任务 {task.task_id} 失败: {str(e)}")
                self.handle_task_failure(task, str(e))
    
    def execute_task(self, task: ScheduleTask):
        """执行单个任务"""
        logging.info(f"开始执行任务: {task.task_id}")
        task.status = "running"
        task.updated_at = datetime.now()
        
        self.task_started.emit(task.task_id)
        
        # 这里可以集成实际的小红书发布逻辑
        # 暂时使用模拟执行
        success = self.publish_to_xiaohongshu(task)
        
        if success:
            task.status = "completed"
            self.task_completed.emit(task.task_id)
            logging.info(f"任务执行成功: {task.task_id}")
        else:
            task.status = "failed"
            task.retry_count += 1
            
            if task.retry_count < task.max_retries:
                # 延迟重试，10分钟后重试
                task.schedule_time = datetime.now() + timedelta(minutes=10)
                task.status = "pending"
                logging.warning(f"任务执行失败，准备重试: {task.task_id}")
            else:
                self.task_failed.emit(task.task_id, "达到最大重试次数")
                logging.error(f"任务执行失败: {task.task_id}")
        
        task.updated_at = datetime.now()
        self.save_tasks()
    
    def publish_to_xiaohongshu(self, task: ScheduleTask) -> bool:
        """发布到小红书（模拟实现）"""
        # 这里集成实际的小红书发布API
        # 返回True表示成功，False表示失败
        
        try:
            # 模拟发布过程
            time.sleep(2)  # 模拟网络请求时间
            
            # 实际实现时需要：
            # 1. 调用小红书API登录
            # 2. 上传图片（如果有）
            # 3. 发布内容
            
            logging.info(f"模拟发布成功: {task.title}")
            return True
            
        except Exception as e:
            logging.error(f"发布失败: {str(e)}")
            return False
    
    def handle_task_failure(self, task: ScheduleTask, error_msg: str):
        """处理任务失败"""
        logging.error(f"任务 {task.task_id} 失败: {error_msg}")
        # 可以在这里添加失败通知机制
    
    def clear_completed_tasks(self):
        """清理已完成的任务"""
        self.tasks = [task for task in self.tasks if task.status != "completed"]
        self.save_tasks()
        logging.info("已清理已完成的任务")
    
    def get_task_stats(self) -> Dict:
        """获取任务统计"""
        stats = {
            'total': len(self.tasks),
            'pending': len([t for t in self.tasks if t.status == "pending"]),
            'running': len([t for t in self.tasks if t.status == "running"]),
            'completed': len([t for t in self.tasks if t.status == "completed"]),
            'failed': len([t for t in self.tasks if t.status == "failed"])
        }
        return stats
    
    def export_tasks(self, file_path: str):
        """导出任务到文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump([task.to_dict() for task in self.tasks], 
                         f, indent=2, ensure_ascii=False)
            logging.info(f"任务已导出到: {file_path}")
        except Exception as e:
            logging.error(f"导出任务失败: {str(e)}")
    
    def import_tasks(self, file_path: str):
        """从文件导入任务"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                new_tasks = [ScheduleTask.from_dict(task_data) for task_data in data]
                self.tasks.extend(new_tasks)
                self.save_tasks()
            logging.info(f"已从 {file_path} 导入 {len(new_tasks)} 个任务")
        except Exception as e:
            logging.error(f"导入任务失败: {str(e)}")


# 全局调度器实例
schedule_manager = ScheduleManager()