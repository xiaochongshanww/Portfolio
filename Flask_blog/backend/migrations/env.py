from __future__ import with_statement
import logging
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# 将 app 加入路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from app import create_app, db  # noqa: E402
from app.models import *  # noqa: F401,F403

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

target_metadata = db.metadata

def run_migrations_offline():
    url = os.getenv('DATABASE_URL', 'sqlite:///dev.db')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    app = create_app()
    with app.app_context():
        try:
            logger.info(f"正在连接数据库: {db.engine.url}")  # 打印数据库连接信息
            connectable = db.engine.connect()
            context.configure(
                connection=connectable,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
            )
        except Exception as e:
            logger.error("数据库连接失败: %s", e)
            return

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    logger.info("以离线模式运行迁移")
    run_migrations_offline()
else:
    logger.info("以在线模式运行迁移")
    run_migrations_online()
