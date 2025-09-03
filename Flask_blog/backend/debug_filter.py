#!/usr/bin/env python3
"""
Debug script to test SQL filtering logic
"""
import re
import tarfile
from pathlib import Path

# Extract the SQL content from backup
backup_file = Path("backups/snapshots/full_20250831_172023.tar.gz")
with tarfile.open(backup_file, 'r:gz') as tar:
    sql_member = tar.extractfile("full_20250831_172023/database_20250831_172023.sql")
    sql_content = sql_member.read().decode('utf-8')

print("=== ORIGINAL SQL (article_bookmarks sections) ===")
lines = sql_content.split('\n')
bookmark_lines = []
for i, line in enumerate(lines):
    if 'article_bookmarks' in line:
        bookmark_lines.append(f"Line {i+1}: {line}")

print("\n".join(bookmark_lines))

# Apply filtering logic from simple_restore_engine.py
protected_tables = {
    'restore_records', 'backup_records', 'backup_configs', 
    'users', 'alembic_version', 'user_roles', 'roles'
}

print(f"\n=== PROTECTED TABLES ===")
print(', '.join(protected_tables))

print(f"\n=== FILTERING PROCESS ===")

# Apply the exact filtering logic from the restore engine  
sql_prefix = """-- ULTRALTHINK 系统表保护和错误容忍设置
SET sql_notes = 0;
SET foreign_key_checks = 0;
SET autocommit = 0;
START TRANSACTION;
"""

sql_suffix = """
-- 恢复MySQL设置
COMMIT;
SET autocommit = 1;
SET foreign_key_checks = 1;
SET sql_notes = 1;
"""

# Apply prefix and suffix
sql_content = sql_prefix + sql_content + sql_suffix

# Define dependent tables
dependent_tables = {
    'article_bookmarks': ['users', 'articles'],
    'article_likes': ['users', 'articles'],
    'comments': ['users', 'articles'],
}

print(f"\n=== PROCESSING DEPENDENT TABLES ===")
# Process dependent tables first
for dep_table, dependencies in dependent_tables.items():
    protected_deps = [dep for dep in dependencies if dep in protected_tables]
    if protected_deps:
        print(f"Processing dependent table {dep_table}, removing FK constraints to: {protected_deps}")
        
        for protected_dep in protected_deps:
            # Remove foreign key constraints
            constraint_pattern = rf'CONSTRAINT `{re.escape(dep_table)}_ibfk_\d+` FOREIGN KEY \([^)]+\) REFERENCES `{re.escape(protected_dep)}` \([^)]+\),?'
            before_count = len(re.findall(constraint_pattern, sql_content, re.IGNORECASE))
            sql_content = re.sub(constraint_pattern, '', sql_content, flags=re.IGNORECASE)
            print(f"  - Removed {before_count} FK constraints from {dep_table} to {protected_dep}")

print(f"\n=== PROCESSING PROTECTED TABLES ===")

for table in protected_tables:
    print(f"Filtering table: {table}")
    
    # Filter DROP TABLE statements
    drop_pattern = rf'DROP TABLE IF EXISTS `{re.escape(table)}`.*?;'
    before_count = len(re.findall(drop_pattern, sql_content, re.IGNORECASE | re.DOTALL))
    sql_content = re.sub(drop_pattern, '', sql_content, flags=re.IGNORECASE | re.DOTALL)
    print(f"  - Removed {before_count} DROP TABLE statements")
    
    # Filter CREATE TABLE blocks
    create_pattern = rf'CREATE TABLE `{re.escape(table)}`.*?;'
    before_count = len(re.findall(create_pattern, sql_content, re.IGNORECASE | re.DOTALL))
    sql_content = re.sub(create_pattern, '', sql_content, flags=re.IGNORECASE | re.DOTALL)
    print(f"  - Removed {before_count} CREATE TABLE statements")
    
    # Filter LOCK TABLES statements
    lock_pattern = rf'LOCK TABLES `{re.escape(table)}`.*?;'
    before_count = len(re.findall(lock_pattern, sql_content, re.IGNORECASE | re.DOTALL))
    sql_content = re.sub(lock_pattern, '', sql_content, flags=re.IGNORECASE | re.DOTALL)
    print(f"  - Removed {before_count} LOCK TABLE statements")
    
    # Filter INSERT INTO statements
    insert_pattern = rf'INSERT INTO `{re.escape(table)}`.*?;'
    before_count = len(re.findall(insert_pattern, sql_content, re.IGNORECASE | re.DOTALL))
    sql_content = re.sub(insert_pattern, '', sql_content, flags=re.IGNORECASE | re.DOTALL)
    print(f"  - Removed {before_count} INSERT statements")

print(f"\n=== FILTERED SQL (article_bookmarks sections) ===")
lines = sql_content.split('\n')
bookmark_lines = []
for i, line in enumerate(lines):
    if 'article_bookmarks' in line:
        bookmark_lines.append(f"Line {i+1}: {line}")

print("\n".join(bookmark_lines))

print(f"\n=== CHECK: Does filtered SQL contain CREATE TABLE for article_bookmarks? ===")
create_pattern = r'CREATE TABLE `article_bookmarks`'
matches = re.findall(create_pattern, sql_content, re.IGNORECASE)
print(f"Found {len(matches)} CREATE TABLE statements for article_bookmarks")

print(f"\n=== CHECK: Does filtered SQL contain INSERT INTO for article_bookmarks? ===")
insert_pattern = r'INSERT INTO `article_bookmarks`'
matches = re.findall(insert_pattern, sql_content, re.IGNORECASE)
print(f"Found {len(matches)} INSERT statements for article_bookmarks")