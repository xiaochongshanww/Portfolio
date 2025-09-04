#!/usr/bin/env python3
"""
数据库结构修复脚本
解决迁移文件静默失败导致的数据库结构不一致问题
"""

import os
import sys
import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_url():
    """从环境变量获取数据库URL"""
    return os.getenv('DATABASE_URL', 'mysql+pymysql://blog:blog@localhost:3306/blog?charset=utf8mb4')

def check_column_exists(engine, table_name, column_name):
    """检查列是否存在"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def check_index_exists(engine, table_name, index_name):
    """检查索引是否存在"""
    inspector = inspect(engine)
    indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
    return index_name in indexes

def fix_views_count_column(engine):
    """修复 views_count 列和索引"""
    logger.info("🔍 检查 articles.views_count 列...")
    
    if not check_column_exists(engine, 'articles', 'views_count'):
        logger.info("❌ views_count 列不存在，正在添加...")
        try:
            with engine.connect() as conn:
                # 添加列
                conn.execute(text("""
                    ALTER TABLE articles 
                    ADD COLUMN views_count INT NOT NULL DEFAULT 0
                """))
                conn.commit()
                logger.info("✅ 成功添加 views_count 列")
        except SQLAlchemyError as e:
            logger.error(f"❌ 添加 views_count 列失败: {e}")
            return False
    else:
        logger.info("✅ views_count 列已存在")
    
    # 检查索引
    if not check_index_exists(engine, 'articles', 'ix_articles_views_count'):
        logger.info("❌ views_count 索引不存在，正在创建...")
        try:
            with engine.connect() as conn:
                conn.execute(text("""
                    CREATE INDEX ix_articles_views_count ON articles (views_count)
                """))
                conn.commit()
                logger.info("✅ 成功创建 views_count 索引")
        except SQLAlchemyError as e:
            logger.error(f"❌ 创建索引失败: {e}")
            return False
    else:
        logger.info("✅ views_count 索引已存在")
    
    return True

def check_performance_indexes(engine):
    """检查性能优化索引"""
    logger.info("🔍 检查性能优化索引...")
    
    expected_indexes = [
        ('articles', 'ix_articles_status_published_at'),
        ('articles', 'ix_articles_author_published_at'), 
        ('articles', 'ix_articles_category_published_at'),
        ('comments', 'ix_comments_article_status_created'),
        ('article_likes', 'ix_article_likes_article'),
        ('article_bookmarks', 'ix_article_bookmarks_article'),
    ]
    
    missing_indexes = []
    for table, index_name in expected_indexes:
        if not check_index_exists(engine, table, index_name):
            missing_indexes.append((table, index_name))
            logger.warning(f"⚠️  缺少索引: {table}.{index_name}")
        else:
            logger.info(f"✅ 索引存在: {table}.{index_name}")
    
    return missing_indexes

def create_missing_indexes(engine, missing_indexes):
    """创建缺失的索引"""
    index_definitions = {
        'ix_articles_status_published_at': "CREATE INDEX ix_articles_status_published_at ON articles (status, published_at)",
        'ix_articles_author_published_at': "CREATE INDEX ix_articles_author_published_at ON articles (author_id, published_at)",
        'ix_articles_category_published_at': "CREATE INDEX ix_articles_category_published_at ON articles (category_id, published_at)",
        'ix_comments_article_status_created': "CREATE INDEX ix_comments_article_status_created ON comments (article_id, status, created_at)",
        'ix_article_likes_article': "CREATE INDEX ix_article_likes_article ON article_likes (article_id)",
        'ix_article_bookmarks_article': "CREATE INDEX ix_article_bookmarks_article ON article_bookmarks (article_id)",
    }
    
    for table, index_name in missing_indexes:
        if index_name in index_definitions:
            logger.info(f"📝 创建索引: {index_name}")
            try:
                with engine.connect() as conn:
                    conn.execute(text(index_definitions[index_name]))
                    conn.commit()
                    logger.info(f"✅ 成功创建索引: {index_name}")
            except SQLAlchemyError as e:
                logger.error(f"❌ 创建索引失败 {index_name}: {e}")

def generate_database_report(engine):
    """生成数据库结构报告"""
    logger.info("📊 生成数据库结构报告...")
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    report = []
    report.append("=" * 50)
    report.append("数据库结构报告")
    report.append("=" * 50)
    
    for table in ['articles', 'users', 'comments', 'categories', 'tags']:
        if table in tables:
            report.append(f"\n📋 表: {table}")
            
            # 列信息
            columns = inspector.get_columns(table)
            report.append("  列:")
            for col in columns:
                report.append(f"    - {col['name']} ({col['type']})")
            
            # 索引信息
            indexes = inspector.get_indexes(table)
            if indexes:
                report.append("  索引:")
                for idx in indexes:
                    report.append(f"    - {idx['name']}: {idx['column_names']}")
    
    report_text = "\n".join(report)
    logger.info(f"\n{report_text}")
    
    # 保存报告到文件
    with open('database_structure_report.txt', 'w', encoding='utf-8') as f:
        f.write(report_text)
    logger.info("📁 报告已保存到: database_structure_report.txt")

def main():
    """主函数"""
    logger.info("🚀 开始数据库结构修复...")
    
    database_url = get_database_url()
    logger.info(f"📡 连接数据库: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
    
    try:
        engine = create_engine(database_url)
        
        # 测试连接
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ 数据库连接成功")
        
        # 修复 views_count 列
        if fix_views_count_column(engine):
            logger.info("✅ views_count 修复完成")
        else:
            logger.error("❌ views_count 修复失败")
            return False
        
        # 检查性能索引
        missing_indexes = check_performance_indexes(engine)
        if missing_indexes:
            logger.info(f"⚠️  发现 {len(missing_indexes)} 个缺失的索引")
            create_missing_indexes(engine, missing_indexes)
        
        # 生成报告
        generate_database_report(engine)
        
        logger.info("🎉 数据库结构修复完成!")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"❌ 数据库连接或操作失败: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 未知错误: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)