#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多线程百度百科爬虫 - 支持10W级别数据采集
支持静态代理和动态代理两种模式
"""

import threading
import queue
import time
import random
import json
import pandas as pd
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, RLock
from collections import deque
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import os
import logging

# 导入文本清理库
try:
    import ftfy
    FTFY_AVAILABLE = True
except ImportError:
    FTFY_AVAILABLE = False
    logging.warning("ftfy库未安装，文本清理功能将使用简化版本")

# 导入动态代理管理器
try:
    from dynamic_proxy import DynamicProxyManager
    DYNAMIC_PROXY_AVAILABLE = True
except ImportError:
    DYNAMIC_PROXY_AVAILABLE = False
    logging.warning("dynamic_proxy.py 未找到，仅支持静态代理模式")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(filename)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class ThreadSafeProxyManager:
    """线程安全的代理管理器"""
    
    def __init__(self, proxy_list):
        self.proxy_list = proxy_list
        self.proxy_queue = queue.Queue()
        self.failed_proxies = set()
        self.lock = RLock()
        self.proxy_usage_count = {}
        self.proxy_success_count = {}
        
        # 初始化代理队列
        for proxy in proxy_list:
            self.proxy_queue.put(proxy)
            self.proxy_usage_count[proxy] = 0
            self.proxy_success_count[proxy] = 0
    
    def get_proxy(self, timeout=5):
        """获取可用代理"""
        try:
            proxy = self.proxy_queue.get(timeout=timeout)
            with self.lock:
                self.proxy_usage_count[proxy] += 1
            return proxy
        except queue.Empty:
            return None
    
    def return_proxy(self, proxy):
        """归还代理到队列"""
        with self.lock:
            if proxy not in self.failed_proxies:
                self.proxy_queue.put(proxy)
    
    def mark_proxy_failed(self, proxy):
        """标记代理失效"""
        with self.lock:
            self.failed_proxies.add(proxy)
            logging.warning(f"代理 {proxy} 已标记为失效")
    
    def mark_proxy_success(self, proxy):
        """标记代理成功"""
        with self.lock:
            self.proxy_success_count[proxy] += 1
            if proxy in self.failed_proxies:
                self.failed_proxies.remove(proxy)
                logging.info(f"代理 {proxy} 恢复正常")
    
    def get_stats(self):
        """获取代理统计信息"""
        with self.lock:
            return {
                'total_proxies': len(self.proxy_list),
                'failed_proxies': len(self.failed_proxies),
                'available_proxies': self.proxy_queue.qsize(),
                'usage_stats': self.proxy_usage_count.copy(),
                'success_stats': self.proxy_success_count.copy()
            }

class ThreadSafeDataManager:
    """线程安全的数据管理器 - 改进版本，分离存储原始数据和映射数据"""
    
    def __init__(self, output_file, temp_file=None, raw_data_file=None):
        self.output_file = output_file  # CSV文件 - 存储映射后的标准化数据
        self.temp_file = temp_file or f"temp_data_{int(time.time())}.json"  # 临时JSON文件
        self.raw_data_file = raw_data_file or f"raw_data_{time.strftime('%Y-%m-%d_%H_%M_%S')}.json"  # 原始数据JSON文件
        self.processed_names = set()
        self.data_buffer = []  # 存储映射后的数据
        self.raw_data_buffer = []  # 存储原始数据
        self.lock = RLock()
        self.buffer_size = 100  # 缓冲区大小
        
        # 加载已处理的数据
        self._load_processed_names()
        
        # 初始化文件
        self._init_temp_file()
        self._init_raw_data_file()
    
    def _load_processed_names(self):
        """加载已处理的名字"""
        if os.path.exists(self.output_file):
            try:
                df = pd.read_csv(self.output_file)
                self.processed_names = set(df['中文名'].dropna())
                logging.info(f"加载了 {len(self.processed_names)} 个已处理的名字")
            except Exception as e:
                logging.error(f"加载已处理数据失败: {e}")
    
    def _init_temp_file(self):
        """初始化临时JSON文件"""
        if not os.path.exists(self.temp_file):
            with open(self.temp_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False)
    
    def _init_raw_data_file(self):
        """初始化原始数据JSON文件"""
        if not os.path.exists(self.raw_data_file):
            with open(self.raw_data_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False)
            logging.info(f"创建原始数据文件: {self.raw_data_file}")
    
    def is_processed(self, name):
        """检查是否已处理"""
        with self.lock:
            return name in self.processed_names
    
    def add_data(self, name, mapped_data, raw_data=None):
        """添加数据到缓冲区 - 支持原始数据和映射数据分离存储"""
        with self.lock:
            self.processed_names.add(name)
            
            # 存储映射后的标准化数据（用于CSV）
            self.data_buffer.append({'name': name, 'data': mapped_data})
            
            # 存储原始提取数据（用于后续重新处理）
            if raw_data:
                self.raw_data_buffer.append({
                    'name': name,
                    'url': f"https://baike.baidu.com/item/{name}",
                    'extraction_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'raw_fields': raw_data,
                    'mapped_status': mapped_data.get('status', '未知')
                })
            
            # 当缓冲区满时，批量写入
            if len(self.data_buffer) >= self.buffer_size:
                self._flush_buffer()
    
    def _flush_buffer(self):
        """刷新缓冲区到文件 - 支持多文件存储"""
        if not self.data_buffer:
            return
        
        try:
            # 1. 保存映射数据到CSV
            # 添加调试信息
            logging.debug(f"缓冲区内容类型: {[type(item) for item in self.data_buffer]}")
            if self.data_buffer:
                sample_item = self.data_buffer[0]
                logging.debug(f"样本数据: {sample_item}")
                if 'data' in sample_item:
                    logging.debug(f"样本数据类型: {type(sample_item['data'])}")
                    
            # 创建DataFrame
            data_for_df = []
            for item in self.data_buffer:
                if isinstance(item, dict) and 'data' in item:
                    data_for_df.append(item['data'])
                else:
                    logging.error(f"数据项格式错误: {item}")
                    
            df_new = pd.DataFrame(data_for_df)
            header = not os.path.exists(self.output_file)
            df_new.to_csv(self.output_file, mode='a', index=False, 
                         header=header, encoding='utf_8_sig')
            logging.info(f"批量保存 {len(self.data_buffer)} 条映射数据到CSV")
            
            # 2. 保存映射数据到临时JSON（向后兼容）
            with open(self.temp_file, 'r+', encoding='utf-8') as f:
                existing_data = json.load(f)
                existing_data.extend(self.data_buffer)
                f.seek(0)
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
                f.truncate()
            
            # 3. 保存原始数据到专用JSON文件
            if self.raw_data_buffer:
                with open(self.raw_data_file, 'r+', encoding='utf-8') as f:
                    existing_raw_data = json.load(f)
                    # 使用字典结构，键为人名，便于查找
                    for item in self.raw_data_buffer:
                        existing_raw_data[item['name']] = item
                    f.seek(0)
                    json.dump(existing_raw_data, f, ensure_ascii=False, indent=2)
                    f.truncate()
                logging.info(f"批量保存 {len(self.raw_data_buffer)} 条原始数据到JSON")
                self.raw_data_buffer.clear()
            
            self.data_buffer.clear()
            
        except Exception as e:
            logging.error(f"保存数据失败: {e}")
    
    def force_flush(self):
        """强制刷新所有缓冲数据"""
        with self.lock:
            self._flush_buffer()
    
    def get_progress(self, total_names):
        """获取进度信息"""
        with self.lock:
            return {
                'processed': len(self.processed_names),
                'total': total_names,
                'percentage': len(self.processed_names) / total_names * 100,
                'buffer_size': len(self.data_buffer)
            }
    
    def get_raw_data_file(self):
        """获取原始数据文件路径"""
        return self.raw_data_file
    
    def load_raw_data(self, name=None):
        """加载原始数据，支持按人名查询"""
        try:
            with open(self.raw_data_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                if name:
                    return raw_data.get(name)
                return raw_data
        except Exception as e:
            logging.error(f"加载原始数据失败: {e}")
            return {} if name else None

class WorkerThread:
    """工作线程类"""
    
    def __init__(self, thread_id, proxy_manager, data_manager, scraper_instance):
        self.thread_id = thread_id
        self.proxy_manager = proxy_manager
        self.data_manager = data_manager
        self.scraper = scraper_instance
        self.session = requests.Session()
        self.success_count = 0
        self.failure_count = 0
        
        # 设置请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',  # 不包含br，避免Brotli压缩问题
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def scrape_single_person(self, name, max_retries=3):
        """爬取单个人物信息"""
        for attempt in range(max_retries):
            proxy = self.proxy_manager.get_proxy()
            if not proxy:
                logging.warning(f"线程 {self.thread_id}: 无可用代理")
                time.sleep(random.uniform(1, 3))
                continue
            
            try:
                # 设置代理
                proxies = {
                    'http': f'http://{proxy}',
                    'https': f'http://{proxy}'
                }
                
                # 发送请求
                url = f"https://baike.baidu.com/item/{name}"
                response = self.session.get(url, proxies=proxies, timeout=15)
                response.raise_for_status()
                
                # 验证响应
                if not self._is_valid_response(response):
                    raise Exception("无效响应")
                
                # 解析数据 - 使用增强版多义词处理
                soup = BeautifulSoup(response.text, 'lxml')
                person_data, raw_data = self._extract_person_data(soup, name)
                
                # 保存数据（包含原始数据）
                self.data_manager.add_data(name, person_data, raw_data)
                
                # 标记代理成功
                self.proxy_manager.mark_proxy_success(proxy)
                
                # 对于静态代理，需要归还代理
                if hasattr(self.proxy_manager, 'return_proxy'):
                    self.proxy_manager.return_proxy(proxy)
                
                self.success_count += 1
                return person_data
                
            except Exception as e:
                error_msg = str(e).lower()
                should_mark_proxy_failed = False
                error_category = "unknown"
                
                # 精确的代理相关错误 (确实应该标记代理失效)
                proxy_error_patterns = [
                    'proxyerror', 'proxy error', 'proxy.*failed',
                    'connection.*refused', 'network.*unreachable',
                    'remotedisconnected', 'connection.*reset', 'connection.*aborted',
                    'read.*timeout', 'connect.*timeout', 'socket.*timeout',
                    'tunnel.*connection.*failed', 'proxy.*connection.*failed'
                ]
                
                # 百度百科正常响应或内容问题 (不应标记代理失效)
                content_issues_patterns = [
                    '404.*client.*error', '404.*not.*found', 'not.*found',
                    '页面不存在', '页面未找到', '词条不存在',
                    'invalid.*response', '无效响应', '响应过短', '响应包含乱码',
                    'html.*parse.*error', 'empty.*response'
                ]
                
                # HTTP服务器问题 (可能是百度服务器问题，不应标记代理失效)
                server_issues_patterns = [
                    '500.*internal.*server.*error', '502.*bad.*gateway',
                    '503.*service.*unavailable', '504.*gateway.*timeout',
                    '429.*too.*many.*requests'
                ]
                
                # 百度反爬或安全检查 (不应标记代理失效，但需要注意)
                baidu_blocking_patterns = [
                    '百度安全中心', '验证码', '安全验证', '请完成以下操作',
                    'access.*denied', 'forbidden', 'captcha', 'robot.*check'
                ]
                
                # 程序错误 (不应标记代理失效)
                program_error_patterns = [
                    'attributeerror', 'object.*has.*no.*attribute',
                    'keyerror', 'indexerror', 'typeerror', 'valueerror',
                    'list.*indices.*must.*be.*integers'
                ]
                
                # 按优先级进行错误分类
                import re
                if any(re.search(pattern, error_msg) for pattern in proxy_error_patterns):
                    should_mark_proxy_failed = True
                    error_category = "proxy_connection"
                elif any(re.search(pattern, error_msg) for pattern in baidu_blocking_patterns):
                    should_mark_proxy_failed = False
                    error_category = "baidu_blocking"
                    # 特殊处理：403错误标记代理被百度拦截
                    if '403' in error_msg and 'forbidden' in error_msg:
                        if hasattr(self.proxy_manager, 'mark_proxy_blocked'):
                            self.proxy_manager.mark_proxy_blocked(proxy)
                        logging.warning(f"代理 {proxy} 被百度拦截(403)，已标记暂时不可用")
                elif any(re.search(pattern, error_msg) for pattern in content_issues_patterns):
                    should_mark_proxy_failed = False
                    error_category = "content_issues"
                elif any(re.search(pattern, error_msg) for pattern in server_issues_patterns):
                    should_mark_proxy_failed = False
                    error_category = "server_issues"
                elif any(re.search(pattern, error_msg) for pattern in baidu_blocking_patterns):
                    should_mark_proxy_failed = False
                    error_category = "baidu_blocking"
                elif any(re.search(pattern, error_msg) for pattern in program_error_patterns):
                    should_mark_proxy_failed = False
                    error_category = "program_error"
                else:
                    # 未分类错误，默认不标记代理失效（保守策略）
                    should_mark_proxy_failed = False
                    error_category = "uncategorized"
                    logging.warning(f"未分类错误 [{error_category}]: {e}")
                
                # 执行代理失效标记或归还
                if should_mark_proxy_failed:
                    self.proxy_manager.mark_proxy_failed(proxy)
                    logging.warning(f"代理失效 [{error_category}]: {proxy} - {str(e)[:100]}")
                else:
                    # 对于非代理问题，归还代理供其他线程使用
                    if hasattr(self.proxy_manager, 'return_proxy'):
                        self.proxy_manager.return_proxy(proxy)
                    logging.debug(f"非代理问题 [{error_category}]: {str(e)[:100]}")
                
                logging.error(f"线程 {self.thread_id} 爬取 '{name}' 失败 (尝试 {attempt+1}) [{error_category}]: {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(1, 2))
                continue
        
        self.failure_count += 1
        return None
    
    def _is_valid_response(self, response):
        """验证响应是否有效 - 增强版本"""
        try:
            text = response.text
        except Exception as e:
            logging.error(f"响应解码失败: {e}")
            return False
        
        # 检查响应状态码
        if response.status_code != 200:
            logging.debug(f"响应状态码异常: {response.status_code}")
            return False
        
        # 基本长度检查
        if len(text) < 500:
            logging.debug(f"响应过短: {len(text)} 字符")
            return False
        
        # 检查是否为乱码或压缩内容
        if any(ord(char) > 127 for char in text[:100]):
            logging.debug("响应包含乱码或未正确解码")
            return False
        
        # 检查是否为错误页面
        error_patterns = [
            r'\b404\s+(not\s+found|page\s+not\s+found|错误|页面不存在)',  # 404相关错误，但排除URL中的数字
            r'页面不存在', r'页面未找到', r'not\s+found',
            r'proxy\s+error', r'代理错误', r'connection\s+error',
            r'服务器错误', r'网络错误', r'timeout',
            r'百度安全中心', r'验证码', r'安全验证',
            r'请完成以下操作', r'access\s+denied'
        ]
        
        text_lower = text.lower()
        for pattern in error_patterns:
            if re.search(pattern, text_lower):
                logging.debug(f"响应包含错误模式: {pattern}")
                return False
        
        # 检查百度百科特征 - 更全面的检查
        baike_indicators = [
            'baike.baidu.com', '百度百科', 'lemma-summary', 
            'basic-info', 'basicInfo', '基本信息',
            'lemma-title', '词条', 'baike-header', 'lemma-main'
        ]
        
        if any(indicator in text for indicator in baike_indicators):
            return True
        
        # 如果没有明显的百度百科特征，检查是否包含HTML结构
        if '<html' in text_lower and '</html>' in text_lower:
            logging.debug("响应为HTML但不是百度百科页面")
            return False
        
        logging.debug("响应验证失败：未识别为有效百度百科页面")
        return False
    
    def _extract_person_data(self, soup, name):
        """提取人物数据 - 返回原始数据和映射数据"""
        # 检查是否为未收录页面
        if self._is_unrecorded_person(soup):
            raw_data = {'页面类型': '未收录页面', 'html_length': len(str(soup))}
            mapped_data = self._map_extracted_fields({}, name)
            mapped_data['status'] = '百度百科尚未收录'
            return mapped_data, raw_data
        
        # 检查是否为安全验证页面
        if self._is_safety_check_page(soup):
            raw_data = {'页面类型': '安全验证页面', 'html_length': len(str(soup))}
            mapped_data = self._map_extracted_fields({}, name)
            mapped_data['status'] = '触发安全验证'
            return mapped_data, raw_data
            
        # 检查是否为多义词页面
        if self._is_polysemous(soup):
            raw_data = {'页面类型': '多义词页面', 'html_length': len(str(soup))}
            mapped_data = self._map_extracted_fields({}, name)
            mapped_data['status'] = '多义词页面'
            return mapped_data, raw_data
        
        # 提取基本信息
        try:
            basic_info = self._get_basic_info_block(soup)
            
            # 构建原始数据 - 保留所有提取到的字段
            raw_data = {
                '页面类型': '正常人物页面',
                'html_length': len(str(soup)),
                'extraction_fields_count': len(basic_info),
                'raw_basic_info': basic_info.copy(),  # 保留原始字段名和值
                'all_extracted_keys': list(basic_info.keys()) if basic_info else []
            }
            
            # 映射到标准字段
            mapped_data = self._map_extracted_fields(basic_info, name)
            mapped_data['status'] = '成功'
            
            # 记录成功提取的字段数量
            extracted_fields = len([v for v in basic_info.values() if v and str(v).strip()])
            logging.debug(f"成功提取 {name} 的 {extracted_fields} 个字段")
            
            return mapped_data, raw_data
            
        except Exception as e:
            logging.error(f"提取 {name} 数据失败: {e}")
            raw_data = {
                '页面类型': '提取失败',
                'error_message': str(e),
                'html_length': len(str(soup))
            }
            mapped_data = self._map_extracted_fields({}, name)
            mapped_data['status'] = f'提取失败: {str(e)}'
            return mapped_data, raw_data
    
    def _is_unrecorded_person(self, soup):
        """检查是否有"未收录"字样"""
        text = soup.get_text()
        return '百度百科尚未收录' in text or '百度百科尚未收录词条' in text
    
    def _is_safety_check_page(self, soup):
        """判断页面是否为安全验证界面"""
        text = soup.get_text()
        keywords = ['百度安全中心', '验证码', '安全验证', '请完成以下操作', '输入验证码']
        return any(keyword in text for keyword in keywords)
    
    def _is_polysemous(self, soup):
        """判断页面是否为多义词页面"""
        text = soup.get_text()
        return '本词条是一个多义词' in text or '请在下列义项中选择浏览' in text
    
    def _get_basic_info_block(self, soup):
        """从基本信息区域获取基本信息的字典"""
        basic_info_dict = {}
        
        # 尝试多种可能的基本信息块选择器
        selectors = [
            'div[class*="basicInfo"]',  # 包含basicInfo的div
            'div.basic-info',           # 老版本格式
            '.lemma-summary .basic-info', # 另一种可能的格式
        ]
        
        basic_info_block = None
        for selector in selectors:
            basic_info_block = soup.select_one(selector)
            if basic_info_block:
                break
        
        if not basic_info_block:
            # 尝试通过正则匹配类名
            basic_info_block = soup.find('div', class_=re.compile(r'basicInfo.*'))
        
        if not basic_info_block:
            logging.debug("未找到基本信息块")
            return basic_info_dict
        
        # 提取键值对
        try:
            # 方法1: 使用dt/dd标签对
            key_elements = basic_info_block.find_all('dt', class_=re.compile(r'basicInfoItem.*'))
            value_elements = basic_info_block.find_all('dd', class_=re.compile(r'basicInfoItem.*'))
            
            if key_elements and value_elements:
                for key_elem, value_elem in zip(key_elements, value_elements):
                    key = self._clean_text(key_elem.get_text(strip=True))
                    value = self._clean_text(value_elem.get_text(strip=True))
                    if key and value:
                        basic_info_dict[key] = value
            
            # 方法2: 如果方法1没有结果，尝试其他格式
            if not basic_info_dict:
                # 查找所有包含冒号的行，可能是"键: 值"格式
                text_lines = basic_info_block.get_text().split('\n')
                for line in text_lines:
                    line = line.strip()
                    if '：' in line or ':' in line:
                        parts = re.split('[：:]', line, 1)
                        if len(parts) == 2:
                            key = self._clean_text(parts[0].strip())
                            value = self._clean_text(parts[1].strip())
                            if key and value:
                                basic_info_dict[key] = value
                                
        except Exception as e:
            logging.error(f"解析基本信息失败: {e}")
        
        return basic_info_dict
    
    def _clean_text(self, text):
        """清理文本"""
        if not text:
            return text
        
        # 如果有ftfy库，使用它进行文本修复
        if FTFY_AVAILABLE:
            try:
                text = ftfy.fix_text(text)
            except:
                pass
        
        # 基本的文本清理
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 移除特殊的空白字符（如\xa0）
        text = text.replace('\xa0', ' ')
        text = text.replace('\u3000', ' ')  # 全角空格
        
        # 移除引用标记和编辑按钮等
        text = re.sub(r'\[\d+\]', '', text)  # 秼除[1]这样的引用标记
        text = re.sub(r'编辑$', '', text)    # 移除末尾的"编辑"
        
        return text.strip()
    
    def _map_extracted_fields(self, basic_info, name):
        """将提取的字段映射到标准列名"""
        from config import COLUMNS
        
        # 创建标准数据字典
        mapped_data = {col: '' for col in COLUMNS}
        mapped_data['中文名'] = name
        
        # 字段映射表 - 将百度百科的字段名映射到我们的标准字段名
        field_mapping = {
            # 基本信息映射
            '外文名': '外文名',
            '别名': '别名', 
            '性别': '性别',
            '国籍': '国籍',
            '民族': '民族',
            '籍贯': '籍贯',
            '出生地': '籍贯',  # 有时出生地可以作为籍贯
            '政治面貌': '政治面貌',
            '出生日期': '出生日期',
            '出生时间': '出生日期',
            '生于': '出生日期',
            '毕业院校': '毕业院校',
            '毕业学校': '毕业院校',
            '学校': '毕业院校',
            '职业': '职业',
            '职务': '担任职务',
            '职称': '职称',
            '主要成就': '成就',
            '成就': '成就',
            '代表作品': '代表作品',
            '作品': '代表作品',
            '逝世日期': '逝世日期',
            '逝世时间': '逝世日期',
            '去世时间': '逝世日期',
            '死于': '逝世日期',
        }
        
        # 执行字段映射
        for extracted_key, extracted_value in basic_info.items():
            if not extracted_value:
                continue
                
            # 直接匹配
            if extracted_key in field_mapping:
                target_field = field_mapping[extracted_key]
                mapped_data[target_field] = str(extracted_value)
                continue
            
            # 模糊匹配
            extracted_key_lower = extracted_key.lower()
            for baike_field, standard_field in field_mapping.items():
                if baike_field.lower() in extracted_key_lower or extracted_key_lower in baike_field.lower():
                    mapped_data[standard_field] = str(extracted_value)
                    break
        
        return mapped_data

    def get_stats(self):
        """获取线程统计信息"""
        return {
            'thread_id': self.thread_id,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'success_rate': self.success_count / (self.success_count + self.failure_count) * 100
                           if (self.success_count + self.failure_count) > 0 else 0
        }

class MultiThreadScraper:
    """多线程爬虫主类"""
    
    def __init__(self, proxy_list=None, people_list_file=None, output_file=None, 
                 num_threads=10, dynamic_proxy_config=None):
        """
        初始化多线程爬虫
        
        Args:
            proxy_list: 静态代理列表
            people_list_file: 人名列表文件
            output_file: 输出文件
            num_threads: 线程数
            dynamic_proxy_config: 动态代理配置字典，如果提供则使用动态代理
        """
        # 选择代理管理器
        if dynamic_proxy_config and DYNAMIC_PROXY_AVAILABLE:
            logging.info("使用动态代理模式")
            self.proxy_manager = DynamicProxyManager(
                dynamic_proxy_config, 
                initial_size=dynamic_proxy_config.get('initial_size', 20)
            )
            self.proxy_mode = 'dynamic'
        elif proxy_list:
            logging.info("使用静态代理模式")
            self.proxy_manager = ThreadSafeProxyManager(proxy_list)
            self.proxy_mode = 'static'
        else:
            raise ValueError("必须提供 proxy_list 或 dynamic_proxy_config")
        
        self.data_manager = ThreadSafeDataManager(output_file)
        self.people_list_file = people_list_file
        self.num_threads = num_threads
        self.workers = []
        
        # 加载人名列表
        self.all_names = self._load_names()
        self.names_to_process = [name for name in self.all_names 
                               if not self.data_manager.is_processed(name)]
        
        logging.info(f"总共 {len(self.all_names)} 个名字，需要处理 {len(self.names_to_process)} 个")
        logging.info(f"代理模式: {self.proxy_mode}")
    
    def _load_names(self):
        """加载人名列表"""
        with open(self.people_list_file, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    
    def run(self):
        """运行多线程爬取"""
        if not self.names_to_process:
            logging.info("没有需要处理的数据")
            return
        
        logging.info(f"开始使用 {self.num_threads} 个线程爬取数据...")
        
        # 创建任务队列
        task_queue = queue.Queue()
        for name in self.names_to_process:
            task_queue.put(name)
        
        # 创建并启动工作线程
        threads = []
        for i in range(self.num_threads):
            worker = WorkerThread(i, self.proxy_manager, self.data_manager, None)
            thread = threading.Thread(target=self._worker_thread, 
                                    args=(worker, task_queue))
            thread.start()
            threads.append((thread, worker))
            self.workers.append(worker)
        
        # 监控进度
        monitor_thread = threading.Thread(target=self._monitor_progress)
        monitor_thread.start()
        
        # 等待所有工作线程完成
        for thread, worker in threads:
            thread.join()
        
        # 停止监控线程
        self.stop_monitoring = True
        monitor_thread.join()
        
        # 强制保存所有缓冲数据
        self.data_manager.force_flush()
        
        # 输出最终统计
        self._print_final_stats()
    
    def _worker_thread(self, worker, task_queue):
        """工作线程函数"""
        while True:
            try:
                name = task_queue.get(timeout=5)
                
                # 再次检查是否已处理（避免重复）
                if self.data_manager.is_processed(name):
                    task_queue.task_done()
                    continue
                
                # 爬取数据
                person_data = worker.scrape_single_person(name)
                
                if person_data:
                    # 注意：这里的person_data已经在scrape_single_person中处理过add_data了
                    logging.info(f"线程 {worker.thread_id} 成功爬取: {name}")
                else:
                    logging.warning(f"线程 {worker.thread_id} 爬取失败: {name}")
                
                # 随机延迟
                time.sleep(random.uniform(0.5, 1.5))
                
                task_queue.task_done()
                
            except queue.Empty:
                logging.info(f"线程 {worker.thread_id} 任务完成")
                break
            except Exception as e:
                logging.error(f"线程 {worker.thread_id} 发生错误: {e}")
                continue
    
    def _monitor_progress(self):
        """监控进度"""
        self.stop_monitoring = False
        start_time = time.time()
        
        while not self.stop_monitoring:
            time.sleep(30)  # 每30秒输出一次进度
            
            progress = self.data_manager.get_progress(len(self.all_names))
            proxy_stats = self.proxy_manager.get_stats()
            
            elapsed_time = time.time() - start_time
            
            logging.info(f"""
