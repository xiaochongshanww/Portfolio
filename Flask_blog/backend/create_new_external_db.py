#!/usr/bin/env python3
"""
创建新的外部元数据数据库
"""

def create_new_external_database():
    """创建新的外部元数据数据库"""
    import os
    import sys
    from pathlib import Path
    
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        print("=== 创建新的外部元数据数据库 ===\n")
        
        # 使用新的数据库文件名
        base_dir = Path(__file__).parent
        metadata_dir = base_dir / 'metadata'
        new_db_file = metadata_dir / 'backup_external_v2.db'
        
        print(f"新数据库文件路径: {new_db_file}")
        
        # 确保目录存在
        metadata_dir.mkdir(exist_ok=True)
        
        # 如果新文件存在，删除它
        if new_db_file.exists():
            os.remove(new_db_file)
            print("   已删除现有新数据库文件")
        
        # 使用独立的SQLAlchemy创建新数据库
        print("创建新的数据库结构...")
        from sqlalchemy import create_engine
        from app.backup.backup_records_external import external_db
        
        # 创建数据库引擎
        db_uri = f"sqlite:///{new_db_file}"
        engine = create_engine(db_uri, echo=False)
        
        # 创建所有表
        external_db.metadata.create_all(engine)
        
        print("   [OK] 数据库表结构已创建")
        
        # 验证表结构
        print("验证数据库表结构...")
        import sqlite3
        conn = sqlite3.connect(str(new_db_file))
        cursor = conn.cursor()
        
        # 检查表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"   创建的表: {[table[0] for table in tables]}")
        
        # 检查backup_records_external表的列
        cursor.execute("PRAGMA table_info(backup_records_external)")
        columns = cursor.fetchall()
        print(f"   backup_records_external表的列数: {len(columns)}")
        
        # 显示所有列名
        column_names = [col[1] for col in columns]
        print(f"   列名: {column_names}")
        
        conn.close()
        engine.dispose()
        
        print(f"\n[SUCCESS] 新的外部元数据数据库创建成功!")
        print(f"数据库大小: {os.path.getsize(new_db_file)} bytes")
        print(f"文件位置: {new_db_file}")
        
        # 现在更新外部元数据管理器使用新数据库
        print("\n更新外部元数据管理器配置...")
        
        # 修改默认数据库路径
        return str(new_db_file)
        
    except Exception as e:
        print(f"\n[ERROR] 创建数据库失败: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    db_path = create_new_external_database()
    if db_path:
        print(f"\n请更新外部元数据系统使用新数据库: {db_path}")
    else:
        exit(1)