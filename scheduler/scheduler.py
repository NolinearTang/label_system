import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class LabelSystemScheduler:
    """标签系统定时任务调度器"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._jobs = {}
    
    def add_job(
        self,
        job_id: str,
        func: Callable,
        interval_seconds: int,
        description: str = ""
    ):
        """
        添加定时任务
        
        Args:
            job_id: 任务唯一标识
            func: 要执行的函数
            interval_seconds: 执行间隔（秒）
            description: 任务描述
        """
        if job_id in self._jobs:
            logger.warning(f"任务 {job_id} 已存在，将被覆盖")
            self.remove_job(job_id)
        
        job = self.scheduler.add_job(
            func=func,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id=job_id,
            name=description or job_id,
            replace_existing=True
        )
        
        self._jobs[job_id] = {
            'job': job,
            'description': description,
            'interval': interval_seconds
        }
        
        logger.info(f"已添加定时任务: {job_id} ({description}), 间隔: {interval_seconds}秒")
    
    def remove_job(self, job_id: str):
        """移除定时任务"""
        if job_id in self._jobs:
            self.scheduler.remove_job(job_id)
            del self._jobs[job_id]
            logger.info(f"已移除定时任务: {job_id}")
    
    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("定时任务调度器已启动")
    
    def shutdown(self, wait: bool = True):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("定时任务调度器已关闭")
    
    def get_jobs(self):
        """获取所有任务信息"""
        return self._jobs
    
    def is_running(self) -> bool:
        """检查调度器是否运行中"""
        return self.scheduler.running
