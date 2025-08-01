#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动态代理爬虫启动器
"""

import sys
import json
import time
from multithreaded_scraper import MultiThreadScraper, DYNAMIC_PROXY_AVAILABLE
from config import *

def test_dynamic_proxy():
    """测试动态代理API"""
    if not DYNAMIC_PROXY_AVAILABLE:
        print("❌ 动态代理模块不可用，请检查 dynamic_proxy.py 文件")
        return False
    
    print("🔧 测试动态代理API连接...")
    
    try:
        from dynamic_proxy import DynamicProxyFetcher
        fetcher = DynamicProxyFetcher(DYNAMIC_PROXY_CONFIG)
        
        print(f"📡 正在测试API: {DYNAMIC_PROXY_CONFIG['url']}")
        proxies = fetcher.fetch_proxies()
        
        if proxies:
            print(f"✅ API测试成功！获取到 {len(proxies)} 个代理")
            print("📋 前5个代理预览:")
            for i, proxy in enumerate(proxies[:5], 1):
                print(f"   {i}. {proxy}")
            return True
        else:
            print("❌ API测试失败：未获取到任何代理")
            return False
            
    except Exception as e:
        print(f"❌ 动态代理测试失败: {e}")
        return False

def configure_api_params():
    """配置API参数"""
    print("\n🔧 动态代理API配置")
    
    current_config = DYNAMIC_PROXY_CONFIG.copy()
    
    print(f"当前API地址: {current_config['url']}")
    # print(f"当前参数: {current_config['params']}")
    
    # 询问是否需要修改参数
    modify = input("\n是否需要修改API参数? (y/N): ").strip().lower()
    
    if modify == 'y':
        print("\n请输入您的API参数 (直接回车保持当前值):")
        
        # 修改交易号
        trade_no = input(f"交易号 (当前: {current_config['params'].get('trade_no', 'N/A')}): ").strip()
        if trade_no:
            current_config['params']['trade_no'] = trade_no
        
        # 修改签名
        sign = input(f"签名 (当前: {current_config['params'].get('sign', 'N/A')}): ").strip()
        if sign:
            current_config['params']['sign'] = sign
        
        # 修改代理数量
        num_str = input(f"每次获取代理数量 (当前: {current_config['params'].get('num', 30)}): ").strip()
        if num_str and num_str.isdigit():
            current_config['params']['num'] = int(num_str)
            current_config['initial_size'] = int(num_str)
    
    return current_config

def estimate_time_and_cost(names_count, proxy_count, threads_count):
    """估算时间和成本"""
    print(f"\n📊 性能估算 (基于 {names_count:,} 个目标):")
    
    # 时间估算
    avg_time_per_request = 3.0  # 秒 (包含网络延迟)
    success_rate = 0.8
    retry_factor = 1.3
    
    effective_threads = min(threads_count, proxy_count)
    
    total_time_seconds = (names_count * avg_time_per_request * retry_factor) / (effective_threads * success_rate)
    hours = total_time_seconds / 3600
    
    print(f"   ⏱️  预计耗时: {int(hours)}小时{int((hours % 1) * 60)}分钟")
    print(f"   🔄 有效线程: {effective_threads} (线程数受代理数量限制)")
    print(f"   📈 预期成功率: {success_rate*100:.0f}%")
    
    # 代理使用量估算 (假设每个代理可重复使用)
    proxy_requests_per_hour = names_count / hours
    print(f"   📡 代理请求频率: {proxy_requests_per_hour:.0f} 请求/小时")

def interactive_config():
    """交互式配置 - 纯动态代理版本"""
    print("\n🚀 动态代理爬虫配置向导")
    print("=" * 40)
    
    # 人名文件
    names_file = input(f"人名文件路径 (回车使用默认 {PEOPLE_LIST_FILE}): ").strip()
    if not names_file:
        names_file = PEOPLE_LIST_FILE
    
    # 检查文件存在
    try:
        with open(names_file, 'r', encoding='utf-8') as f:
            names_count = len([line for line in f if line.strip()])
    except FileNotFoundError:
        print(f"❌ 文件 {names_file} 不存在")
        return None
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return None
    
    print(f"📊 数据统计: 需要处理 {names_count:,} 个人物")
    
    # 输出文件
    output_file = input(f"输出文件路径 (回车使用默认 {OUTPUT_FILE}): ").strip()
    if not output_file:
        output_file = OUTPUT_FILE
    
    # 动态代理配置
    dynamic_config = configure_api_params()
    proxy_count = dynamic_config.get('initial_size', 30)
    
    # 线程数配置
    max_threads = min(proxy_count, 50)  # 不超过代理数，也不超过50
    recommended_threads = min(proxy_count, 20)
    
    threads_input = input(f"线程数量 (推荐: {recommended_threads}, 最大: {max_threads}): ").strip()
    
    try:
        threads_count = int(threads_input) if threads_input else recommended_threads
        threads_count = min(threads_count, max_threads)
    except ValueError:
        threads_count = recommended_threads
        print(f"无效输入，使用推荐值: {threads_count}")
    
    # 显示配置摘要
    print(f"\n🎯 配置摘要:")
    print(f"   📁 人名文件: {names_file}")
    print(f"   📊 目标数量: {names_count:,} 个")
    print(f"   📄 输出文件: {output_file}")
    print(f"   🔄 线程数量: {threads_count}")
    print(f"   🌐 代理模式: 动态代理")
    print(f"   📡 初始代理数: {proxy_count}")
    print(f"   🔄 刷新间隔: {dynamic_config.get('fetch_interval', 300)}秒")
    
    # 性能估算
    estimate_time_and_cost(names_count, proxy_count, threads_count)
    
    return {
        'people_file': names_file,
        'names_count': names_count,
        'output_file': output_file,
        'threads_count': threads_count,
        'dynamic_config': dynamic_config
    }

def main():
    """主函数 - 纯动态代理版本"""
    print("""
