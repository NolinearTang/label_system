import logging
import redis
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Redis客户端
        
        Args:
            config: Redis配置字典
        """
        self.config = config
        self.client = None
    
    def connect(self):
        """建立Redis连接"""
        try:
            self.client = redis.Redis(**self.config)
            self.client.ping()
            logger.info(f"成功连接到Redis: {self.config['host']}:{self.config['port']}")
        except Exception as e:
            logger.error(f"连接Redis失败: {str(e)}")
            raise
    
    def close(self):
        """关闭Redis连接"""
        if self.client:
            self.client.close()
            logger.info("Redis连接已关闭")
    
    def set(self, key: str, value: str):
        """
        设置键值对
        
        Args:
            key: 键
            value: 值
        """
        try:
            self.client.set(key, value)
        except Exception as e:
            logger.error(f"Redis SET失败: key={key}, 错误: {str(e)}")
            raise
    
    def hset(self, name: str, key: str, value: str):
        """
        设置Hash字段
        
        Args:
            name: Hash名称
            key: 字段名
            value: 字段值
        """
        try:
            self.client.hset(name, key, value)
        except Exception as e:
            logger.error(f"Redis HSET失败: name={name}, key={key}, 错误: {str(e)}")
            raise
    
    def hmset(self, name: str, mapping: Dict[str, str]):
        """
        批量设置Hash字段
        
        Args:
            name: Hash名称
            mapping: 字段字典
        """
        try:
            self.client.hset(name, mapping=mapping)
        except Exception as e:
            logger.error(f"Redis HMSET失败: name={name}, 错误: {str(e)}")
            raise
    
    def delete(self, *keys: str):
        """
        删除键
        
        Args:
            keys: 要删除的键
        """
        try:
            if keys:
                self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE失败: keys={keys}, 错误: {str(e)}")
            raise
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 键
            
        Returns:
            是否存在
        """
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS失败: key={key}, 错误: {str(e)}")
            raise
    
    def keys(self, pattern: str = '*'):
        """
        获取匹配模式的所有键
        
        Args:
            pattern: 匹配模式
            
        Returns:
            键列表
        """
        try:
            return self.client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis KEYS失败: pattern={pattern}, 错误: {str(e)}")
            raise
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
