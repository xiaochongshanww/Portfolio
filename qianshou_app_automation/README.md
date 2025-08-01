# 牵手自动化 / QianShou Automation

[English](#english) | [中文](#chinese)

---

## English

### 📱 QianShou (牵手) App Automation Tool

This project is an automated testing tool for the QianShou dating app using Appium framework. It can automatically browse profiles, collect user information, and perform swipe actions.

### ✨ Features

- **Automated Profile Browsing**: Automatically browse through user profiles
- **Data Collection**: Extract and store user information including:
  - Nickname, age, height
  - Constellation, education, work information
  - Salary, hometown, current location
  - Love targets and personal introduction
  - Real-name certification status
- **Smart Swiping**: Automated like/dislike actions
- **Database Storage**: Store collected data in SQLite database
- **Comprehensive Logging**: Detailed logging system with file and console output
- **Error Recovery**: Automatic reconnection and error handling

### 🛠️ Technology Stack

- **Python 3.12+**
- **Appium** - Mobile app automation
- **Selenium WebDriver** - Web automation framework
- **SQLite** - Local database storage
- **PIL (Pillow)** - Image processing
- **Pytesseract** - OCR text recognition
- **lxml** - XML parsing

### 📋 Prerequisites

1. **Android Device/Emulator** with Android 14+
2. **Appium Server** running on `http://127.0.0.1:4723`
3. **ADB (Android Debug Bridge)** properly configured
4. **Tesseract OCR** installed at `C:\Program Files\Tesseract-OCR\tesseract.exe`
5. **Tantan App** installed and logged in on the device

### 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd qianshou_app_automation
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Tesseract OCR**
   - Download and install Tesseract OCR
   - Ensure it's installed at `C:\Program Files\Tesseract-OCR\tesseract.exe`

5. **Start Appium Server**
   ```bash
   appium
   ```

### 🔧 Configuration

Edit `config.py` to customize settings:

```python
APPIUM_SERVER_ADDR = "http://127.0.0.1:4723"
CLOSE_SEND_FLOWER_BUTTON_XPATH = '//android.widget.ImageView[@resource-id="com.tantan.x:id/get_coin_dialog_layout_close"]'
CLOSE_MORE_RIGHT_SWIPE_BUTTON_XPATH = '//android.widget.TextView[@resource-id="com.tantan.x:id/right_swipe_power_dialog_2_confirm"]'
```

### 🎯 Usage

**Main automation script:**
```bash
python qianshou.py
```

### 📁 Project Structure

```
qianshou_app_automation/
├── qianshou.py          # Main automation class
├── qianshouauto.py      # Alternative automation script
├── config.py            # Configuration settings
├── girl_info.py         # User information data model
├── my_log.py            # Logging configuration
├── database/            # SQLite database storage
│   └── qianshou_girl_info.db
├── log_file/            # Log files organized by timestamp
└── __pycache__/         # Python cache files
```

### 📊 Database Schema

The SQLite database stores user information with the following fields:
- Personal details (nickname, age, height)
- Profile information (constellation, education, work)
- Location data (hometown, current city)
- Preferences (love targets, introduction)
- Metadata (certification status, like status, timestamp)

### 🔍 Key Classes

- **`QianShou`**: Main automation controller
- **`GirlInfo`**: User information data model
- **Logger**: Comprehensive logging system

### ⚠️ Disclaimer

This project is for educational and testing purposes only. Please ensure you comply with:
- Tantan's Terms of Service
- Local laws and regulations
- Ethical guidelines for automated testing
- User privacy and data protection laws

### 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### 📄 License

This project is for educational purposes. Please use responsibly and in accordance with applicable laws and terms of service.

---

## Chinese

### 📱 牵手应用自动化工具

这是一个基于 Appium 框架的牵手约会应用自动化测试工具，可以自动浏览用户资料、收集用户信息并执行滑动操作。

### ✨ 功能特性

- **自动化资料浏览**: 自动浏览用户资料
- **数据收集**: 提取并存储用户信息，包括：
  - 昵称、年龄、身高
  - 星座、学历、工作信息
  - 薪资、家乡、当前位置
  - 恋爱目标和个人简介
  - 实名认证状态
- **智能滑动**: 自动化喜欢/不喜欢操作
- **数据库存储**: 将收集的数据存储在 SQLite 数据库中
- **完整日志系统**: 详细的日志记录，支持文件和控制台输出
- **错误恢复**: 自动重连和错误处理

### 🛠️ 技术栈

- **Python 3.12+**
- **Appium** - 移动应用自动化
- **Selenium WebDriver** - Web 自动化框架
- **SQLite** - 本地数据库存储
- **PIL (Pillow)** - 图像处理
- **Pytesseract** - OCR 文字识别
- **lxml** - XML 解析

### 📋 环境要求

1. **Android 设备/模拟器** (Android 14+)
2. **Appium 服务器** 运行在 `http://127.0.0.1:4723`
3. **ADB (Android Debug Bridge)** 正确配置
4. **Tesseract OCR** 安装在 `C:\Program Files\Tesseract-OCR\tesseract.exe`
5. **探探应用** 已安装并登录设备

### 🚀 安装步骤

1. **克隆仓库**
   ```bash
   git clone <repository-url>
   cd qianshou_app_automation
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置 Tesseract OCR**
   - 下载并安装 Tesseract OCR
   - 确保安装路径为 `C:\Program Files\Tesseract-OCR\tesseract.exe`

5. **启动 Appium 服务器**
   ```bash
   appium
   ```

### 🔧 配置

编辑 `config.py` 自定义设置：

```python
APPIUM_SERVER_ADDR = "http://127.0.0.1:4723"
CLOSE_SEND_FLOWER_BUTTON_XPATH = '//android.widget.ImageView[@resource-id="com.tantan.x:id/get_coin_dialog_layout_close"]'
CLOSE_MORE_RIGHT_SWIPE_BUTTON_XPATH = '//android.widget.TextView[@resource-id="com.tantan.x:id/right_swipe_power_dialog_2_confirm"]'
```

### 🎯 使用方法

**主要自动化脚本：**
```bash
python qianshou.py
```


### 📁 项目结构

```
qianshou_app_automation/
├── qianshou.py          # 主要自动化类
├── qianshouauto.py      # 备用自动化脚本
├── config.py            # 配置设置
├── girl_info.py         # 用户信息数据模型
├── my_log.py            # 日志配置
├── database/            # SQLite 数据库存储
│   └── qianshou_girl_info.db
├── log_file/            # 按时间戳组织的日志文件
└── __pycache__/         # Python 缓存文件
```

### 📊 数据库结构

SQLite 数据库存储用户信息，包含以下字段：
- 个人详情（昵称、年龄、身高）
- 资料信息（星座、学历、工作）
- 位置数据（家乡、当前城市）
- 偏好设置（恋爱目标、简介）
- 元数据（认证状态、喜欢状态、时间戳）

### 🔍 核心类

- **`QianShou`**: 主要自动化控制器
- **`GirlInfo`**: 用户信息数据模型
- **Logger**: 完整的日志记录系统

### ⚠️ 免责声明

本项目仅用于教育和测试目的。请确保您遵守：
- 探探的服务条款
- 当地法律法规
- 自动化测试的道德准则
- 用户隐私和数据保护法律

### 🤝 贡献

1. Fork 本仓库
2. 创建您的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

### 📄 许可证

本项目仅用于教育目的。请负责任地使用，并遵守适用的法律和服务条款。

---

## 📞 联系方式 / Contact

如有问题或建议，请创建 Issue 或联系项目维护者。

For questions or suggestions, please create an Issue or contact the project maintainer.
