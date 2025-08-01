# 百度百科批量数据爬虫 / Baidu Baike Batch Data Crawler

[English](#english) | [中文](#中文)

---

## 中文

### 项目简介

这是一个基于Python的百度百科批量数据爬虫项目，支持10万级别数据采集。该爬虫采用多线程架构，支持静态代理和动态代理两种模式，能够高效稳定地爬取百度百科人物条目信息。

### 主要特性

- 🚀 **高性能多线程**：支持多线程并发爬取，可处理10万级别数据
- 🔄 **双代理模式**：支持静态代理池和动态代理API两种模式
- 🛡️ **反爬虫策略**：内置请求延迟、代理轮换、重试机制
- 📊 **实时监控**：提供爬取进度实时显示和统计信息
- 💾 **数据持久化**：支持CSV格式输出和临时JSON缓存
- 🔧 **灵活配置**：可自定义线程数、延迟时间、重试次数等参数

### 技术架构

- **语言**：Python 3.x
- **主要依赖**：requests、BeautifulSoup4、pandas、tqdm
- **并发模型**：基于ThreadPoolExecutor的多线程架构
- **代理管理**：线程安全的代理池管理器

### 核心功能

#### 1. 人物信息提取
爬虫能够从百度百科提取以下人物信息：
- 基本信息：中文名、外文名、别名、性别、国籍、民族、籍贯
- 个人背景：出生日期、逝世日期、毕业院校、政治面貌
- 职业信息：职业、职称、担任职务、军衔晋升
- 成就作品：代表作品、成就、人物评价
- 社会关系：家庭成员、个人生活
- 履历信息：人物履历

#### 2. 动态代理支持
- 通过API接口自动获取代理
- 支持多种API响应格式解析
- 代理健康检查和自动切换
- 代理使用统计和故障恢复

#### 3. 智能反爬虫
- 随机请求延迟
- User-Agent轮换
- 代理IP轮换
- 请求失败重试
- 403错误智能处理

### 文件结构

```
├── config.py                 # 配置文件
├── multithreaded_scraper.py   # 多线程爬虫主程序
├── dynamic_proxy.py           # 动态代理管理器
├── run_dynamic_scraper.py     # 爬虫启动器
├── names.csv                  # 人名列表（10万条数据）
├── scraper.log               # 运行日志
└── README.md                 # 项目说明文档
```

### 快速开始

#### 1. 环境准备

```bash
# 安装Python依赖
pip install requests beautifulsoup4 pandas tqdm ftfy
```

#### 2. 配置设置

编辑 `config.py` 文件，根据需要调整以下参数：

```python
# 多线程配置
NUM_THREADS = 8              # 线程数量
MAX_RETRIES_PER_NAME = 2     # 最大重试次数
PROXY_POOL_SIZE = 32         # 代理池大小

# 请求配置
REQUEST_TIMEOUT = 20         # 请求超时时间
MIN_DELAY = 2.0             # 最小延迟
MAX_DELAY = 4.0             # 最大延迟
```

#### 3. 运行爬虫

```bash
# 运行动态代理爬虫
python run_dynamic_scraper.py
```

#### 4. 查看结果

爬取完成后，数据将保存在 `baike_data_multithreaded.csv` 文件中。

### 配置说明

#### 基本配置
- `PEOPLE_LIST_FILE`: 人名列表文件路径
- `OUTPUT_FILE`: 输出CSV文件路径
- `NUM_THREADS`: 并发线程数量

#### 代理配置
- `PROXY_POOL_SIZE`: 代理池大小
- `PROXY_TIMEOUT`: 代理获取超时时间
- `DYNAMIC_PROXY_CONFIG`: 动态代理API配置

#### 请求配置
- `REQUEST_TIMEOUT`: HTTP请求超时时间
- `MIN_DELAY/MAX_DELAY`: 请求间隔延迟范围

### 监控和日志

项目提供了完整的监控和日志功能：

- **实时进度显示**：使用tqdm显示爬取进度
- **统计信息**：成功率、失败率、代理使用情况
- **日志记录**：详细的运行日志保存在 `scraper.log`
- **错误追踪**：记录所有异常和错误信息

### 注意事项

1. **合规使用**：请遵守robots.txt协议和相关法律法规
2. **频率控制**：建议设置合理的请求延迟，避免对服务器造成压力
3. **代理质量**：建议使用高质量的代理服务，确保爬取稳定性
4. **数据备份**：定期备份爬取的数据，避免意外丢失

### 性能优化建议

1. **代理池大小**：确保代理数量是线程数的3-4倍
2. **请求延迟**：根据代理质量调整延迟时间
3. **线程数量**：根据机器性能和代理数量调整
4. **重试策略**：合理设置重试次数，避免无效重试

### 故障排除

#### 常见问题

1. **403错误频繁**
   - 增加请求延迟时间
   - 更换高质量代理
   - 减少并发线程数

2. **代理连接失败**
   - 检查代理服务器状态
   - 验证代理API配置
   - 增加代理超时时间

3. **数据提取不完整**
   - 检查网页结构变化
   - 更新CSS选择器
   - 验证数据清理逻辑

### 许可证

本项目仅供学习和研究使用，请遵守相关法律法规和网站使用条款。

---

## English

### Project Overview

This is a Python-based Baidu Baike (Baidu Encyclopedia) batch data crawler project that supports data collection at the scale of 100,000 entries. The crawler adopts a multi-threaded architecture and supports both static proxy pools and dynamic proxy APIs for efficient and stable crawling of Baidu Baike biographical entries.

### Key Features

- 🚀 **High-Performance Multi-threading**: Supports concurrent crawling with multiple threads, capable of handling 100K-level data
- 🔄 **Dual Proxy Modes**: Supports both static proxy pools and dynamic proxy APIs
- 🛡️ **Anti-Bot Strategies**: Built-in request delays, proxy rotation, and retry mechanisms
- 📊 **Real-time Monitoring**: Provides real-time crawling progress display and statistics
- 💾 **Data Persistence**: Supports CSV output format and temporary JSON caching
- 🔧 **Flexible Configuration**: Customizable thread count, delay times, retry attempts, and other parameters

### Technical Architecture

- **Language**: Python 3.x
- **Main Dependencies**: requests, BeautifulSoup4, pandas, tqdm
- **Concurrency Model**: Multi-threaded architecture based on ThreadPoolExecutor
- **Proxy Management**: Thread-safe proxy pool manager

### Core Functionality

#### 1. Biographical Information Extraction
The crawler can extract the following biographical information from Baidu Baike:
- Basic Info: Chinese name, foreign name, alias, gender, nationality, ethnicity, hometown
- Personal Background: birth date, death date, alma mater, political affiliation
- Professional Info: occupation, professional title, positions held, military rank progression
- Achievements: representative works, accomplishments, character evaluation
- Social Relations: family members, personal life
- Career History: biographical timeline

#### 2. Dynamic Proxy Support
- Automatic proxy acquisition through API interfaces
- Support for parsing multiple API response formats
- Proxy health checks and automatic switching
- Proxy usage statistics and failure recovery

#### 3. Intelligent Anti-Bot Measures
- Random request delays
- User-Agent rotation
- Proxy IP rotation
- Request failure retry mechanism
- Intelligent 403 error handling

### File Structure

```
├── config.py                 # Configuration file
├── multithreaded_scraper.py   # Multi-threaded crawler main program
├── dynamic_proxy.py           # Dynamic proxy manager
├── run_dynamic_scraper.py     # Crawler launcher
├── names.csv                  # Name list (100K entries)
├── scraper.log               # Runtime logs
└── README.md                 # Project documentation
```

### Quick Start

#### 1. Environment Setup

```bash
# Install Python dependencies
pip install requests beautifulsoup4 pandas tqdm ftfy
```

#### 2. Configuration

Edit the `config.py` file and adjust the following parameters as needed:

```python
# Multi-threading configuration
NUM_THREADS = 8              # Number of threads
MAX_RETRIES_PER_NAME = 2     # Maximum retry attempts
PROXY_POOL_SIZE = 32         # Proxy pool size

# Request configuration
REQUEST_TIMEOUT = 20         # Request timeout
MIN_DELAY = 2.0             # Minimum delay
MAX_DELAY = 4.0             # Maximum delay
```

#### 3. Run the Crawler

```bash
# Run the dynamic proxy crawler
python run_dynamic_scraper.py
```

#### 4. View Results

After crawling is complete, data will be saved in the `baike_data_multithreaded.csv` file.

### Configuration Details

#### Basic Configuration
- `PEOPLE_LIST_FILE`: Path to the name list file
- `OUTPUT_FILE`: Output CSV file path
- `NUM_THREADS`: Number of concurrent threads

#### Proxy Configuration
- `PROXY_POOL_SIZE`: Proxy pool size
- `PROXY_TIMEOUT`: Proxy acquisition timeout
- `DYNAMIC_PROXY_CONFIG`: Dynamic proxy API configuration

#### Request Configuration
- `REQUEST_TIMEOUT`: HTTP request timeout
- `MIN_DELAY/MAX_DELAY`: Request interval delay range

### Monitoring and Logging

The project provides comprehensive monitoring and logging features:

- **Real-time Progress Display**: Uses tqdm to show crawling progress
- **Statistics**: Success rate, failure rate, proxy usage statistics
- **Log Recording**: Detailed runtime logs saved in `scraper.log`
- **Error Tracking**: Records all exceptions and error information

### Important Notes

1. **Compliance**: Please comply with robots.txt protocols and relevant laws and regulations
2. **Rate Control**: It's recommended to set reasonable request delays to avoid putting pressure on servers
3. **Proxy Quality**: Use high-quality proxy services to ensure crawling stability
4. **Data Backup**: Regularly backup crawled data to prevent accidental loss

### Performance Optimization Recommendations

1. **Proxy Pool Size**: Ensure the number of proxies is 3-4 times the thread count
2. **Request Delays**: Adjust delay times based on proxy quality
3. **Thread Count**: Adjust based on machine performance and proxy availability
4. **Retry Strategy**: Set reasonable retry attempts to avoid ineffective retries

### Troubleshooting

#### Common Issues

1. **Frequent 403 Errors**
   - Increase request delay times
   - Switch to higher quality proxies
   - Reduce concurrent thread count

2. **Proxy Connection Failures**
   - Check proxy server status
   - Verify proxy API configuration
   - Increase proxy timeout duration

3. **Incomplete Data Extraction**
   - Check for webpage structure changes
   - Update CSS selectors
   - Verify data cleaning logic

### License

This project is for educational and research purposes only. Please comply with relevant laws, regulations, and website terms of use.

### Contact

For questions or suggestions, please open an issue in the repository.

---

**Disclaimer**: This tool is intended for educational and research purposes only. Users are responsible for ensuring compliance with applicable laws and website terms of service.
