# 配置文件说明

## 快速开始

1. **复制配置模板**
   ```bash
   cp config/.env.example config/.env.development
   cp config/.env.example config/.env.production
   ```

2. **修改配置文件**
   
   编辑对应环境的配置文件，填入实际的数据库和Redis连接信息

3. **在代码中使用**
   ```python
   from config import get_config
   
   # 方式1: 通过环境变量ENV指定环境
   config = get_config()  # 读取环境变量ENV，默认为development
   
   # 方式2: 直接指定环境
   config = get_config('production')
   
   # 获取MySQL配置
   mysql_config = config.get_mysql_config()
   
   # 获取Redis配置
   redis_config = config.get_redis_config()
   ```

## 配置文件

- **config.py**: 配置类定义，自动加载对应环境的 `.env` 文件
- **.env.example**: 配置模板文件
- **.env.development**: 开发环境配置（需手动创建）
- **.env.test**: 测试环境配置（需手动创建）
- **.env.production**: 生产环境配置（需手动创建）

## 环境切换

### 方式1: 设置环境变量

```bash
# Linux/Mac
export ENV=production
python your_script.py

# Windows
set ENV=production
python your_script.py
```

### 方式2: 代码中指定

```python
config = get_config('production')
```

## 配置项说明

### MySQL配置
- `MYSQL_HOST`: 数据库主机地址
- `MYSQL_PORT`: 数据库端口
- `MYSQL_USER`: 数据库用户名
- `MYSQL_PASSWORD`: 数据库密码
- `MYSQL_DATABASE`: 数据库名称
- `MYSQL_CHARSET`: 字符集

### Redis配置
- `REDIS_HOST`: Redis主机地址
- `REDIS_PORT`: Redis端口
- `REDIS_DB`: Redis数据库编号
- `REDIS_PASSWORD`: Redis密码（可选，留空表示无密码）
- `REDIS_DECODE_RESPONSES`: 是否自动解码响应（true/false）

### 定时任务配置
- `SYNC_INTERVAL_SECONDS`: 同步间隔时间（秒）

## 安全建议

1. **不要将 `.env.*` 文件提交到Git仓库**（已在 `.gitignore` 中配置）
2. 生产环境的密码请使用强密码
3. 定期更换数据库和Redis密码
4. 使用环境变量或密钥管理服务存储敏感信息

## 依赖安装

配置模块需要 `python-dotenv` 库：

```bash
pip install python-dotenv
```
