# GEMINI_zh.md

## 项目概述

本项目是一个淘宝价格监控工具。它允许用户跟踪淘宝（一个流行的中国电子商务网站）上的商品价格。该应用程序提供了一个 Web 界面来添加、删除和查看被监控的商品。它具有后台调度程序，可定期自动抓取最新价格。当检测到价格变化时，应用程序会向用户发送电子邮件通知。

该项目采用以下技术构建：

*   **后端：** Python with Flask
*   **网络爬虫：** Playwright with the `playwright-stealth` library to avoid bot detection
*   **数据库：** SQLite to store product information, price history, and application settings
*   **调度：** The `schedule` library is used for periodic scraping.
*   **前端：** HTML, CSS, and JavaScript are used for the web interface.

## 构建和运行

要运行该项目，请按照以下步骤操作：

1.  **创建并激活虚拟环境：**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **安装依赖项：**

    ```bash
    pip install -r requirements.txt
    ```

3.  **配置电子邮件通知（可选）：**

    要接收价格变动通知，请在启动应用程序之前设置以下环境变量。对于 Gmail，您可能需要使用“应用密码”。

    ```bash
    export SMTP_HOST=smtp.example.com
    export SMTP_PORT=465
    export SMTP_USER=your_email@example.com
    export SMTP_PASSWORD=your_password_or_app_password
    ```

4.  **运行应用程序：**

    ```bash
    python app.py
    ```

    该应用程序将在 `http://127.0.0.1:5000` 上可用。

## 开发约定

*   **代码风格：** 代码遵循 Python 的 PEP 8 风格指南。
*   **日志记录：** 应用程序使用 `logging` 模块记录重要事件。日志存储在 `logs` 目录中，每次运行都会创建一个新的子目录。
*   **数据库：** 数据库模式在 `database.py` 中定义。数据库在应用程序启动时初始化。
*   **爬虫：** 网络爬虫逻辑位于 `scraper.py` 中。它使用 Playwright 控制无头浏览器并抓取商品信息。
*   **通知：** 电子邮件通知逻辑位于 `notifier.py` 中。它使用 `smtplib` 发送电子邮件。
*   **前端：** 前端模板位于 `templates` 目录中。CSS 和 JavaScript 等静态资产位于 `static` 目录中。
