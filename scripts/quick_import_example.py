#!/usr/bin/env python3
"""
快速导入示例脚本

使用方法：
1. 修改下面的 label_code 和 sentences 列表
2. 运行: python scripts/quick_import_example.py
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_config
from db import MySQLClient
from scripts.import_intent_rules import IntentRuleImporter


def main():
    """主函数"""
    
    # ==================== 配置区域 ====================
    
    # 1. 选择环境：'development', 'test', 'production'
    environment = 'development'
    
    # 2. 设置标签编码
    label_code = "INTENT_PRODUCT_001"
    
    # 3. 准备要导入的句子列表
    sentences = [
        "如何配置通讯参数",
        "通讯参数怎么设置",
        "参数配置方法是什么",
        "怎样修改设备参数",
        "设备配置教程在哪里",
        "RS485参数怎么调",
        "Modbus地址如何设置",
    ]
    
    # 4. 准备关键词列表（可选）
    keywords_whitelist = [
        "配置",
        "参数",
        "设置",
        "修改",
        "通讯",
    ]
    
    # ==================== 执行导入 ====================
    
    print("=" * 60)
    print("意图规则导入工具")
    print("=" * 60)
    
    # 初始化数据库连接
    config = get_config(environment)
    mysql_config = config.get_mysql_config()
    db_client = MySQLClient(mysql_config)
    
    try:
        db_client.connect()
        print(f"✓ 数据库连接成功 ({environment} 环境)")
        
        # 创建导入器
        importer = IntentRuleImporter(db_client)
        
        # 导入句子规则
        print(f"\n开始导入句子规则到 label_code: {label_code}")
        print(f"句子数量: {len(sentences)}")
        success_count = importer.import_sentences(label_code, sentences)
        print(f"✓ 句子规则导入完成，成功 {success_count} 条")
        
        # 导入关键词（如果有）
        if keywords_whitelist:
            print(f"\n开始导入关键词白名单")
            print(f"关键词数量: {len(keywords_whitelist)}")
            keyword_count = importer.import_keywords(
                label_code, 
                keywords_whitelist, 
                'keyword_whitelist'
            )
            print(f"✓ 关键词导入完成，成功 {keyword_count} 条")
        
        print("\n" + "=" * 60)
        print("✓ 所有数据导入完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 导入失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        db_client.close()
        print("\n数据库连接已关闭")


if __name__ == '__main__':
    main()
