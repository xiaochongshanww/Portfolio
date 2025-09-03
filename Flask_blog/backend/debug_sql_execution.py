#!/usr/bin/env python3
"""
Debug SQL execution to find why article_bookmarks table doesn't get created
"""
import re
import tarfile
from pathlib import Path

# Extract and process the SQL content using the same logic as the restore engine
backup_file = Path("backups/snapshots/full_20250831_172023.tar.gz")
with tarfile.open(backup_file, 'r:gz') as tar:
    sql_member = tar.extractfile("full_20250831_172023/database_20250831_172023.sql")
    sql_content = sql_member.read().decode('utf-8')

# Apply the exact filtering logic from the updated restore engine
protected_tables = {
    'restore_records', 'backup_records', 'backup_configs', 
    'users', 'alembic_version', 'user_roles', 'roles'
}

dependent_tables = {
    'article_bookmarks': ['users', 'articles'],
    'article_likes': ['users', 'articles'],  
    'comments': ['users', 'articles'],
}

print("=== APPLYING FULL RESTORE ENGINE FILTERING ===")

# Apply prefix and suffix
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

sql_content = sql_prefix + sql_content + sql_suffix

# Process dependent tables first - remove ALL foreign key constraints AND drop statements
for dep_table, dependencies in dependent_tables.items():
    print(f"Processing {dep_table}, removing DROP statements and ALL FK constraints")
    
    # 1. Remove DROP TABLE statements
    drop_pattern = rf'DROP TABLE IF EXISTS `{re.escape(dep_table)}`.*?;'
    drop_count = len(re.findall(drop_pattern, sql_content, re.IGNORECASE | re.DOTALL))
    sql_content = re.sub(drop_pattern, f'-- DROP TABLE `{dep_table}` removed for safety', sql_content, flags=re.IGNORECASE | re.DOTALL)
    
    # 2. Remove all foreign key constraints for this table
    constraint_pattern = rf'CONSTRAINT `{re.escape(dep_table)}_ibfk_\d+` FOREIGN KEY \([^)]+\) REFERENCES `[^`]+` \([^)]+\),?\s*'
    removed_count = len(re.findall(constraint_pattern, sql_content, re.IGNORECASE))
    sql_content = re.sub(constraint_pattern, '', sql_content, flags=re.IGNORECASE)
    
    # 3. Clean up extra commas
    cleanup_pattern = rf'(,\s*)\s+\) ENGINE='
    sql_content = re.sub(cleanup_pattern, r'\n) ENGINE=', sql_content, flags=re.IGNORECASE)
    
    print(f"  - Removed {drop_count} DROP statements and {removed_count} FK constraints from {dep_table}")

# Process protected tables
for table in protected_tables:
    # Filter DROP TABLE statements
    drop_pattern = rf'DROP TABLE IF EXISTS `{re.escape(table)}`.*?;'
    sql_content = re.sub(drop_pattern, '', sql_content, flags=re.IGNORECASE | re.DOTALL)
    
    # Filter CREATE TABLE blocks
    create_pattern = rf'CREATE TABLE `{re.escape(table)}`.*?;'
    sql_content = re.sub(create_pattern, '', sql_content, flags=re.IGNORECASE | re.DOTALL)
    
    # Filter LOCK TABLES statements
    lock_pattern = rf'LOCK TABLES `{re.escape(table)}`.*?;'
    sql_content = re.sub(lock_pattern, '', sql_content, flags=re.IGNORECASE | re.DOTALL)
    
    # Filter INSERT INTO statements
    insert_pattern = rf'INSERT INTO `{re.escape(table)}`.*?;'
    sql_content = re.sub(insert_pattern, '', sql_content, flags=re.IGNORECASE | re.DOTALL)

# Clean up empty lines
lines = sql_content.split('\n')
filtered_lines = []
prev_empty = False

for line in lines:
    line_stripped = line.strip()
    is_empty = line_stripped == '' or line_stripped.startswith('--')
    
    if is_empty and prev_empty and not line_stripped.startswith('--'):
        continue
        
    filtered_lines.append(line)
    prev_empty = is_empty

filtered_content = '\n'.join(filtered_lines)

# Now analyze the filtered content
print(f"\n=== ANALYZING FILTERED SQL (line by line for article_bookmarks) ===")
lines = filtered_content.split('\n')

# Find line 37 (the error line from latest restore)
error_context = []  
for i in range(max(0, 32), min(len(lines), 42)):  # Lines 33-41 (around line 37)
    line_num = i + 1
    line = lines[i]
    marker = " >>> ERROR LINE <<<" if line_num == 37 else ""
    error_context.append(f"Line {line_num:3d}: {line}{marker}")

print("=== CONTEXT AROUND ERROR LINE 38 ===")
print("\n".join(error_context))

print(f"\n=== SEARCHING FOR ALL article_bookmarks REFERENCES ===")
bookmark_references = []
for i, line in enumerate(lines):
    if 'article_bookmarks' in line.lower():
        bookmark_references.append(f"Line {i+1:3d}: {line}")

print("\n".join(bookmark_references))

print(f"\n=== CHECKING TABLE CREATION ORDER ===")
create_statements = []
for i, line in enumerate(lines):
    if re.match(r'CREATE TABLE `\w+`', line):
        table_match = re.search(r'CREATE TABLE `(\w+)`', line)
        if table_match:
            table_name = table_match.group(1)
            create_statements.append(f"Line {i+1:3d}: CREATE TABLE `{table_name}`")

print("\n".join(create_statements))

# Write filtered SQL to file for manual inspection
with open('filtered_sql_debug.sql', 'w', encoding='utf-8') as f:
    f.write(filtered_content)
    
print(f"\n=== FILTERED SQL SAVED TO filtered_sql_debug.sql ===")
print(f"Total lines: {len(lines)}")