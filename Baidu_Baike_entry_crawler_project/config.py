#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多线程爬虫配置文件
"""

import logging
import os

# =============================================================================
# 基本配置
# =============================================================================
PEOPLE_LIST_FILE = 'names.csv'  # 人名列表文件
OUTPUT_FILE = 'baike_data_multithreaded.csv'  # 输出文件
TEMP_JSON_FILE = None  # 临时JSON文件，None表示自动生成

# =============================================================================
# 多线程配置 - 临时优化以解决403问题
# =============================================================================
NUM_THREADS = 8  # 从20降至8，减少代理竞争压力
MAX_RETRIES_PER_NAME = 2  # 减少重试次数，避免过度消耗代理
BUFFER_SIZE = 100  # 数据缓冲区大小
PROGRESS_REPORT_INTERVAL = 30  # 进度报告间隔（秒）

# 动态代理池配置 - 针对代理不足问题优化
PROXY_POOL_SIZE = max(NUM_THREADS * 4, 32)  # 确保每线程至少4个代理
PROXY_BLOCK_RECOVERY_TIME = 600  # 代理被拦截后的恢复时间（10分钟）
PROXY_MAX_USAGE = 30  # 每个代理最大使用次数（降低避免过度使用）

# =============================================================================
# 请求配置 - 优化以应对百度反爬
# =============================================================================
REQUEST_TIMEOUT = 20  # 请求超时时间（秒）- 增加容错性
MIN_DELAY = 2.0  # 最小延迟（秒）- 增加以降低被封概率
MAX_DELAY = 4.0  # 最大延迟（秒）- 给百度更多缓冲时间

# =============================================================================
# 代理配置
# =============================================================================
PROXY_TIMEOUT = 5  # 获取代理超时时间（秒）

# =============================================================================
# 数据列配置
# =============================================================================
COLUMNS = [
    '中文名', '外文名', '别名', '性别', '国籍', '民族', '籍贯', '政治面貌',
    '出生日期', '毕业院校', '人物履历', '担任职务', '职业', '职称', '军衔晋升',
    '成就', '代表作品', '逝世日期', '个人生活', '家庭成员', '人物评价', 'status'
]

# =============================================================================
# 日志配置
# =============================================================================
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
LOG_FILE = 'multithreaded_scraper.log'

# =============================================================================
# 示例代理列表（请替换为您的真实代理）
# =============================================================================
SAMPLE_PROXY_LIST = [
    "127.0.0.1:8080",
    "127.0.0.1:8081",
    "127.0.0.1:8082",
    "127.0.0.1:8083",
    "127.0.0.1:8084",
]

# =============================================================================
# 性能优化配置
# =============================================================================
# 根据您的硬件配置调整这些参数

# CPU核心数相关
CPU_CORES = os.cpu_count()

# 推荐线程数计算
def get_recommended_threads(proxy_count):
    """根据代理数量推荐线程数"""
    return min(proxy_count, CPU_CORES * 2, 50)  # 最多50个线程

# 内存相关（MB）
MEMORY_BUFFER_SIZE = 500  # 内存缓冲区大小

# =============================================================================
# 错误处理配置
# =============================================================================
# 代理失效判断关键词
PROXY_ERROR_KEYWORDS = [
    'proxy', 'tunnel connection failed', 'connection refused',
    'cannot connect to proxy', 'proxy server is refusing connections',
    'max retries exceeded', 'connection aborted'
]

# HTTP错误状态码
PROXY_ERROR_STATUS_CODES = [407, 502, 503, 504]

# 页面错误关键词
PAGE_ERROR_KEYWORDS = [
    '404', 'page not found', '页面不存在', 'proxy error', '代理错误'
]

# 百度百科特征关键词
BAIKE_INDICATORS = [
    'baike.baidu.com', '百度百科', 'lemma-summary', 'basic-info'
]

# =============================================================================
# 动态配置函数
# =============================================================================
def get_optimal_config(proxy_count, target_names_count):
    """根据代理数量和目标数据量获取最优配置"""
    config = {
        'num_threads': get_recommended_threads(proxy_count),
        'buffer_size': max(50, min(200, target_names_count // 1000)),
        'progress_interval': 60 if target_names_count > 50000 else 30,
        'batch_save_size': max(10, min(100, target_names_count // 10000))
    }
    
    # 10W数据的特殊配置
    if target_names_count >= 100000:
        config.update({
            'num_threads': min(proxy_count, 30),  # 限制最大线程数
            'buffer_size': 200,  # 增大缓冲区
            'progress_interval': 120,  # 增加报告间隔
            'enable_checkpoint': True,  # 启用检查点保存
            'checkpoint_interval': 1000  # 每1000条数据保存检查点
        })
    
    return config

# =============================================================================
# 动态代理配置 (推荐用于大规模采集)
# =============================================================================
# 默认启用动态代理，不再依赖 proxy_list.txt 文件
ENABLE_DYNAMIC_PROXY = True  # 启用动态代理

# 动态代理API配置 - 快代理KDL配置
DYNAMIC_PROXY_CONFIG = {
    # 快代理API - 获取代理列表
    'url': 'http://v2.api.juliangip.com/company/dynamic/getips?auto_white=1&num=1&pt=1&result_type=json&trade_no=2016978334949568&sign=181afe2636ac6f3316e139448384cce4',
    'method': 'GET',
    'timeout': 15,
    
    # 响应解析配置 - 快代理JSON格式
    'parser': 'json',
    'proxy_field': 'data.proxy_list',  # 快代理的代理在 data.proxy_list 字段
    'format_template': '{}',  # 代理已经是 ip:port 格式，直接使用
    
    # 代理认证配置 - 基于你提供的示例
    'auth': {
        'type': 'url',  # 在URL中包含认证信息
        'username': 'd3323503634',  # 你的快代理用户名
        'password': '9ijy2jff',     # 你的快代理密码
        # 根据快代理文档，认证格式为: http://username:password@proxy_ip:proxy_port
        'proxy_format': 'http://{}:{}@{}',  # {username, password, proxy}
    },
    
    # 代理池配置 - 优化以应对代理不足问题
    'fetch_interval': 60,  # 1分钟刷新一次，保持代理新鲜度
    'initial_size': PROXY_POOL_SIZE,     # 动态代理池大小，应对多线程需求
    'max_retries': 5,       # 增加API请求重试次数
    
    # 请求头（保持简洁）
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # 注意：由于URL已包含所有参数，不需要额外的params字段
}

# 预设的动态代理配置模板
DYNAMIC_PROXY_TEMPLATES = {
    # 快代理API示例
    'kuaidaili': {
        'url': 'https://api.kdlapi.com/api/getproxy',
        'method': 'GET',
        'parser': 'json',
        'proxy_field': 'data',
        'format_template': '{ip}:{port}',
        'params': {
            'orderid': 'YOUR_ORDER_ID',
            'num': 30,
            'format': 'json'
        }
    },
    
    # 芝麻代理API示例
    'zhimahttp': {
        'url': 'http://webapi.http.zhimacangku.com/getip',
        'method': 'GET',
        'parser': 'json',
        'proxy_field': 'data',
        'format_template': '{ip}:{port}',
        'params': {
            'num': 30,
            'type': 2,
            'pro': 0,
            'city': 0,
            'yys': 0,
            'port': 1,
            'pack': 'YOUR_PACK_ID',
            'ts': 1,
            'ys': 1,
            'cs': 1,
            'lb': 1,
            'sb': 0,
            'pb': 4,
            'mr': 1
        }
    },
    
    # 文本格式API示例
    'text_api': {
        'url': 'https://api.proxy-list.com/txt',
        'method': 'GET',
        'parser': 'text',
        'fetch_interval': 300,
    }
}
