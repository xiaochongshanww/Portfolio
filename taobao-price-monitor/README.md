这个项目是一个使用爬虫监控淘宝商品价格变化的工具。

## 功能
- 通过Web界面添加、移除和查看监控的商品。
- 手动触发对单个商品的即时抓取。
- 后台定时自动监控所有商品的价格。
- 当价格发生变动时，通过邮件发送通知。
- 可通过UI配置代理服务器、收件人邮箱和监控频率。

## 如何运行

1.  **创建并激活虚拟环境:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **安装依赖:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **配置邮件通知 (可选):**
    为了能收到价格变动邮件，请在启动应用前设置以下环境变量。对于Gmail等邮箱，您可能需要使用“应用专用密码”。
    ```bash
    export SMTP_HOST=smtp.example.com
    export SMTP_PORT=465
    export SMTP_USER=your_email@example.com
    export SMTP_PASSWORD=your_password_or_app_password
    ```

4.  **在 VS Code 中启动:**
    直接使用已配置好的 "Python: Flask" 调试配置启动即可。

5.  **首次使用:**
    - 启动应用后，访问 `http://127.0.0.1:5000`。
    - 在Settings页面配置您的代理（如果需要）和收件人邮箱。
    - 在主页添加一个商品链接。
    - 点击"Scrape"按钮，在弹出的浏览器窗口中手动登录淘宝。登录信息会被自动保存以备后续使用。
