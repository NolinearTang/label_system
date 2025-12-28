-- =================================================================
-- 标签体系管理系统 数据库SCHEMA (V2)
-- 设计时间: 2025-10-20
-- 设计核心:
-- 1. tag_systems: 定义顶层体系 (产品体系, 意图体系)
-- 2. labels: 定义具体的、有层级的标签 (产品线 -> 产品系列)
-- 3. items: 存放具体的、有层级的实体 (伺服 -> SV660系列)
-- 4. item_synonyms: 存放实体的同义词
-- 5. intent_rules: 存放意图规则
-- =================================================================

-- 1. 标签体系表 (tag_systems)
-- 定义顶层的标签体系
CREATE TABLE tag_systems (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    system_name VARCHAR(100) NOT NULL UNIQUE COMMENT '体系名称',
    system_code VARCHAR(50) NOT NULL UNIQUE COMMENT '体系编码',
    system_type VARCHAR(50) NOT NULL COMMENT '体系类型 (例如: intent, entity)',
    description TEXT COMMENT '体系描述',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='标签体系表';

-- 2. 标签定义表 (labels)
-- 存放具体的标签定义及其层级关系
CREATE TABLE labels (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    label_name VARCHAR(100) NOT NULL COMMENT '标签名称',
    label_code VARCHAR(50) NOT NULL UNIQUE COMMENT '标签编码',
    parent_label_code VARCHAR(50) COMMENT '父级标签编码',
    system_code VARCHAR(50) NOT NULL COMMENT '所属体系编码',
    level INT NOT NULL DEFAULT 1 COMMENT '标签层级',
    description TEXT COMMENT '标签描述',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (system_code) REFERENCES tag_systems(system_code),
    FOREIGN KEY (parent_label_code) REFERENCES labels(label_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='标签定义表';

-- 3. 实体数据表 (items)
-- 存放具体的、可分层的实体数据
CREATE TABLE items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    item_name VARCHAR(200) NOT NULL COMMENT '实体名称',
    item_code VARCHAR(100) NOT NULL UNIQUE COMMENT '实体编码',
    parent_item_code VARCHAR(100) COMMENT '父级实体编码',
    label_code VARCHAR(50) NOT NULL COMMENT '所属标签编码',
    description TEXT COMMENT '实体描述',
    is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (label_code) REFERENCES labels(label_code),
    FOREIGN KEY (parent_item_code) REFERENCES items(item_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实体数据表';

-- 4. 实体同义词表 (item_synonyms)
-- 存放实体的同义词
CREATE TABLE item_synonyms (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    item_code VARCHAR(100) NOT NULL COMMENT '关联的实体编码',
    synonym VARCHAR(200) NOT NULL COMMENT '同义词',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_item_synonym (item_code, synonym),
    FOREIGN KEY (item_code) REFERENCES items(item_code) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实体同义词表';

-- 5. 意图规则表 (intent_rules)
-- 存放用于意图识别的规则，每条规则被视为其意图标签下的一个“实体”
CREATE TABLE intent_rules (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '主键ID',
    rule_code VARCHAR(50) NOT NULL UNIQUE COMMENT '规则编码',
    rule_type VARCHAR(50) NOT NULL COMMENT '规则类型 (例如: keyword_whitelist, keyword_blacklist, expression, sentence)',
    rule_name TEXT NOT NULL COMMENT '规则名称 (规则的具体内容)',
    label_code VARCHAR(50) NOT NULL COMMENT '关联的意图标签编码',
    is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (label_code) REFERENCES labels(label_code) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='意图规则表';