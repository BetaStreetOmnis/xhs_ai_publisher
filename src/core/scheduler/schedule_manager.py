#!/usr/bin/env python3
"""
定时发布任务调度器
管理定时发布任务的创建、执行和监控
"""

import json
import os
import shutil
import time
import tempfile
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer


class ScheduleTask:
    """定时任务类"""
    
    def __init__(self, task_id: str, content: str, schedule_time: datetime, 
                 title: str = "",
                 images: List[str] = None,
                 user_id: Optional[int] = None,
                 task_type: str = "fixed",
                 interval_hours: int = 0,
                 hotspot_source: str = "",
                 hotspot_rank: int = 1,
                 use_hotspot_context: bool = True,
                 cover_template_id: str = "",
                 page_count: int = 3):
        self.task_id = task_id
        self.user_id = user_id
        self.task_type = (task_type or "fixed").strip() or "fixed"
        self.interval_hours = max(0, int(interval_hours or 0))
        self.hotspot_source = (hotspot_source or "").strip()
        self.hotspot_rank = max(1, int(hotspot_rank or 1))
        self.use_hotspot_context = bool(use_hotspot_context)
        self.cover_template_id = (cover_template_id or "").strip()
        self.page_count = max(1, int(page_count or 3))
        self.content = content
        self.title = title
        self.images = images or []
        self.schedule_time = schedule_time
        self.status = "pending"  # pending, running, completed, failed
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.retry_count = 0
        self.max_retries = 3
        self.error_message = ""
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'user_id': self.user_id,
            'task_type': self.task_type,
            'interval_hours': self.interval_hours,
            'hotspot_source': self.hotspot_source,
            'hotspot_rank': self.hotspot_rank,
            'use_hotspot_context': self.use_hotspot_context,
            'cover_template_id': self.cover_template_id,
            'page_count': self.page_count,
            'content': self.content,
            'title': self.title,
            'images': self.images,
            'schedule_time': self.schedule_time.isoformat(),
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'error_message': self.error_message,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ScheduleTask':
        """从字典创建任务"""
        task = cls(
            task_id=data['task_id'],
            content=data.get('content', ''),
            schedule_time=datetime.fromisoformat(data['schedule_time']),
            title=data.get('title', ''),
            images=data.get('images', []),
            user_id=data.get('user_id'),
            task_type=data.get('task_type', 'fixed'),
            interval_hours=data.get('interval_hours', 0),
            hotspot_source=data.get('hotspot_source', ''),
            hotspot_rank=data.get('hotspot_rank', 1),
            use_hotspot_context=data.get('use_hotspot_context', True),
            cover_template_id=data.get('cover_template_id', ''),
            page_count=data.get('page_count', 3),
        )
        task.status = data.get('status', 'pending')
        task.created_at = datetime.fromisoformat(data['created_at'])
        task.updated_at = datetime.fromisoformat(data['updated_at'])
        task.retry_count = data.get('retry_count', 0)
        task.max_retries = data.get('max_retries', 3)
        task.error_message = data.get('error_message', '') or ''
        return task


