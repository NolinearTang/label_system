import logging
import pymysql
from typing import List, Dict, Any, Optional
from pymysql.cursors import DictCursor

logger = logging.getLogger(__name__)


class MySQLClient:
    """MySQL数据库客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化MySQL客户端
        
        Args:
            config: 数据库配置字典
        """
        self.config = config
        self.connection = None
    
    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset=self.config['charset'],
                cursorclass=DictCursor
            )
            logger.info(f"成功连接到MySQL数据库: {self.config['host']}:{self.config['port']}/{self.config['database']}")
        except Exception as e:
            logger.error(f"连接MySQL数据库失败: {str(e)}")
            raise
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("MySQL数据库连接已关闭")
    
    def execute_query(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """
        执行查询SQL
        
        Args:
            sql: SQL语句
            params: 参数元组
            
        Returns:
            查询结果列表
        """
        if not self.connection:
            self.connect()
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchall()
                return result
        except Exception as e:
            logger.error(f"执行查询失败: {sql}, 错误: {str(e)}")
            raise
    
    def get_all_tag_systems(self) -> List[Dict[str, Any]]:
        """
        获取所有标签体系
        
        Returns:
            标签体系列表
        """
        sql = "SELECT * FROM tag_systems"
        return self.execute_query(sql)
    
    def get_labels_by_system(self, system_code: str) -> List[Dict[str, Any]]:
        """
        根据体系编码获取所有标签
        
        Args:
            system_code: 体系编码
            
        Returns:
            标签列表
        """
        sql = "SELECT * FROM labels WHERE system_code = %s"
        return self.execute_query(sql, (system_code,))
    
    def get_items_by_label(self, label_code: str) -> List[Dict[str, Any]]:
        """
        根据标签编码获取所有实体
        
        Args:
            label_code: 标签编码
            
        Returns:
            实体列表
        """
        sql = "SELECT * FROM items WHERE label_code = %s AND is_active = TRUE"
        return self.execute_query(sql, (label_code,))
    
    def get_items_by_system(self, system_code: str) -> List[Dict[str, Any]]:
        """
        根据体系编码获取所有实体（通过关联标签）
        
        Args:
            system_code: 体系编码
            
        Returns:
            实体列表（包含label_code）
        """
        sql = """
            SELECT i.*, l.system_code
            FROM items i
            JOIN labels l ON i.label_code = l.label_code
            WHERE l.system_code = %s AND i.is_active = TRUE
        """
        return self.execute_query(sql, (system_code,))
    
    def get_synonyms_by_item(self, item_code: str) -> List[Dict[str, Any]]:
        """
        根据实体编码获取所有同义词
        
        Args:
            item_code: 实体编码
            
        Returns:
            同义词列表
        """
        sql = "SELECT * FROM item_synonyms WHERE item_code = %s"
        return self.execute_query(sql, (item_code,))
    
    def get_all_synonyms(self) -> List[Dict[str, Any]]:
        """
        获取所有同义词
        
        Returns:
            同义词列表
        """
        sql = "SELECT * FROM item_synonyms"
        return self.execute_query(sql)
    
    def get_label_by_code(self, label_code: str) -> Optional[Dict[str, Any]]:
        """
        根据标签编码获取标签信息
        
        Args:
            label_code: 标签编码
            
        Returns:
            标签信息，如果不存在返回None
        """
        sql = "SELECT * FROM labels WHERE label_code = %s"
        result = self.execute_query(sql, (label_code,))
        return result[0] if result else None
    
    def build_label_tree_path(self, label_code: str) -> Dict[str, str]:
        """
        构建标签的层级树路径
        
        Args:
            label_code: 标签编码
            
        Returns:
            层级树字典 {"level1": "标签名1", "level2": "标签名2", ...}
        """
        tree_path = {}
        current_label = self.get_label_by_code(label_code)
        
        if not current_label:
            return tree_path
        
        # 从当前标签向上追溯到根节点
        path_list = []
        while current_label:
            path_list.append({
                'level': current_label['level'],
                'label_name': current_label['label_name']
            })
            
            # 获取父标签
            parent_code = current_label.get('parent_label_code')
            if parent_code:
                current_label = self.get_label_by_code(parent_code)
            else:
                current_label = None
        
        # 反转列表，从根节点到当前节点
        path_list.reverse()
        
        # 构建层级字典（标准化处理）
        for item in path_list:
            level_key = f"level{item['level']}"
            tree_path[level_key] = item['label_name'].lower().strip()
        
        return tree_path
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
