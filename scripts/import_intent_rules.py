#!/usr/bin/env python3
"""
意图规则数据入库脚本

功能：将意图规则数据批量导入到 intent_rules 表中
"""

import sys
import os
import logging
from typing import List, Dict, Any
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_config
from db import MySQLClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntentRuleImporter:
    """意图规则导入器"""
    
    def __init__(self, db_client: MySQLClient):
        self.db = db_client
    
    def generate_rule_code(self) -> str:
        """
        生成规则编码
        
        从数据库中查询最大的 rule_code，然后递增生成新的编码
        
        Returns:
            规则编码，格式: rule_code_xxxxxxxx (8位数字，前面补0)
            例如: rule_code_00000001, rule_code_00000002
        
        Raises:
            Exception: 如果查询数据库失败
        """
        # 查询当前最大的 rule_code
        query_sql = """
            SELECT rule_code 
            FROM intent_rules 
            WHERE rule_code LIKE 'rule_code_%'
            ORDER BY rule_code DESC 
            LIMIT 1
        """
        result = self.db.execute_query(query_sql)
        
        if result and len(result) > 0:
            max_rule_code = result[0]['rule_code']
            # 提取数字部分
            # rule_code_00000123 -> 00000123 -> 123
            number_part = max_rule_code.split('_')[-1]
            next_number = int(number_part) + 1
        else:
            # 如果没有记录，从1开始
            next_number = 1
        
        # 生成新的 rule_code，8位数字，前面补0
        new_rule_code = f"rule_code_{next_number:08d}"
        logger.debug(f"生成新的 rule_code: {new_rule_code}")
        return new_rule_code
    
    def import_sentences(
        self, 
        label_code: str, 
        sentences: List[str],
        is_active: bool = True
    ) -> int:
        """
        导入句子类型的意图规则
        
        Args:
            label_code: 标签编码
            sentences: 句子列表
            is_active: 是否启用
            
        Returns:
            成功导入的数量
        """
        logger.info(f"开始导入意图规则，label_code: {label_code}, 句子数: {len(sentences)}")
        
        # 验证 label_code 是否存在
        check_sql = "SELECT COUNT(*) as count FROM labels WHERE label_code = %s"
        result = self.db.execute_query(check_sql, (label_code,))
        
        if not result or result[0]['count'] == 0:
            logger.error(f"label_code {label_code} 不存在，请先创建标签")
            return 0
        
        success_count = 0
        failed_count = 0
        
        for i, sentence in enumerate(sentences, start=1):
            if not sentence or not sentence.strip():
                logger.warning(f"跳过空句子，索引: {i}")
                continue
            
            sentence = sentence.strip()
            rule_code = self.generate_rule_code()
            
            try:
                # 插入规则
                insert_sql = """
                    INSERT INTO intent_rules 
                    (rule_code, rule_type, rule_name, label_code, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                """
                self.db.execute_query(
                    insert_sql, 
                    (rule_code, 'sentence', sentence, label_code, is_active)
                )
                success_count += 1
                logger.info(f"成功导入第 {i} 条: {sentence[:50]}...")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"导入第 {i} 条失败: {sentence[:50]}..., 错误: {str(e)}")
        
        logger.info(
            f"导入完成！成功: {success_count} 条，失败: {failed_count} 条，"
            f"总计: {len(sentences)} 条"
        )
        return success_count
    
    def import_keywords(
        self,
        label_code: str,
        keywords: List[str],
        rule_type: str = 'keyword_whitelist',
        is_active: bool = True
    ) -> int:
        """
        导入关键词类型的意图规则
        
        Args:
            label_code: 标签编码
            keywords: 关键词列表
            rule_type: 规则类型 (keyword_whitelist 或 keyword_blacklist)
            is_active: 是否启用
            
        Returns:
            成功导入的数量
        """
        if rule_type not in ['keyword_whitelist', 'keyword_blacklist']:
            logger.error(f"不支持的规则类型: {rule_type}")
            return 0
        
        logger.info(f"开始导入关键词规则，label_code: {label_code}, 类型: {rule_type}, 数量: {len(keywords)}")
        
        # 验证 label_code 是否存在
        check_sql = "SELECT COUNT(*) as count FROM labels WHERE label_code = %s"
        result = self.db.execute_query(check_sql, (label_code,))
        
        if not result or result[0]['count'] == 0:
            logger.error(f"label_code {label_code} 不存在，请先创建标签")
            return 0
        
        success_count = 0
        failed_count = 0
        
        for i, keyword in enumerate(keywords, start=1):
            if not keyword or not keyword.strip():
                logger.warning(f"跳过空关键词，索引: {i}")
                continue
            
            keyword = keyword.strip()
            rule_code = self.generate_rule_code()
            
            try:
                # 插入规则
                insert_sql = """
                    INSERT INTO intent_rules 
                    (rule_code, rule_type, rule_name, label_code, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                """
                self.db.execute_query(
                    insert_sql,
                    (rule_code, rule_type, keyword, label_code, is_active)
                )
                success_count += 1
                logger.info(f"成功导入第 {i} 条关键词: {keyword}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"导入第 {i} 条关键词失败: {keyword}, 错误: {str(e)}")
        
        logger.info(
            f"导入完成！成功: {success_count} 条，失败: {failed_count} 条，"
            f"总计: {len(keywords)} 条"
        )
        return success_count
    
    def import_from_file(
        self,
        label_code: str,
        file_path: str,
        rule_type: str = 'sentence',
        encoding: str = 'utf-8'
    ) -> int:
        """
        从文件导入规则（每行一条规则）
        
        Args:
            label_code: 标签编码
            file_path: 文件路径
            rule_type: 规则类型
            encoding: 文件编码
            
        Returns:
            成功导入的数量
        """
        logger.info(f"从文件导入规则: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return 0
        
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            
            logger.info(f"从文件读取 {len(lines)} 条规则")
            
            if rule_type == 'sentence':
                return self.import_sentences(label_code, lines)
            elif rule_type in ['keyword_whitelist', 'keyword_blacklist']:
                return self.import_keywords(label_code, lines, rule_type)
            else:
                logger.error(f"不支持的规则类型: {rule_type}")
                return 0
                
        except Exception as e:
            logger.error(f"读取文件失败: {str(e)}")
            return 0
    
    def delete_rules_by_label(self, label_code: str) -> int:
        """
        删除指定标签的所有规则
        
        Args:
            label_code: 标签编码
            
        Returns:
            删除的数量
        """
        logger.warning(f"准备删除 label_code: {label_code} 的所有规则")
        
        try:
            delete_sql = "DELETE FROM intent_rules WHERE label_code = %s"
            result = self.db.execute_query(delete_sql, (label_code,))
            
            # 获取删除数量
            count_sql = "SELECT ROW_COUNT() as count"
            count_result = self.db.execute_query(count_sql)
            deleted_count = count_result[0]['count'] if count_result else 0
            
            logger.info(f"已删除 {deleted_count} 条规则")
            return deleted_count
            
        except Exception as e:
            logger.error(f"删除规则失败: {str(e)}")
            return 0


def example_usage():
    """使用示例"""
    
    # 初始化配置和数据库
    config = get_config('development')
    mysql_config = config.get_mysql_config()
    db_client = MySQLClient(mysql_config)
    db_client.connect()
    
    # 创建导入器
    importer = IntentRuleImporter(db_client)
    
    # 示例1: 导入句子规则
    label_code = "INTENT_PRODUCT_001"
    sentences = [
        "如何配置通讯参数",
        "通讯参数怎么设置",
        "参数配置方法",
        "怎样修改设备参数",
        "设备配置教程"
    ]
    importer.import_sentences(label_code, sentences)
    
    # 示例2: 导入关键词白名单
    keywords_whitelist = [
        "配置",
        "参数",
        "设置",
        "修改"
    ]
    importer.import_keywords(label_code, keywords_whitelist, 'keyword_whitelist')
    
    # 示例3: 从文件导入
    # importer.import_from_file(label_code, 'sentences.txt', 'sentence')
    
    # 示例4: 删除规则
    # importer.delete_rules_by_label(label_code)
    
    db_client.close()


if __name__ == '__main__':
    """
    使用方法:
    
    1. 直接运行示例:
       python scripts/import_intent_rules.py
    
    2. 作为模块导入使用:
       from scripts.import_intent_rules import IntentRuleImporter
       importer = IntentRuleImporter(db_client)
       importer.import_sentences('INTENT_001', ['句子1', '句子2'])
    """
    
    # 运行示例
    example_usage()