=== 进度报告 ===
已处理: {progress['processed']}/{progress['total']} ({progress['percentage']:.2f}%)
缓冲区: {progress['buffer_size']} 条数据待写入
可用代理: {proxy_stats['available_proxies']}/{proxy_stats['total_proxies']}
失效代理: {proxy_stats['failed_proxies']} 个
运行时间: {elapsed_time/3600:.2f} 小时
预计剩余时间: {(elapsed_time / max(progress['processed'], 1)) * (progress['total'] - progress['processed']) / 3600:.2f} 小时
            """)
    
    def _print_final_stats(self):
        """输出最终统计信息"""
        total_success = sum(worker.success_count for worker in self.workers)
        total_failure = sum(worker.failure_count for worker in self.workers)
        
        logging.info(f"""
=== 最终统计 ===
总成功数: {total_success}
总失败数: {total_failure}
成功率: {total_success / (total_success + total_failure) * 100:.2f}%

线程统计:
        """)
        
        for worker in self.workers:
            stats = worker.get_stats()
            logging.info(f"线程 {stats['thread_id']}: 成功 {stats['success_count']}, "
                        f"失败 {stats['failure_count']}, 成功率 {stats['success_rate']:.2f}%")
    
    def _enhanced_extract_person_data(self, soup, name):
        """增强版人物数据提取 - 处理重名和多义词情况"""
        
        # 首先分析页面类型和重名情况
        page_analysis = self._analyze_page_and_name_disambiguation(soup, name)
        
        # 构建基础原始数据
        base_raw_data = {
            'original_name': name,
            'page_type': page_analysis['page_type'],
            'html_length': len(str(soup)),
            'is_specific_person': page_analysis.get('is_specific_person', False),
            'person_identifier': page_analysis.get('person_identifier'),
            'disambiguation_info': page_analysis.get('disambiguation_info', {})
        }
        
        # 根据页面类型采用不同的处理策略
        if page_analysis['page_type'] == '多义词消歧页面':
            # 处理多义词页面
            alternatives = self._extract_person_alternatives(soup)
            mapped_data = self._map_extracted_fields({}, name)
            mapped_data['status'] = f'多义词页面({len(alternatives)}个选项)'
            
            raw_data = {
                **base_raw_data,
                'alternatives_count': len(alternatives),
                'person_alternatives': alternatives[:5],  # 只保存前5个
                'extraction_fields_count': 0,
                'raw_basic_info': {}
            }
            
            logging.info(f"检测到多义词页面 {name}，发现 {len(alternatives)} 个选项")
            
        elif page_analysis['page_type'] == '特定人物页面':
            # 处理特定人物页面
            try:
                basic_info = self._get_basic_info_block(soup)
                mapped_data = self._map_extracted_fields(basic_info, name)
                
                # 如果是重名的特定人物，在中文名字段中标注身份
                if page_analysis.get('person_identifier'):
                    mapped_data['中文名'] = f"{name}（{page_analysis['person_identifier']}）"
                
                mapped_data['status'] = '成功'
                
                raw_data = {
                    **base_raw_data,
                    'extraction_fields_count': len(basic_info),
                    'raw_basic_info': basic_info.copy(),
                    'all_extracted_keys': list(basic_info.keys()) if basic_info else []
                }
                
                extracted_fields = len([v for v in basic_info.values() if v and str(v).strip()])
                logging.debug(f"成功提取特定人物 {name} 的 {extracted_fields} 个字段")
                
            except Exception as e:
                logging.error(f"提取特定人物 {name} 数据失败: {e}")
                mapped_data = self._map_extracted_fields({}, name)
                mapped_data['status'] = f'特定人物提取失败: {str(e)}'
                
                raw_data = {
                    **base_raw_data,
                    'error_message': str(e),
                    'extraction_fields_count': 0,
                    'raw_basic_info': {}
                }
        
        elif page_analysis['page_type'] == '一般概念页面':
            # 非人物词条
            mapped_data = self._map_extracted_fields({}, name)
            mapped_data['status'] = '非人物词条'
            
            raw_data = {
                **base_raw_data,
                'extraction_fields_count': 0,
                'raw_basic_info': {},
                'concept_type': '一般概念'
            }
            
            logging.debug(f"检测到非人物词条: {name}")
            
        else:
            # 其他类型页面，提取基本信息
            try:
                basic_info = self._get_basic_info_block(soup)
                
                # 构建原始数据
                raw_data = {
                    **base_raw_data,
                    'extraction_fields_count': len(basic_info),
                    'raw_basic_info': basic_info.copy(),
                    'all_extracted_keys': list(basic_info.keys()) if basic_info else []
                }
                
                # 映射到标准字段
                mapped_data = self._map_extracted_fields(basic_info, name)
                mapped_data['status'] = '成功'
                
                logging.debug(f"成功提取 {name} 的 {len(basic_info)} 个字段")
                
            except Exception as e:
                logging.error(f"提取 {name} 数据失败: {e}")
                raw_data = {
                    **base_raw_data,
                    'error_message': str(e)
                }
                mapped_data = self._map_extracted_fields({}, name)
                mapped_data['status'] = f'提取失败: {str(e)}'
            
        return mapped_data, raw_data
    
    def _analyze_page_and_name_disambiguation(self, soup, original_name):
        """分析页面类型和重名消歧情况"""
        analysis = {
            'page_type': '未知页面',
            'is_specific_person': False,
            'person_identifier': None,
            'disambiguation_info': {}
        }
        
        text = soup.get_text()
        title_elem = soup.find('title')
        title_text = title_elem.get_text() if title_elem else ""
        
        # 检测多义词消歧页面
        disambiguation_keywords = [
            '本词条是一个多义词',
            '请在下列义项中选择浏览',
            '多义词消歧页面',
            '存在多个含义'
        ]
        
        if any(keyword in text for keyword in disambiguation_keywords):
            analysis['page_type'] = '多义词消歧页面'
            return analysis
        
        # 检测安全验证页面
        if self._is_safety_check_page(soup):
            analysis['page_type'] = '安全验证页面'
            return analysis
            
        # 检测未收录页面
        if self._is_unrecorded_person(soup):
            analysis['page_type'] = '未收录页面'
            return analysis
        
        # 分析标题中的身份标识
        identifier_pattern = r'（([^）]+)）'
        identifier_match = re.search(identifier_pattern, title_text)
        
        if identifier_match:
            identifier = identifier_match.group(1)
            
            # 判断是否为人物身份标识
            person_indicators = [
                # 学术和专业职称
                '院士', '教授', '博士', '专家', '学者', '研究员', '科学家',
                # 政府和军队职务
                '主任', '部长', '书记', '厅长', '局长', '司长', '处长', '科长',
                '将军', '上校', '中校', '少校', '上尉', '中尉', '少尉',
                '烈士', '革命家', '政治家',
                # 企业职务
                '总裁', '董事长', '总经理', 'CEO', 'CTO', 'CFO',
                '企业家', '商人', '创始人', '创办人',
                # 文艺和体育
                '作家', '诗人', '画家', '艺术家', '演员', '歌手', '导演', '编剧',
                '运动员', '教练', '球员', '选手', '冠军',
                # 专业技术
                '医生', '律师', '工程师', '设计师', '建筑师',
                '飞行员', '宇航员', '船员', '机长',
                # 时间标识（表示历史人物）
                '年生', '年-', '世纪', '朝代', '明朝', '清朝', '宋朝', '唐朝'
            ]
            
            if any(indicator in identifier for indicator in person_indicators):
                analysis['page_type'] = '特定人物页面'
                analysis['is_specific_person'] = True
                analysis['person_identifier'] = identifier
                analysis['disambiguation_info'] = {
                    'is_disambiguation_case': True,
                    'resolved_identity': identifier,
                    'name_conflict_resolved': True
                }
            else:
                analysis['page_type'] = '一般概念页面'
                analysis['disambiguation_info'] = {
                    'is_disambiguation_case': False,
                    'concept_identifier': identifier
                }
        else:
            # 没有括号标识，检查是否有人物基本信息
            has_basic_info = self._has_person_basic_info(soup)
            
            if has_basic_info:
                analysis['page_type'] = '普通人物页面'
                analysis['is_specific_person'] = True
                analysis['disambiguation_info'] = {
                    'is_disambiguation_case': False,
                    'name_conflict_resolved': False
                }
            else:
                analysis['page_type'] = '一般概念页面'
        
        return analysis
    
    def _has_person_basic_info(self, soup):
        """检查是否包含人物基本信息区块"""
        basic_info_selectors = [
            'div[class*="basicInfo"]',
            'div.basic-info',
            '.lemma-summary .basic-info'
        ]
        
        for selector in basic_info_selectors:
            basic_info_block = soup.select_one(selector)
            if basic_info_block:
                # 进一步检查是否包含人物相关字段
                text = basic_info_block.get_text().lower()
                person_fields = ['性别', '国籍', '出生', '职业', '毕业', '民族']
                if any(field in text for field in person_fields):
                    return True
        
        return False
    
    def _extract_person_alternatives(self, soup):
        """从消歧页面提取人物选项"""
        alternatives = []
        
        # 多种可能的消歧页面选择器
        selectors = [
            '.polysemantList-wrapper a',
            '.polysemant-list a', 
            '.disambiguation a',
            'ul li a[href*="/item/"]',
            '.lemma-summary a[href*="/item/"]',
            '.para a[href*="/item/"]'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                text = link.get_text().strip()
                
                if href and text and '/item/' in href:
                    full_url = f"https://baike.baidu.com{href}" if href.startswith('/') else href
                    
                    # 判断是否可能是人物链接
                    if self._is_likely_person_link(text):
                        alternatives.append({
                            'title': text,
                            'url': full_url,
                            'extracted_from': selector
                        })
            
            if alternatives:  # 找到就停止
                break
        
        # 去重
        seen_urls = set()
        unique_alternatives = []
        for alt in alternatives:
            if alt['url'] not in seen_urls:
                unique_alternatives.append(alt)
                seen_urls.add(alt['url'])
        
        return unique_alternatives[:10]  # 限制数量
    
    def _is_likely_person_link(self, link_text):
        """判断链接文本是否可能指向人物"""
        person_indicators = [
            '院士', '教授', '博士', '专家', '学者',
            '主任', '部长', '书记', '厅长', '局长',
            '作家', '诗人', '画家', '演员', '歌手', '导演',
            '运动员', '球员', '选手', '教练',
            '将军', '上校', '中校', '少校',
            '企业家', '总裁', '董事长', 'CEO'
        ]
        
        return any(indicator in link_text for indicator in person_indicators)
        
    # ...existing code...
