#!/usr/bin/env python3
"""
创建外部元数据SQLite数据库和表结构
"""

def create_external_database():
    """创建外部元数据数据库"""
    import os
    from pathlib import Path
    import sqlite3
    
    try:
        print("Creating external metadata database...")
        
        # 确保metadata目录存在
        base_dir = Path(__file__).parent
        metadata_dir = base_dir / 'metadata'
        metadata_dir.mkdir(exist_ok=True)
        
        # 数据库文件路径
        db_file = metadata_dir / 'backup_external.db'
        print(f"Database file: {db_file}")
        
        # 如果数据库文件已存在，删除它以重新创建
        if db_file.exists():
            print("Removing existing database file...")
            os.remove(db_file)
        
        # 创建数据库连接
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        
        print("Creating database tables...")
        
        # 创建backup_records_external表
        cursor.execute('''
        CREATE TABLE backup_records_external (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            backup_id VARCHAR(255) UNIQUE NOT NULL,
            backup_type VARCHAR(50) NOT NULL DEFAULT 'physical',
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            sync_status VARCHAR(50) NOT NULL DEFAULT 'synced',
            conflict_reason TEXT,
            
            -- 时间字段
            created_at DATETIME NOT NULL,
            started_at DATETIME,
            completed_at DATETIME,
            last_sync_at DATETIME,
            
            -- 文件信息
            file_path TEXT,
            file_size INTEGER DEFAULT 0,
            compressed_size INTEGER DEFAULT 0,
            compression_ratio REAL DEFAULT 0,
            checksum VARCHAR(255),
            
            -- 备份信息
            databases_count INTEGER DEFAULT 1,
            encryption_enabled BOOLEAN DEFAULT FALSE,
            description TEXT,
            requested_by VARCHAR(255),
            error_message TEXT,
            
            -- 额外数据
            extra_data_json TEXT
        )
        ''')
        
        # 创建restore_records_external表
        cursor.execute('''
        CREATE TABLE restore_records_external (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restore_id VARCHAR(255) UNIQUE NOT NULL,
            backup_record_id INTEGER,
            restore_type VARCHAR(50) NOT NULL DEFAULT 'full',
            status VARCHAR(50) NOT NULL DEFAULT 'pending',
            sync_status VARCHAR(50) NOT NULL DEFAULT 'synced',
            conflict_reason TEXT,
            
            -- 时间字段
            created_at DATETIME NOT NULL,
            started_at DATETIME,
            completed_at DATETIME,
            last_sync_at DATETIME,
            
            -- 恢复信息
            progress INTEGER DEFAULT 0,
            status_message TEXT,
            error_message TEXT,
            restored_databases_count INTEGER DEFAULT 0,
            restore_options_json TEXT,
            requested_by VARCHAR(255),
            
            -- 额外数据
            extra_data_json TEXT
        )
        ''')
        
        # 创建sync_logs_external表
        cursor.execute('''
        CREATE TABLE sync_logs_external (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation VARCHAR(100) NOT NULL,
            record_type VARCHAR(50) NOT NULL,
            record_id VARCHAR(255) NOT NULL,
            sync_direction VARCHAR(50) NOT NULL DEFAULT 'mysql_to_sqlite',
            conflict_resolved BOOLEAN DEFAULT FALSE,
            file_exists BOOLEAN,
            details_json TEXT,
            created_at DATETIME NOT NULL
        )
        ''')
        
        # 创建索引以提高查询性能
        print("Creating database indexes...")
        
        # backup_records_external索引
        cursor.execute('CREATE INDEX idx_backup_records_backup_id ON backup_records_external (backup_id)')
        cursor.execute('CREATE INDEX idx_backup_records_status ON backup_records_external (status)')
        cursor.execute('CREATE INDEX idx_backup_records_sync_status ON backup_records_external (sync_status)')
        cursor.execute('CREATE INDEX idx_backup_records_created_at ON backup_records_external (created_at)')
        
        # restore_records_external索引
        cursor.execute('CREATE INDEX idx_restore_records_restore_id ON restore_records_external (restore_id)')
        cursor.execute('CREATE INDEX idx_restore_records_status ON restore_records_external (status)')
        cursor.execute('CREATE INDEX idx_restore_records_backup_record_id ON restore_records_external (backup_record_id)')
        
        # sync_logs_external索引
        cursor.execute('CREATE INDEX idx_sync_logs_operation ON sync_logs_external (operation)')
        cursor.execute('CREATE INDEX idx_sync_logs_record_type ON sync_logs_external (record_type)')
        cursor.execute('CREATE INDEX idx_sync_logs_record_id ON sync_logs_external (record_id)')
        cursor.execute('CREATE INDEX idx_sync_logs_created_at ON sync_logs_external (created_at)')
        
        # 提交更改
        conn.commit()
        print("Database tables and indexes created successfully!")
        
        # 验证表是否创建成功
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Created tables: {[table[0] for table in tables]}")
        
        # 关闭连接
        conn.close()
        
        print(f"External metadata database created at: {db_file}")
        print(f"Database file size: {os.path.getsize(db_file)} bytes")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to create external database: {e}")
        return False

if __name__ == "__main__":
    success = create_external_database()
    if success:
        print("\n[SUCCESS] External metadata database setup completed!")
    else:
        print("\n[FAILED] External metadata database setup failed!")
    exit(0 if success else 1)