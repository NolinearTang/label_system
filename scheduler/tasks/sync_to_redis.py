import json
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
            
            # 同步意图句子规则到Redis
            self.sync_intent_sentences_to_redis()
            
            # 同步意图标签层级树到Redis
            self.sync_intent_label_tree_to_redis()
            
            # 同步实体层级树到Redis
            self.sync_item_tree_to_redis()
            
            logger.info("数据同步任务执行完成")
        except Exception as e:
            logger.error(f"数据同步任务执行失败: {str(e)}", exc_info=True)
            raise
    
    def sync_items_to_redis(self):
        """
        同步实体信息到Redis
        格式: item_name2label:{system_code} -> Hash {item_name: label_code}
        只处理 system_type=entity 的标签体系
        """
        logger.info("开始同步实体信息到Redis...")
        
        # 1. 获取所有标签体系
        tag_systems = self.db.get_all_tag_systems()
        logger.info(f"获取到 {len(tag_systems)} 个标签体系")
        
        for system in tag_systems:
            system_code = system['system_code']
            system_name = system['system_name']
            system_type = system['system_type']
            
            # 只处理实体类标签体系
            if system_type != 'entity':
                logger.debug(f"跳过非实体类标签体系: {system_name} ({system_code}), type={system_type}")
                continue
            
            logger.info(f"处理实体标签体系: {system_name} ({system_code})")
            
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
            redis_key = f"kllm:entity:item_name2label:{system_code}"
            
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
        同步实体标签层级树到Redis
        格式: entity:label_code2label_tree:{system_code} -> Hash {label_code: JSON字符串}
        JSON内容: {"level1": "标签名1", "level2": "标签名2", ...}
        只处理 system_type=entity 的标签体系
        """
        logger.info("开始同步实体标签层级树到Redis...")
        
        # 1. 获取所有标签体系
        tag_systems = self.db.get_all_tag_systems()
        logger.info(f"获取到 {len(tag_systems)} 个标签体系")
        
        for system in tag_systems:
            system_code = system['system_code']
            system_name = system['system_name']
            system_type = system['system_type']
            
            # 只处理实体类标签体系
            if system_type != 'entity':
                logger.debug(f"跳过非实体类标签体系: {system_name} ({system_code}), type={system_type}")
                continue
            
            logger.info(f"处理实体标签体系: {system_name} ({system_code})")
            
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
            redis_key = f"kllm:entity:label_code2label_tree:{system_code}"
            
            if label_code_to_tree:
                # 先删除旧数据
                self.redis.delete(redis_key)
                
                # 批量写入新数据
                self.redis.hmset(redis_key, label_code_to_tree)
                logger.info(f"  已写入Redis: {redis_key}, 共 {len(label_code_to_tree)} 条记录")
            else:
                logger.warning(f"  标签体系 {system_code} 下没有标签数据")
        
        logger.info("实体标签层级树同步完成")
    
    def sync_item_tree_to_redis(self):
        """
        同步实体层级树到Redis
        格式: kllm:entity:item_name2tree:{system_code} -> Hash {item_name: JSON字符串}
        JSON内容: {"level1": "实体名1", "level2": "实体名2", ...}
        只处理 system_type=entity 的标签体系
        注意：同义词的层级树最后一层是标准词（item_name），而不是同义词本身
        """
        logger.info("开始同步实体层级树到Redis...")
        
        # 1. 获取所有标签体系
        tag_systems = self.db.get_all_tag_systems()
        logger.info(f"获取到 {len(tag_systems)} 个标签体系")
        
        for system in tag_systems:
            system_code = system['system_code']
            system_name = system['system_name']
            system_type = system['system_type']
            
            # 只处理实体类标签体系
            if system_type != 'entity':
                logger.debug(f"跳过非实体类标签体系: {system_name} ({system_code}), type={system_type}")
                continue
            
            logger.info(f"处理实体标签体系: {system_name} ({system_code})")
            
            # 2. 获取该体系下的所有实体
            items = self.db.get_items_by_system(system_code)
            logger.info(f"  获取到 {len(items)} 个实体")
            
            # 3. 构建 item_name -> item_tree 映射
            item_name_to_tree = {}
            
            for item in items:
                item_name = item['item_name']
                item_code = item['item_code']
                
                # 构建该实体的层级树路径
                tree_path = self.db.build_item_tree_path(item_code)
                
                # 实体名称（标准词）映射到层级树（标准化处理）
                normalized_item_name = item_name.lower().strip()
                tree_json = json.dumps(tree_path, ensure_ascii=False)
                item_name_to_tree[normalized_item_name] = tree_json
                
                # 4. 获取该实体的所有同义词
                synonyms = self.db.get_synonyms_by_item(item_code)
                
                # 同义词也映射到相同的层级树（最后一层是标准词，不是同义词本身）
                for synonym in synonyms:
                    synonym_name = synonym['synonym']
                    normalized_synonym = synonym_name.lower().strip()
                    # 同义词使用相同的层级树（层级树最后一层是标准词item_name）
                    item_name_to_tree[normalized_synonym] = tree_json
            
            logger.info(f"  构建了 {len(item_name_to_tree)} 个实体层级树（包含同义词）")
            
            # 5. 写入Redis
            redis_key = f"kllm:entity:item_name2tree:{system_code}"
            
            if item_name_to_tree:
                # 先删除旧数据
                self.redis.delete(redis_key)
                
                # 批量写入新数据
                self.redis.hmset(redis_key, item_name_to_tree)
                logger.info(f"  已写入Redis: {redis_key}, 共 {len(item_name_to_tree)} 条记录")
            else:
                logger.warning(f"  标签体系 {system_code} 下没有实体数据")
        
        logger.info("实体层级树同步完成")
    
    def sync_intent_sentences_to_redis(self):
        """
        同步意图句子规则到Redis
        格式: sentence:rule_name2label:{system_code} -> Hash {rule_name: label_code}
        只处理 system_type=intent 且 rule_type=sentence 的规则
        """
        logger.info("开始同步意图句子规则到Redis...")
        
        # 1. 获取所有标签体系
        tag_systems = self.db.get_all_tag_systems()
        logger.info(f"获取到 {len(tag_systems)} 个标签体系")
        
        for system in tag_systems:
            system_code = system['system_code']
            system_name = system['system_name']
            system_type = system['system_type']
            
            # 只处理意图类标签体系
            if system_type != 'intent':
                logger.debug(f"跳过非意图类标签体系: {system_name} ({system_code}), type={system_type}")
                continue
            
            logger.info(f"处理意图标签体系: {system_name} ({system_code})")
            
            # 2. 获取该体系下的所有句子类型规则
            rules = self.db.get_intent_rules_by_system(system_code, rule_type='sentence')
            logger.info(f"  获取到 {len(rules)} 个句子规则")
            
            # 3. 构建 rule_name -> label_code 映射
            rule_name_to_label = {}
            
            for rule in rules:
                rule_name = rule['rule_name']
                label_code = rule['label_code']
                
                # 规则名称映射到标签编码（标准化处理）
                normalized_rule_name = rule_name.lower().strip()
                rule_name_to_label[normalized_rule_name] = label_code
            
            logger.info(f"  构建了 {len(rule_name_to_label)} 个句子规则映射")
            
            # 4. 写入Redis
            redis_key = f"kllm:intent:sentence:rule_name2label:{system_code}"
            
            if rule_name_to_label:
                # 先删除旧数据
                self.redis.delete(redis_key)
                
                # 批量写入新数据
                self.redis.hmset(redis_key, rule_name_to_label)
                logger.info(f"  已写入Redis: {redis_key}, 共 {len(rule_name_to_label)} 条记录")
            else:
                logger.warning(f"  意图体系 {system_code} 下没有句子规则数据")
        
        logger.info("意图句子规则同步完成")
    
    def sync_intent_label_tree_to_redis(self):
        """
        同步意图标签层级树到Redis
        格式: intent:label_code2label_tree:{system_code} -> Hash {label_code: JSON字符串}
        JSON内容: {"level1": "标签名1", "level2": "标签名2", ...}
        只处理 system_type=intent 的标签体系
        """
        logger.info("开始同步意图标签层级树到Redis...")
        
        # 1. 获取所有标签体系
        tag_systems = self.db.get_all_tag_systems()
        logger.info(f"获取到 {len(tag_systems)} 个标签体系")
        
        for system in tag_systems:
            system_code = system['system_code']
            system_name = system['system_name']
            system_type = system['system_type']
            
            # 只处理意图类标签体系
            if system_type != 'intent':
                logger.debug(f"跳过非意图类标签体系: {system_name} ({system_code}), type={system_type}")
                continue
            
            logger.info(f"处理意图标签体系: {system_name} ({system_code})")
            
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
            redis_key = f"kllm:intent:label_code2label_tree:{system_code}"
            
            if label_code_to_tree:
                # 先删除旧数据
                self.redis.delete(redis_key)
                
                # 批量写入新数据
                self.redis.hmset(redis_key, label_code_to_tree)
                logger.info(f"  已写入Redis: {redis_key}, 共 {len(label_code_to_tree)} 条记录")
            else:
                logger.warning(f"  标签体系 {system_code} 下没有标签数据")
        
        logger.info("意图标签层级树同步完成")
