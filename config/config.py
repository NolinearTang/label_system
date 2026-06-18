import os
from typing import Dict, Any
from dotenv import load_dotenv


class Config:
    """配置类 - 从环境变量或.env文件加载配置"""
    
    def __init__(self, env: str = None):
        """
        初始化配置
        
        Args:
            env: 环境名称 (development/test/production)，如果为None则从环境变量ENV读取
        """
        if env is None:
            env = os.getenv('ENV', 'development')
        
        self.env = env
        
        # 加载对应环境的.env文件
        env_file = os.path.join(
            os.path.dirname(__file__), 
            f'.env.{env}'
        )
        if os.path.exists(env_file):
            load_dotenv(env_file, override=True)
        
        # MySQL数据库配置
        self.MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
        self.MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3306'))
        self.MYSQL_USER = os.getenv('MYSQL_USER', 'root')
        self.MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
        self.MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', 'label_system')
        self.MYSQL_CHARSET = os.getenv('MYSQL_CHARSET', 'utf8mb4')
        
        # Redis配置
        self.REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
        self.REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
        self.REDIS_DB = int(os.getenv('REDIS_DB', '0'))
        self.REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
        self.REDIS_DECODE_RESPONSES = os.getenv('REDIS_DECODE_RESPONSES', 'true').lower() == 'true'
        
        # 定时任务配置
        self.SYNC_INTERVAL_SECONDS = int(os.getenv('SYNC_INTERVAL_SECONDS', '300'))
        
        # Embedding服务配置
        self.EMBEDDING_URL = os.getenv('EMBEDDING_URL', None)
        self.RERANK_URL = os.getenv('RERANK_URL', None)
    
    def get_mysql_config(self) -> Dict[str, Any]:
        """获取MySQL配置"""
        return {
            'host': self.MYSQL_HOST,
            'port': self.MYSQL_PORT,
            'user': self.MYSQL_USER,
            'password': self.MYSQL_PASSWORD,
            'database': self.MYSQL_DATABASE,
            'charset': self.MYSQL_CHARSET,
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """获取Redis配置"""
        config = {
            'host': self.REDIS_HOST,
            'port': self.REDIS_PORT,
            'db': self.REDIS_DB,
            'decode_responses': self.REDIS_DECODE_RESPONSES,
        }
        if self.REDIS_PASSWORD:
            config['password'] = self.REDIS_PASSWORD
        return config
    
    def get_embedding_config(self) -> Dict[str, Any]:
        """获取Embedding服务配置"""
        return {
            'embedding_url': self.EMBEDDING_URL,
            'rerank_url': self.RERANK_URL,
        }


def get_config(env: str = None) -> Config:
    """
    获取配置对象
    
    Args:
        env: 环境名称 (development/test/production)，如果为None则从环境变量ENV读取
    
    Returns:
        配置对象
    """
    return Config(env)
