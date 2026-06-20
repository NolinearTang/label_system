# 意图规则导入脚本使用说明

## 功能介绍

`import_intent_rules.py` 是一个用于批量导入意图规则数据到 `intent_rules` 表的脚本。

## 主要功能

1. **导入句子规则** - 用于意图识别的完整句子
2. **导入关键词规则** - 白名单/黑名单关键词
3. **从文件导入** - 批量从文本文件导入规则
4. **删除规则** - 删除指定标签的所有规则

## 使用方法

### 方法1: 直接在脚本中修改示例代码

编辑 `import_intent_rules.py` 中的 `example_usage()` 函数：

```python
def example_usage():
    # 初始化
    config = get_config('development')
    mysql_config = config.get_mysql_config()
    db_client = MySQLClient(mysql_config)
    db_client.connect()
    
    importer = IntentRuleImporter(db_client)
    
    # 你的数据
    label_code = "INTENT_PRODUCT_001"
    sentences = [
        "如何配置通讯参数",
        "通讯参数怎么设置",
        # ... 更多句子
    ]
    
    # 导入
    importer.import_sentences(label_code, sentences)
    
    db_client.close()
```

然后运行：
```bash
python scripts/import_intent_rules.py
```

### 方法2: 作为模块导入使用

创建你自己的脚本：

```python
import sys
sys.path.append('..')

from config import get_config
from db import MySQLClient
from scripts.import_intent_rules import IntentRuleImporter

# 初始化
config = get_config('development')
mysql_config = config.get_mysql_config()
db_client = MySQLClient(mysql_config)
db_client.connect()

importer = IntentRuleImporter(db_client)

# 导入句子
label_code = "INTENT_PRODUCT_001"
sentences = ["句子1", "句子2", "句子3"]
importer.import_sentences(label_code, sentences)

db_client.close()
```

### 方法3: 从文件导入

1. 创建文本文件 `sentences.txt`，每行一条规则：
```
如何配置通讯参数
通讯参数怎么设置
参数配置方法
怎样修改设备参数
```

2. 运行导入：
```python
importer.import_from_file(
    label_code='INTENT_PRODUCT_001',
    file_path='data/sentences.txt',
    rule_type='sentence'
)
```

## API 说明

### 1. import_sentences()

导入句子类型的规则。

```python
importer.import_sentences(
    label_code='INTENT_PRODUCT_001',  # 必填：标签编码
    sentences=[                        # 必填：句子列表
        "如何配置通讯参数",
        "通讯参数怎么设置"
    ],
    is_active=True                     # 可选：是否启用，默认True
)
```

### 2. import_keywords()

导入关键词规则。

```python
importer.import_keywords(
    label_code='INTENT_PRODUCT_001',        # 必填：标签编码
    keywords=['配置', '参数', '设置'],      # 必填：关键词列表
    rule_type='keyword_whitelist',          # 可选：关键词类型
    is_active=True                          # 可选：是否启用
)
```

**rule_type 可选值：**
- `keyword_whitelist` - 关键词白名单（默认）
- `keyword_blacklist` - 关键词黑名单

### 3. import_from_file()

从文件导入规则。

```python
importer.import_from_file(
    label_code='INTENT_PRODUCT_001',   # 必填：标签编码
    file_path='data/sentences.txt',    # 必填：文件路径
    rule_type='sentence',              # 可选：规则类型，默认sentence
    encoding='utf-8'                   # 可选：文件编码，默认utf-8
)
```

### 4. delete_rules_by_label()

删除指定标签的所有规则。

```python
deleted_count = importer.delete_rules_by_label('INTENT_PRODUCT_001')
print(f"已删除 {deleted_count} 条规则")
```

## 规则编码生成规则

自动生成的规则编码格式：
```
rule_code_xxxxxxxx
```

其中 `xxxxxxxx` 是8位数字，前面以0填充，自动递增。

生成逻辑：
1. 查询数据库中最大的 rule_code
2. 提取数字部分并递增
3. 生成新的 rule_code

示例：
```
rule_code_00000001
rule_code_00000002
rule_code_00000123
rule_code_99999999
```

## 注意事项

1. **label_code 必须存在** - 在导入规则前，确保对应的 `label_code` 已经在 `labels` 表中存在
2. **重复导入** - 每次导入都会生成新的 `rule_code`，不会自动去重
3. **批量删除** - 使用 `delete_rules_by_label()` 会删除该标签下的所有规则，请谨慎操作
4. **环境配置** - 修改 `get_config('development')` 中的参数来切换环境

## 完整示例

```python
#!/usr/bin/env python3
import sys
sys.path.append('..')

from config import get_config
from db import MySQLClient
from scripts.import_intent_rules import IntentRuleImporter

def main():
    # 初始化数据库连接
    config = get_config('development')
    mysql_config = config.get_mysql_config()
    db_client = MySQLClient(mysql_config)
    db_client.connect()
    
    try:
        importer = IntentRuleImporter(db_client)
        
        # 产品咨询意图
        product_label = "INTENT_PRODUCT_001"
        
        # 1. 导入句子规则
        product_sentences = [
            "如何配置通讯参数",
            "通讯参数怎么设置",
            "参数配置方法是什么",
            "怎样修改设备参数",
            "设备配置教程在哪里",
            "RS485参数怎么调",
            "Modbus地址如何设置"
        ]
        importer.import_sentences(product_label, product_sentences)
        
        # 2. 导入关键词白名单
        product_keywords = [
            "配置", "参数", "设置", "修改",
            "通讯", "Modbus", "RS485", "波特率"
        ]
        importer.import_keywords(
            product_label, 
            product_keywords, 
            'keyword_whitelist'
        )
        
        # 售后服务意图
        service_label = "INTENT_SERVICE_001"
        
        # 从文件导入
        importer.import_from_file(
            service_label,
            'data/service_sentences.txt',
            'sentence'
        )
        
        print("所有数据导入完成！")
        
    finally:
        db_client.close()

if __name__ == '__main__':
    main()
```

## 文件导入格式示例

`data/sentences.txt` 文件内容：
```
如何配置通讯参数
通讯参数怎么设置
参数配置方法是什么
怎样修改设备参数
```

每行一条规则，空行会自动跳过。
