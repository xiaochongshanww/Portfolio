#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态代理获取器 - 支持通过API接口获取代理
"""

import requests
import json
import time
import threading
from typing import List, Dict, Optional
import logging

class DynamicProxyFetcher:
    """动态代理获取器"""
    
    def __init__(self, api_config: Dict):
        """
        初始化动态代理获取器
        
        Args:
            api_config: API配置字典，包含以下字段：
                - url: API接口地址
                - method: 请求方法 (GET/POST)
                - headers: 请求头 (可选)
                - params: 请求参数 (可选)
                - auth: 认证信息 (可选)
                - timeout: 超时时间 (默认10秒)
                - parser: 响应解析器类型 (json/text/custom)
        """
        self.api_config = api_config
        self.session = requests.Session()
        self.last_fetch_time = 0
        self.fetch_interval = api_config.get('fetch_interval', 60)  # 默认60秒获取一次
        self.max_retries = api_config.get('max_retries', 3)
        
        # 设置默认请求头
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        if 'headers' in api_config:
            default_headers.update(api_config['headers'])
        self.session.headers.update(default_headers)
    
    def fetch_proxies(self) -> List[str]:
        """从API获取代理列表"""
        for attempt in range(self.max_retries):
            try:
                # 发送请求
                response = self._make_request()
                
                if response.status_code == 200:
                    # 解析响应
                    proxies = self._parse_response(response)
                    
                    if proxies:
                        logging.info(f"成功获取 {len(proxies)} 个代理")
                        self.last_fetch_time = time.time()
                        return proxies
                    else:
                        logging.warning("API返回空的代理列表")
                else:
                    logging.error(f"API请求失败，状态码: {response.status_code}")
                
            except Exception as e:
                logging.error(f"获取代理失败 (尝试 {attempt + 1}): {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
        
        return []
    
    def _make_request(self) -> requests.Response:
        """发送API请求"""
        method = self.api_config.get('method', 'GET').upper()
        url = self.api_config['url']
        timeout = self.api_config.get('timeout', 10)
        
        if method == 'GET':
            # 如果URL中已经包含参数（如巨量IP的完整URL），则不再添加params
            params = self.api_config.get('params') if '?' not in url else None
            return self.session.get(
                url,
                params=params,
                timeout=timeout
            )
        elif method == 'POST':
            return self.session.post(
                url,
                data=self.api_config.get('data'),
                json=self.api_config.get('json'),
                timeout=timeout
            )
        else:
            raise ValueError(f"不支持的请求方法: {method}")
    
    def _parse_response(self, response: requests.Response) -> List[str]:
        """解析API响应"""
        parser_type = self.api_config.get('parser', 'json')
        
        if parser_type == 'json':
            return self._parse_json_response(response)
        elif parser_type == 'text':
            return self._parse_text_response(response)
        elif parser_type == 'custom':
            return self._parse_custom_response(response)
        else:
            raise ValueError(f"不支持的解析器类型: {parser_type}")
    
    def _parse_json_response(self, response: requests.Response) -> List[str]:
        """解析JSON格式的响应"""
        try:
            data = response.json()
            
            # 根据不同的JSON结构提取代理
            proxy_field = self.api_config.get('proxy_field', 'proxies')
            format_template = self.api_config.get('format_template', '{ip}:{port}')
            
            if isinstance(data, list):
                # 直接是代理列表
                proxies = []
                for item in data:
                    if isinstance(item, str):
                        proxies.append(item)
                    elif isinstance(item, dict):
                        proxy = format_template.format(**item)
                        proxies.append(proxy)
                return proxies
            
            elif isinstance(data, dict):
                # 支持嵌套字段（如 data.proxy_list）
                proxy_data = self._get_nested_field(data, proxy_field)
                
                if proxy_data is not None:
                    return self._extract_proxies_from_list(proxy_data, format_template)
                else:
                    # 尝试常见的字段名
                    common_fields = [
                        'data.proxy_list', 'data', 'result.proxies', 'result', 
                        'proxies', 'proxy_list', 'ips', 'list'
                    ]
                    for field in common_fields:
                        proxy_data = self._get_nested_field(data, field)
                        if proxy_data is not None:
                            return self._extract_proxies_from_list(proxy_data, format_template)
            
            logging.warning("无法从JSON响应中提取代理列表")
            return []
            
        except json.JSONDecodeError as e:
            logging.error(f"JSON解析失败: {e}")
            return []
    
    def _parse_text_response(self, response: requests.Response) -> List[str]:
        """解析文本格式的响应"""
        lines = response.text.strip().split('\n')
        proxies = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # 简单验证代理格式
                if ':' in line and len(line.split(':')) == 2:
                    proxies.append(line)
        
        return proxies
    
    def _parse_custom_response(self, response: requests.Response) -> List[str]:
        """自定义响应解析"""
        # 这里可以根据具体的API响应格式自定义解析逻辑
        custom_parser = self.api_config.get('custom_parser')
        if custom_parser and callable(custom_parser):
            return custom_parser(response)
        else:
            logging.error("未提供有效的自定义解析器")
            return []
    
    def _extract_proxies_from_list(self, proxy_list: List, format_template: str) -> List[str]:
        """从列表中提取代理"""
        proxies = []
        
        for item in proxy_list:
            try:
                if isinstance(item, str):
                    # 如果是字符串且已经是代理格式（如 "ip:port"），直接使用
                    if ':' in item and format_template in ['{}', '{0}']:
                        proxies.append(item)
                    else:
                        # 使用模板格式化
                        proxy = format_template.format(item)
                        proxies.append(proxy)
                elif isinstance(item, dict):
                    # 如果是字典，使用模板格式化
                    proxy = format_template.format(**item)
                    proxies.append(proxy)
            except (KeyError, ValueError) as e:
                logging.warning(f"格式化代理失败: {e}, 数据: {item}")
                continue
        
        return proxies
    
    def _get_nested_field(self, data: dict, field_path: str):
        """
        获取嵌套字段值
        
        Args:
            data: 字典数据
            field_path: 字段路径，如 'data.proxy_list' 或 'data'
        
        Returns:
            字段值或None
        """
        if not field_path:
            return None
        
        # 分割嵌套路径
        keys = field_path.split('.')
        current = data
        
        try:
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current
        except (TypeError, KeyError):
            return None

    def should_refresh(self) -> bool:
        """判断是否需要刷新代理"""
        return time.time() - self.last_fetch_time > self.fetch_interval

class DynamicProxyManager:
    """动态代理管理器"""
    
    def __init__(self, api_config: Dict, initial_size: int = 50):
        self.fetcher = DynamicProxyFetcher(api_config)
        self.proxy_pool = []
        self.failed_proxies = set()
        self.blocked_proxies = set()  # 被百度拦截的代理
        self.proxy_usage = {}
        self.proxy_block_time = {}
        self.lock = threading.RLock()
        self.initial_size = max(initial_size, 20)
        self.max_pool_size = initial_size * 3
        self.auto_refresh = True
        
        # 百度反爬相关参数
        self.block_recovery_time = 300  # 5分钟后重试被拦截的代理
        self.max_usage_per_proxy = 50   # 每个代理最大使用次数
        
        # 初始化代理池
        self._initialize_proxy_pool()
        
        # 启动自动刷新和恢复线程
        self._start_refresh_thread()
        self._start_recovery_thread()
    
    def _initialize_proxy_pool(self):
        """初始化代理池"""
        logging.info("正在初始化代理池...")
        
        # 多次获取以达到目标大小
        attempts = 0
        max_attempts = 5
        
        while len(self.proxy_pool) < self.initial_size and attempts < max_attempts:
            new_proxies = self.fetcher.fetch_proxies()
            if new_proxies:
                with self.lock:
                    # 去重并添加到代理池
                    for proxy in new_proxies:
                        if proxy not in self.proxy_pool:
                            self.proxy_pool.append(proxy)
                            self.proxy_usage[proxy] = 0
            attempts += 1
            if len(self.proxy_pool) < self.initial_size and attempts < max_attempts:
                time.sleep(2)  # 短暂等待后再次获取
        
        logging.info(f"代理池初始化完成，当前有 {len(self.proxy_pool)} 个代理")
    
    def get_proxy(self, timeout: int = 5) -> Optional[str]:
        """获取一个可用代理"""
        with self.lock:
            # 清理过度使用的代理
            self._cleanup_overused_proxies()
            
            # 过滤掉失效和被拦截的代理
            available_proxies = [
                p for p in self.proxy_pool 
                if p not in self.failed_proxies 
                and p not in self.blocked_proxies
                and self.proxy_usage.get(p, 0) < self.max_usage_per_proxy
            ]
            
            if not available_proxies:
                # 尝试恢复被拦截的代理
                self._try_recover_blocked_proxies()
                
                # 重新获取可用代理
                available_proxies = [
                    p for p in self.proxy_pool 
                    if p not in self.failed_proxies 
                    and p not in self.blocked_proxies
                    and self.proxy_usage.get(p, 0) < self.max_usage_per_proxy
                ]
                
                if not available_proxies:
                    logging.warning("没有可用代理，尝试刷新代理池")
                    self._refresh_proxy_pool()
                    
                    # 再次尝试获取代理
                    available_proxies = [
                        p for p in self.proxy_pool 
                        if p not in self.failed_proxies 
                        and p not in self.blocked_proxies
                        and self.proxy_usage.get(p, 0) < self.max_usage_per_proxy
                    ]
                    
                    if not available_proxies:
                        logging.error("无法获取可用代理")
                        return None
            
            # 选择使用次数最少的代理
            proxy = min(available_proxies, key=lambda p: self.proxy_usage.get(p, 0))
            self.proxy_usage[proxy] = self.proxy_usage.get(proxy, 0) + 1
            
            return proxy
    
    def mark_proxy_failed(self, proxy: str):
        """标记代理失效"""
        with self.lock:
            self.failed_proxies.add(proxy)
            logging.warning(f"代理 {proxy} 已标记为失效")
            
            # 如果失效代理过多，尝试刷新
            available_count = len(self.proxy_pool) - len(self.failed_proxies)
            if available_count < len(self.proxy_pool) * 0.3:
                logging.info("可用代理不足，触发代理池刷新")
                self._refresh_proxy_pool()
    
    def mark_proxy_success(self, proxy: str):
        """标记代理成功"""
        with self.lock:
            if proxy in self.failed_proxies:
                self.failed_proxies.remove(proxy)
                logging.info(f"代理 {proxy} 恢复正常")
    
    def mark_proxy_blocked(self, proxy: str):
        """标记代理被百度拦截（403 Forbidden）"""
        with self.lock:
            self.blocked_proxies.add(proxy)
            self.proxy_block_time[proxy] = time.time()
            logging.warning(f"代理 {proxy} 被百度拦截（403），将在 {self.block_recovery_time} 秒后重试")
    
    def _try_recover_blocked_proxies(self):
        """尝试恢复被拦截的代理"""
        current_time = time.time()
        recovered = []
        
        for proxy in list(self.blocked_proxies):
            block_time = self.proxy_block_time.get(proxy, 0)
            if current_time - block_time > self.block_recovery_time:
                self.blocked_proxies.discard(proxy)
                self.proxy_block_time.pop(proxy, None)
                # 重置使用计数给代理一个新的机会
                self.proxy_usage[proxy] = 0
                recovered.append(proxy)
        
        if recovered:
            logging.info(f"恢复 {len(recovered)} 个被拦截的代理")
    
    def _cleanup_overused_proxies(self):
        """清理过度使用的代理"""
        overused = [
            proxy for proxy, count in self.proxy_usage.items()
            if count >= self.max_usage_per_proxy
        ]
        
        if overused:
            logging.info(f"发现 {len(overused)} 个过度使用的代理，将暂时移除")
            for proxy in overused:
                self.blocked_proxies.add(proxy)
                self.proxy_block_time[proxy] = time.time()
    
    def _refresh_proxy_pool(self):
        """刷新代理池"""
        try:
            new_proxies = self.fetcher.fetch_proxies()
            
            if new_proxies:
                with self.lock:
                    # 保留一些旧的可用代理
                    old_available = [p for p in self.proxy_pool if p not in self.failed_proxies]
                    
                    # 合并新旧代理，去重
                    all_proxies = list(set(new_proxies + old_available))
                    
                    # 更新代理池
                    self.proxy_pool = all_proxies[:self.max_pool_size]
                    
                    # 清理失效标记中不存在的代理
                    self.failed_proxies = {p for p in self.failed_proxies if p in self.proxy_pool}
                    
                    # 初始化新代理的使用计数
                    for proxy in new_proxies:
                        if proxy not in self.proxy_usage:
                            self.proxy_usage[proxy] = 0
                    
                    logging.info(f"代理池刷新完成，当前有 {len(self.proxy_pool)} 个代理")
            else:
                logging.error("获取新代理失败")
                
        except Exception as e:
            logging.error(f"刷新代理池失败: {e}")
    
    def _start_refresh_thread(self):
        """启动自动刷新线程"""
        def refresh_worker():
            while self.auto_refresh:
                if self.fetcher.should_refresh():
                    self._refresh_proxy_pool()
                time.sleep(30)  # 每30秒检查一次
        
        self.refresh_thread = threading.Thread(target=refresh_worker, daemon=True)
        self.refresh_thread.start()
        logging.info("代理自动刷新线程已启动")
    
    def _start_recovery_thread(self):
        """启动代理恢复线程"""
        def recovery_worker():
            while self.auto_refresh:
                self._try_recover_blocked_proxies()
                time.sleep(60)  # 每分钟检查一次恢复
        
        recovery_thread = threading.Thread(target=recovery_worker, daemon=True)
        recovery_thread.start()
        logging.info("代理恢复线程已启动")
    
    def stop_auto_refresh(self):
        """停止自动刷新"""
        self.auto_refresh = False
        if hasattr(self, 'refresh_thread'):
            self.refresh_thread.join(timeout=5)
    
    def get_stats(self) -> Dict:
        """获取代理池统计信息"""
        with self.lock:
            available_count = len([
                p for p in self.proxy_pool 
                if p not in self.failed_proxies 
                and p not in self.blocked_proxies
                and self.proxy_usage.get(p, 0) < self.max_usage_per_proxy
            ])
            
            return {
                'total_proxies': len(self.proxy_pool),
                'failed_proxies': len(self.failed_proxies),
                'blocked_proxies': len(self.blocked_proxies),
                'available_proxies': available_count,
                'overused_proxies': len([p for p, c in self.proxy_usage.items() if c >= self.max_usage_per_proxy]),
                'usage_stats': self.proxy_usage.copy(),
                'last_refresh': self.fetcher.last_fetch_time
            }


# 预定义的API配置模板
API_CONFIG_TEMPLATES = {
    # 示例1: 简单的JSON API
    'simple_json': {
        'url': 'https://api.example.com/proxies',
        'method': 'GET',
        'parser': 'json',
        'proxy_field': 'data',
        'format_template': '{ip}:{port}',
        'fetch_interval': 300,  # 5分钟刷新一次
    },
    
    # 示例2: 需要认证的API
    'auth_api': {
        'url': 'https://api.proxy-service.com/get',
        'method': 'GET',
        'headers': {
            'Authorization': 'Bearer YOUR_API_TOKEN'
        },
        'params': {
            'count': 50,
            'format': 'json'
        },
        'parser': 'json',
        'format_template': '{host}:{port}',
        'fetch_interval': 600,  # 10分钟刷新一次
    },
    
    # 示例3: 文本格式API
    'text_api': {
        'url': 'https://api.proxy-list.com/txt',
        'method': 'GET',
        'parser': 'text',
        'fetch_interval': 300,
    }
}

def create_dynamic_proxy_manager(api_type: str, **kwargs) -> DynamicProxyManager:
    """
    创建动态代理管理器的便捷函数
    
    Args:
        api_type: API类型 ('simple_json', 'auth_api', 'text_api' 或 'custom')
        **kwargs: 额外的配置参数
    
    Returns:
        DynamicProxyManager实例
    """
    if api_type == 'custom':
        api_config = kwargs
    else:
        if api_type not in API_CONFIG_TEMPLATES:
            raise ValueError(f"不支持的API类型: {api_type}")
        
        api_config = API_CONFIG_TEMPLATES[api_type].copy()
        api_config.update(kwargs)
    
    return DynamicProxyManager(api_config)

# class EnhancedProxyPool:
    """增强版代理池，支持动态获取、失效检测、百度反爬检测"""
    
    def __init__(self, api_config: Dict, initial_size: int = 20):
        """初始化增强版代理池"""
        self.fetcher = DynamicProxyFetcher(api_config)
        self.proxy_pool = []
        self.failed_proxies = set()  # 失效的代理
        self.blocked_proxies = set()  # 被百度拦截的代理
        self.proxy_usage = {}  # 代理使用次数统计
        self.proxy_create_time = {}  # 记录代理获取时间
        self.proxy_block_time = {}  # 记录代理被拦截的时间
        self.lock = threading.RLock()
        self.initial_size = max(initial_size, 20)  # 确保最小代理池大小
        self.max_pool_size = initial_size * 3  # 最大代理池大小
        self.auto_refresh = True
        
        # 百度反爬和代理生命周期相关参数
        self.block_recovery_time = 600  # 10分钟后重试被拦截的代理（但一般不会用到）
        self.max_usage_per_proxy = 300   # 每个代理最大使用次数，设置更合理的阈值
        self.proxy_lifetime = 180  # 代理生命周期：3分钟（180秒）
        
        # 初始化代理池
        self._initialize_proxy_pool()
        
        # 启动自动刷新和恢复线程
        self._start_refresh_thread()
        self._start_recovery_thread()
    
    def _initialize_proxy_pool(self):
        """初始化代理池"""
        logging.info("正在初始化代理池...")
        
        # 多次获取以填充代理池
        target_size = self.initial_size
        attempts = 0
        max_attempts = min(target_size, 10)  # 限制获取次数
        
        while len(self.proxy_pool) < target_size and attempts < max_attempts:
            proxies = self.fetcher.fetch_proxies()
            if proxies:
                current_time = time.time()
                with self.lock:
                    for proxy in proxies:
                        if proxy not in self.proxy_pool:
                            self.proxy_pool.append(proxy)
                            self.proxy_usage[proxy] = 0
                            self.proxy_create_time[proxy] = current_time  # 记录创建时间
                    
                    # 避免重复添加
                    self.proxy_pool = list(set(self.proxy_pool))
            
            attempts += 1
            if len(self.proxy_pool) < target_size:
                time.sleep(1)  # 短暂等待避免API过于频繁
        
        logging.info(f"代理池初始化完成，当前有 {len(self.proxy_pool)} 个代理")
        
        # 启动自动刷新和恢复线程
        if self.auto_refresh:
            self._start_refresh_thread()
            self._start_recovery_thread()
    
    def get_proxy(self, timeout: int = 5) -> Optional[str]:
        """获取一个可用代理"""
        with self.lock:
            # 清理过度使用的代理
            self._cleanup_overused_proxies()
            
            # 过滤掉失效和被拦截的代理
            available_proxies = [
                p for p in self.proxy_pool 
                if p not in self.failed_proxies 
                and p not in self.blocked_proxies
                and self.proxy_usage.get(p, 0) < self.max_usage_per_proxy
            ]
            
            if not available_proxies:
                # 尝试恢复被拦截的代理
                self._try_recover_blocked_proxies()
                
                # 重新获取可用代理
                available_proxies = [
                    p for p in self.proxy_pool 
                    if p not in self.failed_proxies 
                    and p not in self.blocked_proxies
                    and self.proxy_usage.get(p, 0) < self.max_usage_per_proxy
                ]
                
                if not available_proxies:
                    logging.warning("没有可用代理，尝试刷新代理池")
                    self._refresh_proxy_pool()
                    
                    # 再次尝试获取代理
                    available_proxies = [
                        p for p in self.proxy_pool 
                        if p not in self.failed_proxies 
                        and p not in self.blocked_proxies
                        and self.proxy_usage.get(p, 0) < self.max_usage_per_proxy
                    ]
                    
                    if not available_proxies:
                        logging.error("无法获取可用代理")
                        return None
            
            # 选择使用次数最少的代理
            proxy = min(available_proxies, key=lambda p: self.proxy_usage.get(p, 0))
            self.proxy_usage[proxy] = self.proxy_usage.get(proxy, 0) + 1
            
            # 添加认证信息（如果需要）
            proxy_with_auth = self._format_proxy_with_auth(proxy)
            
            return proxy_with_auth
    
    def mark_proxy_failed(self, proxy: str):
        """标记代理失效"""
        with self.lock:
            self.failed_proxies.add(proxy)
            logging.warning(f"代理 {proxy} 标记为失效")
            
            # 如果失效代理过多，尝试刷新
            available_count = len(self.proxy_pool) - len(self.failed_proxies)
            if available_count < len(self.proxy_pool) * 0.3:  # 可用代理少于30%
                logging.info("可用代理不足，触发代理池刷新")
                self._refresh_proxy_pool()
    
    def mark_proxy_success(self, proxy: str):
        """标记代理成功"""
        with self.lock:
            if proxy in self.failed_proxies:
                self.failed_proxies.remove(proxy)
                logging.info(f"代理 {proxy} 恢复正常")
    
    def mark_proxy_blocked(self, proxy: str):
        """标记代理被百度拦截（403 Forbidden）"""
        with self.lock:
            self.blocked_proxies.add(proxy)
            self.proxy_block_time[proxy] = time.time()
            logging.warning(f"代理 {proxy} 被百度拦截（403），将在 {self.block_recovery_time} 秒后重试")
    
    def _try_recover_blocked_proxies(self):
        """尝试恢复被拦截的代理"""
        current_time = time.time()
        recovered = []
        
        for proxy in list(self.blocked_proxies):
            block_time = self.proxy_block_time.get(proxy, 0)
            if current_time - block_time > self.block_recovery_time:
                self.blocked_proxies.discard(proxy)
                self.proxy_block_time.pop(proxy, None)
                # 重置使用计数给代理一个新的机会
                self.proxy_usage[proxy] = 0
                recovered.append(proxy)
        
        if recovered:
            logging.info(f"恢复 {len(recovered)} 个被拦截的代理")
    
    def _cleanup_expired_proxies(self):
        """清理过期的代理"""
        current_time = time.time()
        expired = [
            proxy for proxy, create_time in self.proxy_create_time.items()
            if (current_time - create_time) >= self.proxy_lifetime
        ]
        
        if expired:
            logging.info(f"发现 {len(expired)} 个过期代理，将移除")
            for proxy in expired:
                # 从代理池中移除
                if proxy in self.proxy_pool:
                    self.proxy_pool.remove(proxy)
                # 清理相关记录
                self.proxy_usage.pop(proxy, None)
                self.proxy_create_time.pop(proxy, None)
                self.failed_proxies.discard(proxy)
                self.blocked_proxies.discard(proxy)
                self.proxy_block_time.pop(proxy, None)

    def _cleanup_overused_proxies(self):
        """清理过度使用的代理 - 修复统计问题"""
        overused = [
            proxy for proxy, count in self.proxy_usage.items()
            if count >= self.max_usage_per_proxy
        ]
        
        if overused:
            logging.info(f"发现 {len(overused)} 个过度使用的代理，将移除并刷新")
            for proxy in overused:
                # 直接从代理池中移除，而不是加入blocked_proxies
                if proxy in self.proxy_pool:
                    self.proxy_pool.remove(proxy)
                # 清理相关记录
                self.proxy_usage.pop(proxy, None)
                self.proxy_create_time.pop(proxy, None)
                self.failed_proxies.discard(proxy)
                self.blocked_proxies.discard(proxy)
                self.proxy_block_time.pop(proxy, None)
    
    def _refresh_proxy_pool(self):
        """刷新代理池"""
        try:
            new_proxies = self.fetcher.fetch_proxies()
            
            if new_proxies:
                with self.lock:
                    # 保留一些旧的可用代理
                    old_available = [p for p in self.proxy_pool if p not in self.failed_proxies]
                    
                    # 合并新旧代理，去重
                    all_proxies = list(set(new_proxies + old_available))
                    
                    # 更新代理池
                    self.proxy_pool = all_proxies[:self.initial_size * 2]  # 适当扩容
                    
                    # 清理失效标记中不存在的代理
                    self.failed_proxies = {p for p in self.failed_proxies if p in self.proxy_pool}
                    
                    # 初始化新代理的使用计数
                    for proxy in new_proxies:
                        if proxy not in self.proxy_usage:
                            self.proxy_usage[proxy] = 0
                    
                    logging.info(f"代理池刷新完成，当前有 {len(self.proxy_pool)} 个代理")
            else:
                logging.error("获取新代理失败")
                
        except Exception as e:
            logging.error(f"刷新代理池失败: {e}")
    
    def _start_refresh_thread(self):
        """启动自动刷新线程"""
        def refresh_worker():
            while self.auto_refresh:
                if self.fetcher.should_refresh():
                    self._refresh_proxy_pool()
                time.sleep(30)  # 每30秒检查一次
        
        self.refresh_thread = threading.Thread(target=refresh_worker, daemon=True)
        self.refresh_thread.start()
        logging.info("代理自动刷新线程已启动")
    
    def _start_recovery_thread(self):
        """启动代理恢复线程"""
        def recovery_worker():
            while self.auto_refresh:
                try:
                    self._try_recover_blocked_proxies()
                    time.sleep(60)  # 每60秒检查一次恢复
                except Exception as e:
                    logging.error(f"代理恢复线程错误: {e}")
                    time.sleep(30)  # 出错后等待30秒再试
        
        self.recovery_thread = threading.Thread(target=recovery_worker, daemon=True)
        self.recovery_thread.start()
        logging.info("代理恢复线程已启动")

    def stop_auto_refresh(self):
        """停止自动刷新"""
        self.auto_refresh = False
        if self.refresh_thread:
            self.refresh_thread.join(timeout=5)
        if self.recovery_thread:
            self.recovery_thread.join(timeout=5)
    
    def get_stats(self) -> Dict:
        """获取代理池统计信息"""
        with self.lock:
            return {
                'total_proxies': len(self.proxy_pool),
                'failed_proxies': len(self.failed_proxies),
                'available_proxies': len(self.proxy_pool) - len(self.failed_proxies),
                'usage_stats': self.proxy_usage.copy(),
                'last_refresh': self.fetcher.last_fetch_time
            }
