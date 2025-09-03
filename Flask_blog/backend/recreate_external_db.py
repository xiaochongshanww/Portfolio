#!/usr/bin/env python3
"""
重新创建外部元数据数据库以匹配当前模型
"""

def recreate_external_database():
    """重新创建外部元数据数据库"""
    import os
    import sys
    import time
    from pathlib import Path
    
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        print("=== 重新创建外部元数据数据库 ===\n")
        
        # 数据库文件路径
        base_dir = Path(__file__).parent
        metadata_dir = base_dir / 'metadata'
        db_file = metadata_dir / 'backup_external.db'
        
        print(f"数据库文件路径: {db_file}")
        
        # 如果文件存在，尝试删除
        if db_file.exists():
            print("删除现有数据库文件...")
            try:
                # 等待文件句柄释放
                time.sleep(1)
                os.remove(db_file)
                print("   [OK] 旧数据库文件已删除")
            except Exception as e:
                print(f"   [WARNING] 无法删除旧文件: {e}")
                # 尝试重命名
                backup_file = db_file.with_suffix('.db.bak')
                try:
                    db_file.rename(backup_file)
                    print(f"   [OK] 旧文件已备份为: {backup_file}")
                except Exception as e2:
                    print(f"   [ERROR] 无法备份文件: {e2}")
                    return False
        
        # 使用独立的SQLAlchemy创建新数据库
        print("创建新的数据库结构...")
        from sqlalchemy import create_engine
        from app.backup.backup_records_external import external_db
        
        # 创建数据库引擎
        db_uri = f"sqlite:///{db_file}"
        engine = create_engine(db_uri, echo=False)
        
        # 创建所有表
        external_db.metadata.create_all(engine)
        
        print("   [OK] 数据库表结构已创建")
        
        # 验证表结构
        print("验证数据库表结构...")
        import sqlite3
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        
        # 检查表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"   创建的表: {[table[0] for table in tables]}")
        
        # 检查backup_records_external表的列
        cursor.execute("PRAGMA table_info(backup_records_external)")
        columns = cursor.fetchall()
        print(f"   backup_records_external表的列数: {len(columns)}")
        
        # 显示前几个列名
        column_names = [col[1] for col in columns]
        print(f"   列名: {column_names[:10]}...")  # 只显示前10个列名
        
        conn.close()
        
        print(f"\n[SUCCESS] 外部元数据数据库重新创建成功!")
        print(f"数据库大小: {os.path.getsize(db_file)} bytes")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] 重新创建数据库失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = recreate_external_database()
    exit(0 if success else 1)