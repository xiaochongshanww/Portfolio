import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # 使用 Alembic 迁移管理数据库结构，参见 docs/backend/overview.md 与 migrations/README_migrations.md
    #
    # debug reloader 教训(2026-08):调试期间后台启动的 run.py 因 bash -c "... &"
    # 未 wait 变成孤儿,父进程死后 reloader 子进程陷入 stat 轮询死循环,
    # 4 个进程抢听 5000 端口,单进程 ~60% CPU,持续 5 天把 8 核跑满。
    # 规则:
    # 1. host 绑定 127.0.0.1(本机调试);需要局域网访问时用 FLASK_HOST 覆盖;
    # 2. reloader 默认关闭,需要热重载时显式 FLASK_RELOADER=1 启动;
    # 3. 后台启动务必用 start-backend.ps1(带 PID 记录与 stop-backend.ps1 成对清理),
    #    不要直接 bash -c "... &"。
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        debug=debug,
        use_reloader=os.getenv("FLASK_RELOADER", "0") == "1",
    )
