from app import create_app

app = create_app()

if __name__ == '__main__':
    # 使用 Alembic 迁移管理数据库结构，参见 README 与 migrations/README_migrations.md
    app.run(debug=True)

