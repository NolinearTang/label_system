import logging
import time
import signal
import sys
from config import get_config
from db import MySQLClient
from cache import RedisClient
from scheduler import LabelSystemScheduler
from scheduler.tasks import SyncToRedisTask


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/scheduler.log', encoding='utf-8')
        ]
    )


def signal_handler(signum, frame):
    """信号处理器"""
    logger = logging.getLogger(__name__)
    logger.info(f"收到信号 {signum}，准备关闭...")
    sys.exit(0)


def main():
    """主函数"""
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 60)
    logger.info("标签系统定时任务调度器启动")
    logger.info("=" * 60)
    
    try:
        # 加载配置
        config = get_config()
        logger.info(f"当前环境: {config.env}")
        logger.info(f"同步间隔: {config.SYNC_INTERVAL_SECONDS} 秒")
        
        # 初始化数据库客户端
        mysql_config = config.get_mysql_config()
        db_client = MySQLClient(mysql_config)
        db_client.connect()
        logger.info("数据库客户端初始化完成")
        
        # 初始化Redis客户端
        redis_config = config.get_redis_config()
        redis_client = RedisClient(redis_config)
        redis_client.connect()
        logger.info("Redis客户端初始化完成")
        
        # 创建同步任务
        sync_task = SyncToRedisTask(db_client, redis_client)
        
        # 创建调度器
        scheduler = LabelSystemScheduler()
        
        # 添加定时任务
        scheduler.add_job(
            job_id='sync_items_to_redis',
            func=sync_task.execute,
            interval_seconds=config.SYNC_INTERVAL_SECONDS,
            description='实体信息同步到Redis'
        )
        
        # 立即执行一次同步
        logger.info("执行首次同步...")
        sync_task.execute()
        
        # 启动调度器
        scheduler.start()
        logger.info("调度器已启动，按 Ctrl+C 退出")
        
        # 保持运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
    except Exception as e:
        logger.error(f"程序异常: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        # 清理资源
        if 'scheduler' in locals():
            scheduler.shutdown()
        if 'db_client' in locals():
            db_client.close()
        if 'redis_client' in locals():
            redis_client.close()
        logger.info("程序已退出")


if __name__ == '__main__':
    main()
