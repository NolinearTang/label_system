import json
import logging
import threading
import numpy as np
import faiss
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


class IntentHandler:
    """意图处理器"""
    
    def __init__(self, config, redis_client, embedding_handler=None):
        """
        初始化意图处理器
        
        Args:
            config: 配置对象
            redis_client: Redis客户端
            embedding_handler: Embedding处理器（可选，用于faiss检索）
        """
        self.config = config
        self.redis = redis_client
        self.embedding_handler = embedding_handler
        
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
        
        # 初始化faiss相关数据
        # faiss_dic: key为意图名称（intent_system_code的key），value为faiss索引
        self.faiss_dic = {}
        # faiss_label_mapping: key为意图名称，value为label_code列表（与faiss索引对应）
        self.faiss_label_mapping = {}
        
        # 首次加载数据
        self._load_data_from_redis()
        self._load_entity_from_redis()
        self._load_faiss_from_redis()
    
    def _load_data_from_redis(self):
        """从Redis加载意图相关数据（线程安全）"""
        if not self.intent_system_code:
            logger.warning("intent_system_code未配置，跳过意图数据加载")
            return
        
        try:
            # 临时存储新数据 - 使用二级字典结构按 intent_name 隔离
            new_sentence_rule_name2label = {}
            new_intent_label_code2label_tree = {}
            
            # 遍历所有意图体系配置
            for intent_name, system_code in self.intent_system_code.items():
                logger.info(f"加载意图 {intent_name} (system_code: {system_code}) 的数据")
                
                # 初始化该 intent_name 的数据
                new_sentence_rule_name2label[intent_name] = {}
                new_intent_label_code2label_tree[intent_name] = {}
                
                # 加载句子规则映射: sentence:rule_name2label:{system_code}
                sentence_key = f"kllm:intent:sentence:rule_name2label:{system_code}"
                if self.redis.exists(sentence_key):
                    sentence_data = self.redis.client.hgetall(sentence_key)
                    new_sentence_rule_name2label[intent_name] = sentence_data
                    logger.info(f"  已加载 {len(sentence_data)} 条句子规则映射")
                else:
                    logger.warning(f"  Redis中不存在key: {sentence_key}")
                
                # 加载意图标签层级树: intent:label_code2label_tree:{system_code}
                tree_key = f"kllm:intent:label_code2label_tree:{system_code}"
                if self.redis.exists(tree_key):
                    raw_tree_data = self.redis.client.hgetall(tree_key)
                    # 将JSON字符串解析为字典
                    for label_code, tree_json in raw_tree_data.items():
                        new_intent_label_code2label_tree[intent_name][label_code] = json.loads(tree_json)
                    logger.info(f"  已加载 {len(raw_tree_data)} 条意图标签层级树")
                else:
                    logger.warning(f"  Redis中不存在key: {tree_key}")
            
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
    
    def intent_by_sentence(self, sentence: str, intent_name: str) -> Optional[Dict[str, str]]:
        """
        根据句子判断意图标签（线程安全）
        
        Args:
            sentence: 输入的句子
            intent_name: 意图名称
            
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
            if intent_name not in self.sentence_rule_name2label:
                logger.warning(f"意图 {intent_name} 不存在")
                return None
            
            label_code = self.sentence_rule_name2label[intent_name].get(normalized_sentence)
            
            if not label_code:
                logger.debug(f"在意图 {intent_name} 中未找到句子 '{sentence}'")
                return None
            
            # 根据label_code获取层级树
            label_tree = self.intent_label_code2label_tree[intent_name].get(label_code)
            
            if label_tree:
                logger.info(f"句子 '{sentence}' 在意图 {intent_name} 中匹配到标签: {label_code}, 层级树: {label_tree}")
                return label_tree
            else:
                logger.warning(f"找到label_code '{label_code}' 但未找到对应的层级树")
                return None
    
    def reload_data(self):
        """重新加载Redis数据（由外部调度器调用）"""
        logger.info("重新加载意图和实体数据...")
        self._load_data_from_redis()
        self._load_entity_from_redis()
        self._load_faiss_from_redis()
    
    def _load_faiss_from_redis(self):
        """从Redis加载faiss相关数据（线程安全）"""
        if not self.embedding_handler:
            logger.warning("embedding_handler未配置，跳过faiss数据加载")
            return
        
        if not self.intent_system_code:
            logger.warning("intent_system_code未配置，跳过faiss数据加载")
            return
        
        try:
            logger.info("开始加载faiss数据...")
            
            # 临时存储新数据
            new_faiss_dic = {}
            new_faiss_label_mapping = {}
            
            # 遍历所有意图体系配置
            for intent_name, system_code in self.intent_system_code.items():
                logger.info(f"加载意图 {intent_name} (system_code: {system_code}) 的faiss数据")
                
                # 从Redis加载faiss数据
                redis_key = f"kllm:intent:faiss:{system_code}"
                
                if not self.redis.exists(redis_key):
                    logger.warning(f"Redis中不存在key: {redis_key}")
                    continue
                
                # 获取所有label_code和对应的embedding数据
                raw_data = self.redis.client.hgetall(redis_key)
                
                if not raw_data:
                    logger.warning(f"Redis key {redis_key} 中没有数据")
                    continue
                
                logger.info(f"  获取到 {len(raw_data)} 个label_code的embedding数据")
                
                # 构建faiss索引
                all_embeddings = []
                all_label_codes = []
                
                for label_code, embedding_json in raw_data.items():
                    # 解析JSON数据
                    embedding_data = json.loads(embedding_json)
                    
                    # 提取所有embedding向量和对应的label_code
                    for item in embedding_data:
                        embedding = item['embedding']
                        all_embeddings.append(embedding)
                        all_label_codes.append(label_code)
                
                if not all_embeddings:
                    logger.warning(f"意图 {intent_name} 没有embedding数据")
                    continue
                
                # 转换为numpy数组
                embeddings_array = np.array(all_embeddings, dtype=np.float32)
                dimension = embeddings_array.shape[1]
                
                logger.info(f"  总共 {len(all_embeddings)} 个embedding向量，维度: {dimension}")
                
                # 创建faiss索引（使用L2距离）
                index = faiss.IndexFlatL2(dimension)
                index.add(embeddings_array)
                
                # 使用锁更新数据
                with self._lock:
                    new_faiss_dic[intent_name] = index
                    new_faiss_label_mapping[intent_name] = all_label_codes
                
                logger.info(f"  已为意图 {intent_name} 创建faiss索引，包含 {index.ntotal} 个向量")
            
            # 使用锁更新全局数据
            with self._lock:
                self.faiss_dic = new_faiss_dic
                self.faiss_label_mapping = new_faiss_label_mapping
            
            logger.info(f"faiss数据加载完成，共加载 {len(new_faiss_dic)} 个意图索引")
            
        except Exception as e:
            logger.error(f"从Redis加载faiss数据失败: {str(e)}", exc_info=True)
            raise
    
    def search_intent_by_faiss(
        self, 
        query: str, 
        intent_name: str
    ) -> Dict[str, str]:
        """
        使用faiss检索意图
        
        Args:
            query: 查询文本
            intent_name: 意图名称（intent_system_code的key）
            
        Returns:
            如果最相似的结果相似度 >= 0.95，返回对应的label_tree字典，否则返回空字典
            label_tree格式: {"level1": "标签名1", "level2": "标签名2", ...}
        """
        if not self.embedding_handler:
            logger.warning("embedding_handler未配置，无法进行faiss检索")
            return {}
        
        # 检查意图是否存在
        if intent_name not in self.faiss_dic:
            logger.warning(f"意图 {intent_name} 的faiss索引不存在")
            return {}
        
        try:
            # 获取查询文本的embedding
            query_embedding = self.embedding_handler.get_embedding(query)
            query_vector = np.array([query_embedding], dtype=np.float32)
            
            # 使用锁保护读取操作
            with self._lock:
                index = self.faiss_dic[intent_name]
                label_mapping = self.faiss_label_mapping[intent_name]
                
                # 只检索最相似的1个结果
                distances, indices = index.search(query_vector, 1)
                
                # 获取第一个结果
                distance = distances[0][0]
                idx = indices[0][0]
                
                # 检查是否有效
                if idx == -1:
                    logger.debug(f"faiss检索未找到有效结果，查询: '{query}'")
                    return {}
                
                label_code = label_mapping[idx]
                
                # 将L2距离转换为相似度分数（距离越小，相似度越高）
                # 使用负指数函数将距离转换为0-1之间的相似度
                similarity = 1.0 / (1.0 + distance)
                
                logger.info(
                    f"faiss检索结果: label_code={label_code}, "
                    f"similarity={similarity:.4f}, distance={distance:.4f}, 查询: '{query}'"
                )
                
                # 判断相似度是否 >= 0.95
                if similarity >= 0.95:
                    # 获取label_tree（从对应的 intent_name 中获取）
                    label_tree = self.intent_label_code2label_tree.get(intent_name, {}).get(label_code, {})
                    logger.info(f"相似度满足阈值(>= 0.95)，返回标签树: {label_tree}")
                    return label_tree
                else:
                    logger.info(f"相似度 {similarity:.4f} 低于阈值 0.95，返回空字典")
                    return {}
            
        except Exception as e:
            logger.error(f"faiss检索失败: {str(e)}", exc_info=True)
            return {}
