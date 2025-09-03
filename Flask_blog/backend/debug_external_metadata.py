#!/usr/bin/env python3
"""
诊断外部元数据系统集成问题
"""

def debug_external_metadata_system():
    """诊断外部元数据系统"""
    import os
    import sys
    
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        print("=== 外部元数据系统诊断 ===\n")
        
        # Test 1: Flask应用初始化
        print("1. 测试Flask应用初始化...")
        from app import create_app
        app = create_app()
        print("   [OK] Flask应用创建成功")
        
        # Test 2: 在应用上下文中检查外部元数据管理器
        print("2. 检查外部元数据管理器初始化状态...")
        with app.app_context():
            from app.backup.backup_records_external import get_external_metadata_manager
            manager = get_external_metadata_manager()
            
            if manager:
                print("   [OK] 外部元数据管理器已初始化")
                print(f"      管理器类型: {type(manager)}")
                print(f"      数据库路径: {manager.db_path}")
                
                # Test 3: 检查数据库连接
                print("3. 测试数据库连接...")
                try:
                    stats = manager.get_statistics()
                    print(f"   [OK] 数据库连接正常")
                    print(f"      统计信息: {stats}")
                except Exception as e:
                    print(f"   [ERROR] 数据库连接失败: {e}")
                    return False
                
                # Test 4: 测试创建备份记录
                print("4. 测试创建备份记录...")
                try:
                    test_backup_id = "debug_test_backup_001"
                    
                    # 删除可能存在的测试记录
                    existing = manager.get_backup_record(test_backup_id)
                    if existing:
                        manager.delete_backup_record(test_backup_id)
                        print("   [INFO] 已删除现有测试记录")
                    
                    # 创建测试记录
                    record = manager.create_backup_record(
                        backup_id=test_backup_id,
                        backup_type="physical",
                        status="completed",
                        description="Debug test backup",
                        requested_by="debug_script"
                    )
                    print(f"   [OK] 测试记录创建成功: {record.backup_id}")
                    
                    # 验证记录
                    retrieved = manager.get_backup_record(test_backup_id)
                    if retrieved:
                        print(f"   [OK] 记录验证成功, ID: {retrieved.backup_id}")
                    else:
                        print("   [ERROR] 记录创建后无法检索")
                        return False
                    
                    # 获取最新统计
                    stats_after = manager.get_statistics()
                    print(f"   [OK] 创建后统计: {stats_after['total_backup_records']} 条记录")
                    
                    # 清理测试记录
                    manager.delete_backup_record(test_backup_id)
                    print("   [OK] 测试记录已清理")
                    
                except Exception as e:
                    print(f"   [ERROR] 创建备份记录失败: {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            else:
                print("   [ERROR] 外部元数据管理器未初始化 (返回None)")
                return False
        
        print("\n=== 诊断结果 ===")
        print("[SUCCESS] 外部元数据系统工作正常!")
        print("问题可能在于备份创建时的实际调用流程")
        
        return True
        
    except Exception as e:
        print(f"\n=== 诊断失败 ===")
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_external_metadata_system()
    exit(0 if success else 1)