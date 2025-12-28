# 定时任务模块

## 目录结构

```
scheduler/
├── __init__.py           # 模块初始化
├── scheduler.py          # 调度器核心类
├── tasks/                # 任务实现目录
│   ├── __init__.py
│   └── sync_to_redis.py  # Redis同步任务
└── README.md             # 说明文档
```

## 使用方式

### 1. 基本使用

```python
from scheduler import LabelSystemScheduler
from scheduler.tasks import SyncToRedisTask
from config import get_config

# 获取配置
config = get_config('development')

# 初始化数据库和Redis客户端
# db_client = ...
# redis_client = ...

# 创建调度器
scheduler = LabelSystemScheduler()

# 创建同步任务
sync_task = SyncToRedisTask(db_client, redis_client)

# 添加定时任务
scheduler.add_job(
    job_id='sync_to_redis',
    func=sync_task.execute,
    interval_seconds=config.SYNC_INTERVAL_SECONDS,
    description='数据库到Redis同步任务'
)

# 启动调度器
scheduler.start()

# 保持运行
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    scheduler.shutdown()
```

### 2. 添加自定义任务

在 `tasks/` 目录下创建新的任务类：

```python
# tasks/my_task.py
import logging

logger = logging.getLogger(__name__)

class MyTask:
    def __init__(self, **kwargs):
        # 初始化任务所需的资源
        pass
    
    def execute(self):
        """执行任务逻辑"""
        try:
            logger.info("开始执行自定义任务...")
            # 实现具体逻辑
            logger.info("自定义任务执行完成")
        except Exception as e:
            logger.error(f"任务执行失败: {str(e)}", exc_info=True)
            raise
```

然后在调度器中注册：

```python
from scheduler.tasks.my_task import MyTask

my_task = MyTask()
scheduler.add_job(
    job_id='my_task',
    func=my_task.execute,
    interval_seconds=60,
    description='我的自定义任务'
)
```

## 依赖安装

```bash
pip install apscheduler
```

## 注意事项

1. 所有任务的 `execute` 方法应该处理异常，避免影响调度器运行
2. 长时间运行的任务应该考虑超时控制
3. 任务执行间隔应该大于任务执行时间，避免任务堆积
4. 生产环境建议配置日志记录任务执行情况
