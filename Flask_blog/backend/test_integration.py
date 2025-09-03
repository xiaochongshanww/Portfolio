#!/usr/bin/env python3
"""
Integration test for external metadata system
"""

def test_external_metadata_integration():
    """Test the external metadata system integration"""
    import os
    import sys
    
    # Add current directory to Python path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        print("Testing external metadata system integration...")
        
        # Test 1: Import modules
        print("1. Testing module imports...")
        from app.backup.backup_records_external import (
            BackupRecordExternal, 
            ExternalMetadataManager,
            init_external_metadata_system
        )
        print("   [OK] Modules imported successfully")
        
        # Test 2: Create manager instance
        print("2. Testing manager creation...")
        db_path = "sqlite:///./test_external_metadata.db"
        
        # Clean up any existing test database
        file_path = "./test_external_metadata.db"
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Create manager without Flask app (standalone mode)
        manager = ExternalMetadataManager(app=None, db_path=db_path)
        print("   [OK] External metadata manager created")
        
        # Test 3: Create a test backup record
        print("3. Testing backup record creation...")
        backup_id = "test_integration_backup_001"
        manager.create_backup_record(
            backup_id=backup_id,
            backup_type="physical",
            status="completed",
            description="Integration test backup",
            requested_by="integration_test"
        )
        print("   [OK] Backup record created")
        
        # Test 4: Query the record
        print("4. Testing record query...")
        record = manager.get_backup_record(backup_id)
        if record:
            print(f"   [OK] Record retrieved: {record.backup_id}")
            print(f"      Status: {record.status}")
            print(f"      Type: {record.backup_type}")
        else:
            raise Exception("Record not found")
        
        # Test 5: Get statistics
        print("5. Testing statistics...")
        stats = manager.get_statistics()
        print(f"   [OK] Statistics: {stats['total_backup_records']} total records")
        
        # Test 6: Update record
        print("6. Testing record update...")
        manager.update_backup_record(
            backup_id=backup_id,
            file_size=1024*1024,  # 1MB
            compressed_size=512*1024,  # 512KB
            compression_ratio=0.5
        )
        updated_record = manager.get_backup_record(backup_id)
        if updated_record.file_size == 1024*1024:
            print("   [OK] Record updated successfully")
        else:
            raise Exception("Record update failed")
        
        # Test 7: Test conflict detection (simulate)
        print("7. Testing conflict detection...")
        conflicts = manager.find_conflicts()
        print(f"   [OK] Conflict detection working, found {len(conflicts)} conflicts")
        
        # Cleanup
        print("8. Cleaning up...")
        manager.delete_backup_record(backup_id)
        
        # 关闭数据库连接（如果是独立模式）
        if hasattr(manager, '_standalone_session') and manager._standalone_session:
            manager._standalone_session.close()
        if hasattr(manager, '_standalone_engine') and manager._standalone_engine:
            manager._standalone_engine.dispose()
        
        # 等待一小段时间确保文件句柄被释放
        import time
        time.sleep(0.1)
        
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"   [WARNING] Could not remove test database file: {e}")
        print("   [OK] Cleanup completed")
        
        print("\n=== INTEGRATION TEST RESULTS ===")
        print("[SUCCESS] All tests passed successfully!")
        print("[SUCCESS] External metadata system is working correctly")
        print("[SUCCESS] Ready for integration with Flask application")
        
        return True
        
    except Exception as e:
        print(f"\n=== INTEGRATION TEST FAILED ===")
        print(f"[ERROR] Error: {e}")
        print("[ERROR] External metadata system integration failed")
        
        # Cleanup on error
        try:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        
        return False

if __name__ == "__main__":
    success = test_external_metadata_integration()
    exit(0 if success else 1)