class ScheduleManager(QObject):
    """定时发布管理器"""
    
    task_started = pyqtSignal(str)  # 任务开始信号
    task_completed = pyqtSignal(str)  # 任务完成信号
    task_failed = pyqtSignal(str, str)  # 任务失败信号
    task_execute_requested = pyqtSignal(object)  # 请求外部执行任务（dict）
    
    def __init__(self):
        super().__init__()
        self.tasks: List[ScheduleTask] = []
        self.running = False
        self.check_interval = 60  # 每60秒检查一次
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_tasks)
        
        # 配置文件路径
        self.config_dir = os.getenv('XHS_DATA_DIR', '').strip() or os.path.expanduser('~/.xhs_system')
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
                recovered = False
                for task in self.tasks:
                    if task.status == "running":
                        task.status = "needs_review"
                        task.error_message = "程序在任务执行中退出，请先到小红书核验结果，不会自动重发"
                        recovered = True
                if recovered:
                    self.save_tasks()
                logging.info(f"已加载 {len(self.tasks)} 个定时任务")
        except Exception as e:
            logging.error(f"加载定时任务失败: {str(e)}")
    
    def save_tasks(self):
        """Persist before dispatch; an interrupted write must not erase tasks."""
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.config_dir,
                                             prefix='.schedule-', delete=False) as handle:
                temporary_path = handle.name
                json.dump([task.to_dict() for task in self.tasks], handle, indent=2, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.tasks_file)
        except Exception:
            if temporary_path and os.path.exists(temporary_path):
                os.unlink(temporary_path)
            raise

    def _copy_task_images(self, task_id: str, images: List[str]) -> List[str]:
        """将任务图片复制到稳定目录，避免后续生成覆盖导致定时任务引用错误图片。"""
        if not images:
            return []

        safe_images = []
        for p in images:
            if isinstance(p, str) and p and os.path.isfile(p):
                safe_images.append(p)

        if not safe_images:
            return []

        root = os.path.join(self.config_dir, "scheduled_assets", task_id)
        try:
            os.makedirs(root, exist_ok=True)
        except Exception as e:
            logging.warning(f"创建任务图片目录失败: {e}")
            return safe_images

        copied: List[str] = []
        for idx, src in enumerate(safe_images):
            try:
                ext = os.path.splitext(src)[1].lower() or ".jpg"
                if idx == 0:
                    name = f"cover{ext}"
                else:
                    name = f"content_{idx}{ext}"
                dst = os.path.join(root, name)
                shutil.copy2(src, dst)
                copied.append(dst)
            except Exception as e:
                logging.warning(f"复制任务图片失败: {src} -> {e}")
                copied.append(src)

        return copied

    def add_task(
        self,
        content: str,
        schedule_time: datetime,
        title: str = "",
        images: List[str] = None,
        user_id: Optional[int] = None,
        task_type: str = "fixed",
        interval_hours: int = 0,
        hotspot_source: str = "",
        hotspot_rank: int = 1,
        use_hotspot_context: bool = True,
        cover_template_id: str = "",
        page_count: int = 3,
    ) -> str:
        """添加定时任务"""
        task_id = f"task_{int(time.time())}_{hash(content) % 10000}"
        stable_images = self._copy_task_images(task_id, images or [])
        task = ScheduleTask(
            task_id,
            content,
            schedule_time,
            title,
            stable_images,
            user_id=user_id,
            task_type=task_type,
            interval_hours=interval_hours,
            hotspot_source=hotspot_source,
            hotspot_rank=hotspot_rank,
            use_hotspot_context=use_hotspot_context,
            cover_template_id=cover_template_id,
            page_count=page_count,
        )
        
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
                # 同步清理资源目录
                try:
                    assets_dir = os.path.join(self.config_dir, "scheduled_assets", task_id)
                    if os.path.isdir(assets_dir):
                        shutil.rmtree(assets_dir, ignore_errors=True)
                except Exception:
                    pass
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
        self.save_tasks()

        # 交给外部执行器（例如：BrowserThread + Playwright）
        try:
            self.task_execute_requested.emit(task.to_dict())
        except Exception as e:
            self.handle_task_failure(task, str(e))

    @pyqtSlot(str, bool, str)
    def handle_task_result(self, task_id: str, success: bool, error_msg: str = ""):
        """由外部执行器回调任务结果（通过 Qt 信号连接此方法，跨线程安全）。"""
        task = None
        for t in self.tasks:
            if t.task_id == task_id:
                task = t
                break

        if not task:
            logging.warning(f"收到未知任务结果回调: {task_id}")
            return

        task.updated_at = datetime.now()
        task.error_message = (error_msg or "").strip()

        if success:
            # A browser acknowledgement is not moderation approval. Do not roll
            # hotspot tasks into another unattended publication automatically.
            task.status = error_msg if error_msg in {"submitted", "under_review"} else "needs_review"
            task.error_message = "已执行，请到小红书核验提交及审核结果"
            self.task_completed.emit(task.task_id)
        else:
            task.status = "needs_review"
            task.retry_count += 1
            task.error_message = task.error_message or "执行结果不明，请人工核验"
            self.stop_scheduler()
            for other in self.tasks:
                if other is not task and other.status in {"pending", "running"}:
                    other.status = "needs_review"
                    other.error_message = "其他任务出现异常，后续定时任务已暂停，请核验账号和平台记录"
            self.task_failed.emit(task.task_id, task.error_message)
        self.save_tasks()

    def handle_task_failure(self, task: ScheduleTask, error_msg: str):
        """处理任务失败"""
        logging.error(f"任务 {task.task_id} 失败: {error_msg}")
        try:
            self.handle_task_result(task.task_id, False, error_msg)
        except Exception:
            # 可以在这里添加失败通知机制
            pass
    
    def clear_completed_tasks(self):
        """清理已完成的任务"""
        completed_ids = [t.task_id for t in self.tasks if t.status == "completed"]
        self.tasks = [task for task in self.tasks if task.status != "completed"]
        self.save_tasks()
        for task_id in completed_ids:
            try:
                assets_dir = os.path.join(self.config_dir, "scheduled_assets", task_id)
                if os.path.isdir(assets_dir):
                    shutil.rmtree(assets_dir, ignore_errors=True)
            except Exception:
                pass
        logging.info("已清理已完成的任务")
    
    def get_task_stats(self) -> Dict:
        """获取任务统计"""
        stats = {
            'total': len(self.tasks),
            'pending': len([t for t in self.tasks if t.status == "pending"]),
            'running': len([t for t in self.tasks if t.status == "running"]),
            'completed': len([t for t in self.tasks if t.status == "completed"]),
            'failed': len([t for t in self.tasks if t.status == "failed"]),
            'needs_review': len([t for t in self.tasks if t.status == "needs_review"]),
            'submitted': len([t for t in self.tasks if t.status == "submitted"]),
            'under_review': len([t for t in self.tasks if t.status == "under_review"])
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
