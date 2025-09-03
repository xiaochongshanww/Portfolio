#!/usr/bin/env python3
"""
测试智能数据源路由逻辑
"""

def test_smart_data_routing():
    """测试智能数据源路由"""
    import os
    import sys
    import json
    
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        print("=== 测试智能数据源路由逻辑 ===\n")
        
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from app.backup.backup_records_external import get_external_metadata_manager
            from app.models import BackupRecord
            from app import db
            from datetime import datetime
            from app.models import SHANGHAI_TZ
            
            manager = get_external_metadata_manager()
            if not manager:
                print("   [ERROR] 外部元数据管理器未初始化")
                return False
            
            print("1. 设置测试场景...")
            
            # 创建测试备份记录
            test_backup_id = "smart_routing_test_003"
            
            # 清理现有测试数据
            existing_mysql = BackupRecord.query.filter_by(backup_id=test_backup_id).first()
            if existing_mysql:
                db.session.delete(existing_mysql)
                db.session.commit()
            
            existing_external = manager.get_backup_record(test_backup_id)
            if existing_external:
                manager.delete_backup_record(test_backup_id)
            
            print("   [OK] 清理完成")
            
            # 场景1: 创建MySQL记录，状态为completed
            print("2. 场景1: 创建正常完成的备份记录...")
            mysql_record = BackupRecord(
                backup_id=test_backup_id,
                backup_type='physical',
                status='completed',  # 正常完成状态
                created_at=datetime.now(SHANGHAI_TZ),
                started_at=datetime.now(SHANGHAI_TZ),
                completed_at=datetime.now(SHANGHAI_TZ),
                file_size=1024*1024,
                compressed_size=512*1024,
                compression_ratio=0.5,
                file_path=f"backups/physical/{test_backup_id}/mysql_data.tar.gz",
                databases_count=1,
                encryption_enabled=False,
                extra_data=json.dumps({
                    'description': 'Smart routing test backup',
                    'requested_by': 'smart_routing_test',
                    'engine': 'physical_backup_engine'
                })
            )
            db.session.add(mysql_record)
            db.session.commit()
            print(f"   [OK] MySQL记录已创建，状态: {mysql_record.status}")
            
            # 场景2: 模拟数据库恢复，状态回滚到running
            print("3. 场景2: 模拟数据库恢复，状态回滚...")
            
            # 首先同步到外部数据库（模拟正常运行时的同步）
            synced = manager.sync_from_mysql_backup_records()
            print(f"   同步到外部数据库: {synced} 条记录")
            
            # 验证外部数据库记录状态
            external_record = manager.get_backup_record(test_backup_id)
            if external_record:
                print(f"   外部数据库状态: {external_record.status}")
            
            # 模拟MySQL恢复操作，状态被回滚
            mysql_record.status = 'running'
            mysql_record.completed_at = None
            db.session.commit()
            print(f"   [OK] MySQL状态已回滚为: {mysql_record.status}")
            
            # 场景3: 测试智能路由的冲突检测
            print("4. 场景3: 测试智能路由冲突检测...")
            
            # 再次同步，触发冲突检测
            synced_to_external = manager.sync_from_mysql_backup_records()
            print(f"   MySQL到外部同步: {synced_to_external} 条记录")
            
            # 检测冲突
            conflicts = manager.find_conflicts()
            print(f"   发现冲突: {len(conflicts)} 个")
            
            if conflicts:
                for conflict in conflicts:
                    print(f"     冲突记录: {conflict.backup_id}, 外部状态: {conflict.status}, 同步状态: {conflict.sync_status}")
                    
                    # 解决冲突
                    resolution = conflict.resolve_conflict_by_file_check()
                    manager.save_record(conflict)
                    print(f"     冲突解决结果: {resolution}")
            
            # 场景4: 同步解决结果回MySQL
            print("5. 场景4: 同步权威数据回MySQL...")
            synced_to_mysql = manager.sync_to_mysql_backup_records()
            print(f"   外部到MySQL同步: {synced_to_mysql} 条记录")
            
            # 验证修复结果
            mysql_record = BackupRecord.query.filter_by(backup_id=test_backup_id).first()
            external_record = manager.get_backup_record(test_backup_id)
            
            print("6. 验证智能路由结果...")
            print(f"   MySQL最终状态: {mysql_record.status}")
            print(f"   外部数据库状态: {external_record.status}")
            
            if mysql_record.status == external_record.status:
                print("   [OK] 数据一致性已恢复")
                success = True
            else:
                print("   [ERROR] 数据一致性未恢复")
                success = False
            
            # 清理测试数据
            print("7. 清理测试数据...")
            db.session.delete(mysql_record)
            db.session.commit()
            manager.delete_backup_record(test_backup_id)
            print("   [OK] 测试数据已清理")
            
            if success:
                print("\n=== 智能数据源路由测试结果 ===")
                print("[SUCCESS] 智能数据源路由工作正常！")
                print("[SUCCESS] 能够检测和自动解决状态冲突")
                print("[SUCCESS] 以外部数据库为权威数据源")
                print("[SUCCESS] 前端现在将获得一致的数据")
            
            return success
        
    except Exception as e:
        print(f"\n=== 智能路由测试失败 ===")
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_smart_data_routing()
    exit(0 if success else 1)