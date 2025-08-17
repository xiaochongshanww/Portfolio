from app import create_app

# 专用：不使用自动重载，便于脚本化/生成 OpenAPI
app = create_app()

if __name__ == '__main__':
    # 关闭 reloader，避免父进程退出导致外部检测不到服务
    app.run(debug=False, use_reloader=False)