🚀 动态代理百度百科爬虫 v3.0
=====================================
专为大规模数据采集设计
✅ 纯动态代理，无需管理代理文件
✅ 自动代理刷新和失效检测
✅ 多线程并发采集
    """)
    
    # 检查动态代理可用性
    if not DYNAMIC_PROXY_AVAILABLE:
        print("❌ 动态代理功能不可用")
        print("请确保 dynamic_proxy.py 文件存在且可正常导入")
        return
    
    # 测试动态代理
    if not test_dynamic_proxy():
        print("\n❌ 动态代理测试失败，请检查配置")
        print("💡 请确认以下内容:")
        print("   1. API地址是否正确")
        print("   2. 交易号和签名是否有效")
        print("   3. 网络连接是否正常")
        return
    
    # 交互式配置
    config = interactive_config()
    if not config:
        return
    
    # 最终确认
    print(f"\n🎯 即将开始爬取 {config['names_count']:,} 个人物信息")
    confirm = input("确认开始? (y/N): ").strip().lower()
    
    if confirm != 'y':
        print("❌ 取消操作")
        return
    
    # 创建并启动爬虫
    print("🚀 启动动态代理爬虫...")
    print("📡 代理将自动获取和管理，无需手动维护")
    
    try:
        scraper = MultiThreadScraper(
            proxy_list=None,  # 不使用静态代理列表
            people_list_file=config['people_file'],
            output_file=config['output_file'],
            num_threads=config['threads_count'],
            dynamic_proxy_config=config['dynamic_config']
        )
        
        start_time = time.time()
        scraper.run()
        end_time = time.time()
        
        
        elapsed = end_time - start_time
        print(f"\n✅ 爬取任务完成！")
        print(f"⏱️  总耗时: {elapsed/3600:.1f} 小时")
        print(f"📄 输出文件: {config['output_file']}")
        
    except KeyboardInterrupt:
        print("\n⏸️  用户中断，正在保存数据...")
        scraper.data_manager.force_flush()
        print("💾 数据已保存")
    except Exception as e:
        print(f"\n❌ 爬取过程中发生错误: {e}")
        print("💾 正在保存已爬取的数据...")
        try:
            scraper.data_manager.force_flush()
        except:
            pass

if __name__ == '__main__':
    main()
