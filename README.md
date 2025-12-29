# 标签体系管理系统

标签体系管理系统，支持实体标签和意图标签的管理，并提供定时任务将数据同步到Redis。

## 项目结构

```
label_system/
├── config/                  # 配置模块
│   ├── __init__.py
│   ├── config.py           # 配置类
│   ├── .env.example        # 配置模板
│   └── README.md
├── db/                     # 数据库模块
│   ├── __init__.py
│   └── mysql_client.py     # MySQL客户端
├── cache/                  # 缓存模块
│   ├── __init__.py
│   └── redis_client.py     # Redis客户端
├── scheduler/              # 定时任务模块
│   ├── __init__.py
│   ├── scheduler.py        # 调度器
│   ├── tasks/              # 任务实现
│   │   ├── __init__.py
│   │   └── sync_to_redis.py  # Redis同步任务
│   └── README.md
├── logs/                   # 日志目录
├── data_define.sql         # 数据库表结构
├── requirements.txt        # 依赖包
├── run_scheduler.py        # 启动脚本
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

复制配置模板并修改：

```bash
cp config/.env.example config/.env.development
```

编辑 `config/.env.development`，填入实际的数据库和Redis连接信息。

### 3. 初始化数据库

执行 `data_define.sql` 创建数据库表结构：

```bash
mysql -u root -p < data_define.sql
```

### 4. 创建日志目录

```bash
mkdir -p logs
```

### 5. 运行定时任务

```bash
# 使用默认环境（development）
python run_scheduler.py

# 或指定环境
ENV=production python run_scheduler.py
```

## 功能说明

### 数据同步任务

定时任务会将数据库中的实体信息同步到Redis，数据格式如下：

**Redis Key格式**: `item_name2label:{system_code}`

**数据结构**: Hash

**内容**:
- Key: 实体名称（item_name）或同义词（synonym）
- Value: 标签编码（label_code）

**示例**:
```
item_name2label:product_system
  "伺服" -> "servo"
  "SV660系列" -> "sv660"
  "伺服电机" -> "servo"  (同义词)
```

### 数据库表说明

1. **tag_systems**: 标签体系表（实体体系、意图体系）
2. **labels**: 标签定义表（树状层级结构）
3. **items**: 实体数据表（实体类标签下的具体实体）
4. **item_synonyms**: 实体同义词表
5. **intent_rules**: 意图规则表（意图类标签下的规则）

## 配置说明

详见 `config/README.md`

## 开发说明

### 添加新的定时任务

1. 在 `scheduler/tasks/` 下创建新的任务类
2. 实现 `execute()` 方法
3. 在 `run_scheduler.py` 中注册任务

示例：

```python
# scheduler/tasks/my_task.py
class MyTask:
    def __init__(self, **kwargs):
        pass
    
    def execute(self):
        # 实现任务逻辑
        pass

# run_scheduler.py
from scheduler.tasks.my_task import MyTask

my_task = MyTask()
scheduler.add_job(
    job_id='my_task',
    func=my_task.execute,
    interval_seconds=60,
    description='我的任务'
)
```

## 日志

日志会同时输出到：
- 控制台（标准输出）
- 文件：`logs/scheduler.log`

日志级别：INFO

## 注意事项

1. 确保MySQL和Redis服务正常运行
2. 首次运行会立即执行一次同步
3. 按 `Ctrl+C` 可以优雅地关闭程序
4. 生产环境建议使用进程管理工具（如 systemd、supervisor）
