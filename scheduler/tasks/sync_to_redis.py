import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class SyncToRedisTask:
    """数据库到Redis同步任务"""
    
    def __init__(self, db_client, redis_client):
        """
        初始化同步任务
        
        Args:
            db_client: 数据库客户端
            redis_client: Redis客户端
        """
        self.db = db_client
        self.redis = redis_client
    
    def execute(self):
        """执行同步任务"""
        try:
            logger.info("开始执行数据同步任务...")
            
            # 同步实体信息到Redis
            self.sync_items_to_redis()
            
            # 同步标签层级树到Redis
            self.sync_label_tree_to_redis()
            
            logger.info("数据同步任务执行完成")
        except Exception as e:
            logger.error(f"数据同步任务执行失败: {str(e)}", exc_info=True)
            raise
    
    def sync_items_to_redis(self):
        """
        同步实体信息到Redis
        格式: item_name2label:{system_code} -> Hash {item_name: label_code}
        """
        logger.info("开始同步实体信息到Redis...")
        
        # 1. 获取所有标签体系
        tag_systems = self.db.get_all_tag_systems()
        logger.info(f"获取到 {len(tag_systems)} 个标签体系")
        
        for system in tag_systems:
            system_code = system['system_code']
            system_name = system['system_name']
            
            logger.info(f"处理标签体系: {system_name} ({system_code})")
            
            # 2. 获取该体系下的所有实体
            items = self.db.get_items_by_system(system_code)
            logger.info(f"  获取到 {len(items)} 个实体")
            
            # 3. 构建 item_name -> label_code 映射
            item_name_to_label = {}
            
            for item in items:
                item_name = item['item_name']
                item_code = item['item_code']
                label_code = item['label_code']
                
                # 实体名称映射到标签编码（标准化处理）
                normalized_item_name = item_name.lower().strip()
                item_name_to_label[normalized_item_name] = label_code
                
                # 4. 获取该实体的所有同义词
                synonyms = self.db.get_synonyms_by_item(item_code)
                
                # 同义词也映射到相同的标签编码（标准化处理）
                for synonym in synonyms:
                    synonym_name = synonym['synonym']
                    normalized_synonym = synonym_name.lower().strip()
                    item_name_to_label[normalized_synonym] = label_code
            
            logger.info(f"  构建了 {len(item_name_to_label)} 个映射（包含同义词）")
            
            # 5. 写入Redis
            redis_key = f"item_name2label:{system_code}"
            
            if item_name_to_label:
                # 先删除旧数据
                self.redis.delete(redis_key)
                
                # 批量写入新数据
                self.redis.hmset(redis_key, item_name_to_label)
                logger.info(f"  已写入Redis: {redis_key}, 共 {len(item_name_to_label)} 条记录")
            else:
                logger.warning(f"  标签体系 {system_code} 下没有实体数据")
        
        logger.info("实体信息同步完成")
    
    def sync_label_tree_to_redis(self):
        """
        同步标签层级树到Redis
        格式: label_code2label_tree:{system_code} -> Hash {label_code: JSON字符串}
        JSON内容: {"level1": "标签名1", "level2": "标签名2", ...}
        """
        import json
        
        logger.info("开始同步标签层级树到Redis...")
        
        # 1. 获取所有标签体系
        tag_systems = self.db.get_all_tag_systems()
        logger.info(f"获取到 {len(tag_systems)} 个标签体系")
        
        for system in tag_systems:
            system_code = system['system_code']
            system_name = system['system_name']
            
            logger.info(f"处理标签体系: {system_name} ({system_code})")
            
            # 2. 获取该体系下的所有标签
            labels = self.db.get_labels_by_system(system_code)
            logger.info(f"  获取到 {len(labels)} 个标签")
            
            # 3. 构建 label_code -> label_tree 映射
            label_code_to_tree = {}
            
            for label in labels:
                label_code = label['label_code']
                
                # 构建该标签的层级树路径
                tree_path = self.db.build_label_tree_path(label_code)
                
                # 将字典转换为JSON字符串存储
                label_code_to_tree[label_code] = json.dumps(tree_path, ensure_ascii=False)
            
            logger.info(f"  构建了 {len(label_code_to_tree)} 个标签层级树")
            
            # 4. 写入Redis
            redis_key = f"label_code2label_tree:{system_code}"
            
            if label_code_to_tree:
                # 先删除旧数据
                self.redis.delete(redis_key)
                
                # 批量写入新数据
                self.redis.hmset(redis_key, label_code_to_tree)
                logger.info(f"  已写入Redis: {redis_key}, 共 {len(label_code_to_tree)} 条记录")
            else:
                logger.warning(f"  标签体系 {system_code} 下没有标签数据")
        
        logger.info("标签层级树同步完成")
