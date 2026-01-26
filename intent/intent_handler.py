import json
import logging
import threading
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class IntentHandler:
    """意图处理器"""
    
    def __init__(self, config, redis_client):
        """
        初始化意图处理器
        
        Args:
            config: 配置对象
            redis_client: Redis客户端
        """
        self.config = config
        self.redis = redis_client
        
        # 从配置中获取意图体系的system_code
        self.intent_system_code = config.get("user_id", {}).get("intent_system_code")
        # 从配置中获取实体体系的system_code
        self.entity_system_code = config.get("user_id", {}).get("entity_system_code")
        
        # 线程锁，保证读写安全
        self._lock = threading.RLock()
        
        # 初始化意图相关数据
        self.sentence_rule_name2label = {}
        self.intent_label_code2label_tree = {}
        
        # 初始化实体相关数据
        self.entity_list = []  # 实体列表
        self.item_name2label = {}  # 实体名称到标签编码的映射
        self.item_name2tree = {}  # 实体名称到层级树的映射
        
        # 首次加载数据
        self._load_data_from_redis()
        self._load_entity_from_redis()
    
    def _load_data_from_redis(self):
        """从Redis加载意图相关数据（线程安全）"""
        try:
            # 临时存储新数据
            new_sentence_rule_name2label = {}
            new_intent_label_code2label_tree = {}
            
            # 加载句子规则映射: sentence:rule_name2label:{system_code}
            sentence_key = f"kllm:intent:sentence:rule_name2label:{self.intent_system_code}"
            if self.redis.exists(sentence_key):
                new_sentence_rule_name2label = self.redis.client.hgetall(sentence_key)
                logger.info(f"已加载 {len(new_sentence_rule_name2label)} 条句子规则映射")
            else:
                logger.warning(f"Redis中不存在key: {sentence_key}")
            
            # 加载意图标签层级树: intent:label_code2label_tree:{system_code}
            tree_key = f"kllm:intent:label_code2label_tree:{self.intent_system_code}"
            if self.redis.exists(tree_key):
                raw_tree_data = self.redis.client.hgetall(tree_key)
                # 将JSON字符串解析为字典
                new_intent_label_code2label_tree = {
                    label_code: json.loads(tree_json)
                    for label_code, tree_json in raw_tree_data.items()
                }
                logger.info(f"已加载 {len(new_intent_label_code2label_tree)} 条意图标签层级树")
            else:
                logger.warning(f"Redis中不存在key: {tree_key}")
            
            # 使用锁更新数据，保证原子性
            with self._lock:
                self.sentence_rule_name2label = new_sentence_rule_name2label
                self.intent_label_code2label_tree = new_intent_label_code2label_tree
                
        except Exception as e:
            logger.error(f"从Redis加载意图数据失败: {str(e)}", exc_info=True)
            raise
    
    def _load_entity_from_redis(self):
        """从Redis加载实体相关数据（线程安全）"""
        try:
            # 临时存储新数据
            new_item_name2label = {}
            new_item_name2tree = {}
            
            # 加载实体名称到标签编码的映射: kllm:entity:item_name2label:{system_code}
            item_label_key = f"kllm:entity:item_name2label:{self.entity_system_code}"
            if self.redis.exists(item_label_key):
                new_item_name2label = self.redis.client.hgetall(item_label_key)
                logger.info(f"已加载 {len(new_item_name2label)} 条实体名称到标签映射")
            else:
                logger.warning(f"Redis中不存在key: {item_label_key}")
            
            # 加载实体名称到层级树的映射: kllm:entity:item_name2tree:{system_code}
            item_tree_key = f"kllm:entity:item_name2tree:{self.entity_system_code}"
            if self.redis.exists(item_tree_key):
                raw_tree_data = self.redis.client.hgetall(item_tree_key)
                # 将JSON字符串解析为字典
                new_item_name2tree = {
                    item_name: json.loads(tree_json)
                    for item_name, tree_json in raw_tree_data.items()
                }
                logger.info(f"已加载 {len(new_item_name2tree)} 条实体层级树")
            else:
                logger.warning(f"Redis中不存在key: {item_tree_key}")
            
            # 构建实体列表（所有实体名称，包括标准词和同义词）
            new_entity_list = list(new_item_name2label.keys())
            
            # 使用锁更新数据，保证原子性
            with self._lock:
                self.item_name2label = new_item_name2label
                self.item_name2tree = new_item_name2tree
                self.entity_list = new_entity_list
                
        except Exception as e:
            logger.error(f"从Redis加载实体数据失败: {str(e)}", exc_info=True)
            raise
    
    def intent_by_sentence(self, sentence: str) -> Optional[Dict[str, str]]:
        """
        根据句子判断意图标签（线程安全）
        
        Args:
            sentence: 输入的句子
            
        Returns:
            如果匹配到意图，返回意图的label_tree字典，否则返回None
            label_tree格式: {"level1": "标签名1", "level2": "标签名2", ...}
        """
        if not sentence or not self.sentence_rule_name2label:
            return None
        
        # 标准化输入句子
        normalized_sentence = sentence.lower().strip()
        
        # 使用锁保护读取操作
        with self._lock:
            # 在句子规则映射中查找
            label_code = self.sentence_rule_name2label.get(normalized_sentence)
            
            if not label_code:
                logger.debug(f"未找到句子 '{sentence}' 对应的意图标签")
                return None
            
            # 根据label_code获取层级树
            label_tree = self.intent_label_code2label_tree.get(label_code)
        
        if label_tree:
            logger.info(f"句子 '{sentence}' 匹配到意图标签: {label_code}, 层级树: {label_tree}")
            return label_tree
        else:
            logger.warning(f"找到label_code '{label_code}' 但未找到对应的层级树")
            return None
    
    def reload_data(self):
        """重新加载Redis数据（由外部调度器调用）"""
        logger.info("重新加载意图和实体数据...")
        self._load_data_from_redis()
        self._load_entity_from_redis()
