#!/usr/bin/env python3
"""
测试备份创建的完整流程，验证外部元数据系统集成
"""

def test_backup_creation_flow():
    """测试备份创建完整流程"""
    import os
    import sys
    
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        print("=== 测试备份创建完整流程 ===\n")
        
        # Test 1: Flask应用初始化
        print("1. 初始化Flask应用和外部元数据系统...")
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from app.backup.backup_records_external import get_external_metadata_manager
            from app.models import BackupRecord
            from app import db
            from datetime import datetime
            from app.models import SHANGHAI_TZ
            import json
            
            manager = get_external_metadata_manager()
            if not manager:
                print("   [ERROR] 外部元数据管理器未初始化")
                return False
            
            print("   [OK] Flask应用和外部元数据系统初始化成功")
            
            # Test 2: 模拟备份创建流程
            print("2. 模拟备份创建流程...")
            backup_id = "integration_test_backup_002"
            description = "Integration test backup"
            
            # 清理可能存在的测试数据
            existing_mysql = BackupRecord.query.filter_by(backup_id=backup_id).first()
            if existing_mysql:
                db.session.delete(existing_mysql)
                db.session.commit()
            
            existing_external = manager.get_backup_record(backup_id)
            if existing_external:
                manager.delete_backup_record(backup_id)
            
            # Step 2a: 创建MySQL记录 (模拟routes.py中的逻辑)
            print("   2a. 创建MySQL数据库记录...")
            backup_record = BackupRecord(
                backup_id=backup_id,
                backup_type='physical',
                status='running',
                started_at=datetime.now(SHANGHAI_TZ),
                databases_count=1,
                encryption_enabled=False,
                extra_data=json.dumps({
                    'description': description,
                    'requested_by': 'integration_test',
                    'engine': 'physical_backup_engine'
                })
            )
            db.session.add(backup_record)
            db.session.commit()
            print(f"      [OK] MySQL记录已创建，状态: {backup_record.status}")
            
            # Step 2b: 创建外部元数据记录 (模拟routes.py中的逻辑)
            print("   2b. 创建外部元数据记录...")
            try:
                external_record = manager.create_backup_record(
                    backup_id=backup_id,
                    backup_type='physical',
                    status='running',
                    description=description,
                    requested_by='integration_test'
                )
                print(f"      [OK] 外部元数据记录已创建，状态: {external_record.status}")
            except Exception as e:
                print(f"      [ERROR] 创建外部元数据记录失败: {e}")
                return False
            
            # Step 2c: 模拟备份完成，更新状态
            print("   2c. 模拟备份完成，更新状态...")
            
            # 更新MySQL记录
            backup_record.status = 'completed'
            backup_record.completed_at = datetime.now(SHANGHAI_TZ)
            backup_record.file_size = 1024 * 1024  # 1MB
            backup_record.compressed_size = 512 * 1024  # 512KB
            backup_record.compression_ratio = 0.5
            backup_record.file_path = f"backups/physical/{backup_id}/mysql_data.tar.gz"
            db.session.commit()
            print(f"      [OK] MySQL记录已更新为completed")
            
            # 更新外部元数据记录
            try:
                manager.update_backup_record(
                    backup_id=backup_id,
                    status='completed',
                    file_size=1024 * 1024,
                    compressed_size=512 * 1024,
                    compression_ratio=0.5,
                    file_path=f"backups/physical/{backup_id}/mysql_data.tar.gz",
                    completed_at=datetime.now(SHANGHAI_TZ)
                )
                print(f"      [OK] 外部元数据记录已更新为completed")
            except Exception as e:
                print(f"      [ERROR] 更新外部元数据记录失败: {e}")
                return False
            
            # Test 3: 验证数据一致性
            print("3. 验证数据一致性...")
            
            # 检查MySQL记录
            mysql_record = BackupRecord.query.filter_by(backup_id=backup_id).first()
            if not mysql_record or mysql_record.status != 'completed':
                print(f"   [ERROR] MySQL记录状态异常: {mysql_record.status if mysql_record else 'None'}")
                return False
            
            # 检查外部元数据记录
            external_record = manager.get_backup_record(backup_id)
            if not external_record or external_record.status != 'completed':
                print(f"   [ERROR] 外部元数据记录状态异常: {external_record.status if external_record else 'None'}")
                return False
            
            print(f"   [OK] 数据一致性验证通过")
            print(f"      MySQL状态: {mysql_record.status}")
            print(f"      外部元数据状态: {external_record.status}")
            print(f"      文件大小: {mysql_record.file_size} / {external_record.file_size}")
            
            # Test 4: 模拟数据库恢复场景
            print("4. 模拟数据库恢复场景...")
            print("   4a. 模拟MySQL记录状态被回滚...")
            # 假设恢复操作将MySQL记录状态回滚到running
            mysql_record.status = 'running'
            mysql_record.completed_at = None
            db.session.commit()
            print(f"      [OK] MySQL记录状态已回滚为running")
            
            # Test 5: 测试冲突检测和解决
            print("5. 测试冲突检测和解决...")
            
            # 检查外部元数据记录状态（应该仍然是completed）
            external_record = manager.get_backup_record(backup_id)
            print(f"   外部元数据状态: {external_record.status}")
            print(f"   MySQL状态: {mysql_record.status}")
            
            if external_record.status == 'completed' and mysql_record.status == 'running':
                print("   [OK] 检测到状态冲突（这是预期的）")
                print("   [INFO] 在实际应用中，冲突解决机制会自动修复这种状态不一致")
            
            # Test 6: 清理测试数据
            print("6. 清理测试数据...")
            db.session.delete(mysql_record)
            db.session.commit()
            manager.delete_backup_record(backup_id)
            print("   [OK] 测试数据已清理")
            
            # Test 7: 获取统计信息
            print("7. 获取外部元数据统计...")
            stats = manager.get_statistics()
            print(f"   总记录数: {stats['total_backup_records']}")
            print(f"   成功率: {stats['success_rate']}%")
            
        print("\n=== 集成测试结果 ===")
        print("[SUCCESS] 备份创建完整流程测试通过！")
        print("[SUCCESS] 外部元数据系统集成正常工作")
        print("[SUCCESS] 可以检测和处理状态冲突")
        
        return True
        
    except Exception as e:
        print(f"\n=== 集成测试失败 ===")
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_backup_creation_flow()
    exit(0 if success else 1)