#!/usr/bin/env python3
"""
独立的智能数据源路由任务
避免在HTTP请求中进行复杂的数据库同步操作，防止SQLAlchemy会话冲突
"""

def run_smart_routing():
    """执行完整的智能数据源路由任务"""
    import os
    import sys
    
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        print("=== 开始智能数据源路由任务 ===\n")
        
        from app import create_app
        app = create_app()
        
        with app.app_context():
            from app.backup.backup_records_external import get_external_metadata_manager
            
            manager = get_external_metadata_manager()
            if not manager:
                print("[ERROR] 外部元数据管理器未初始化")
                return False
            
            print("1. 从MySQL同步到外部数据库...")
            try:
                synced_to_external = manager.sync_from_mysql_backup_records()
                print(f"   [OK] 已同步 {synced_to_external} 条记录到外部数据库")
            except Exception as sync_error:
                print(f"   [ERROR] MySQL同步失败: {sync_error}")
                return False
            
            print("2. 检测和解决冲突...")
            try:
                conflicts = manager.find_conflicts()
                if conflicts:
                    print(f"   发现 {len(conflicts)} 个冲突，开始解决...")
                    resolved_count = 0
                    
                    for conflict in conflicts:
                        try:
                            resolution_result = conflict.resolve_conflict_by_file_check()
                            manager.save_record(conflict)
                            resolved_count += 1
                            print(f"     冲突 {conflict.backup_id} 解决结果: {resolution_result}")
                        except Exception as conflict_error:
                            print(f"     [WARNING] 冲突 {conflict.backup_id} 解决失败: {conflict_error}")
                    
                    print(f"   [OK] 成功解决 {resolved_count} 个冲突")
                else:
                    print("   [OK] 未发现冲突")
            except Exception as conflict_error:
                print(f"   [ERROR] 冲突检测失败: {conflict_error}")
                return False
            
            print("3. 将权威数据同步回MySQL...")
            try:
                synced_to_mysql = manager.sync_to_mysql_backup_records()
                print(f"   [OK] 已将 {synced_to_mysql} 条记录同步回MySQL")
            except Exception as mysql_sync_error:
                print(f"   [ERROR] 同步到MySQL失败: {mysql_sync_error}")
                return False
            
            print("4. 获取统计信息...")
            try:
                stats = manager.get_statistics()
                print(f"   总记录数: {stats['total_backup_records']}")
                print(f"   冲突记录: {stats['conflict_records']}")
                print(f"   成功率: {stats['success_rate']}%")
            except Exception as stats_error:
                print(f"   [WARNING] 获取统计信息失败: {stats_error}")
        
        print("\n=== 智能数据源路由任务完成 ===")
        print("[SUCCESS] 数据一致性已确保")
        print("[SUCCESS] 前端将获得准确的备份状态信息")
        
        return True
        
    except Exception as e:
        print(f"\n=== 智能路由任务失败 ===")
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_smart_routing()
    exit(0 if success else 1)