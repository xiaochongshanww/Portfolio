"""
智能表验证器

基于 SQLAlchemy 模型反射和多源验证的动态表发现系统
避免硬编码表名，自动适应项目结构变化
"""

import re
import logging
from pathlib import Path
from typing import Dict, Set, List, Tuple, Any, Optional
from dataclasses import dataclass
from enum import Enum

from flask import current_app
from sqlalchemy import text
from .. import db


class TableImportance(Enum):
    """表重要性级别"""
    CRITICAL = "critical"      # 核心业务表，丢失会导致系统无法运行
    IMPORTANT = "important"    # 重要功能表，影响主要功能
    SYSTEM = "system"          # 系统管理表，影响后台功能  
    RELATIONSHIP = "relationship"  # 关联表，维护数据关系
    OPTIONAL = "optional"      # 可选功能表，丢失不影响核心功能


@dataclass
class TableInfo:
    """表信息数据结构"""
    name: str
    importance: TableImportance
    columns: List[str]
    has_foreign_keys: bool
    is_junction_table: bool
    dependencies: List[str]  # 依赖的其他表


class SQLAlchemyTableDiscovery:
    """SQLAlchemy 模型反射表发现器"""
    
    @staticmethod
    def get_all_model_tables() -> Set[str]:
        """从 SQLAlchemy 模型中获取所有表名"""
        try:
            # 获取所有定义的模型表
            model_tables = set()
            for table_name in db.metadata.tables.keys():
                model_tables.add(table_name)
            
            current_app.logger.info(f"从 SQLAlchemy 模型发现 {len(model_tables)} 张表")
            return model_tables
            
        except Exception as e:
            current_app.logger.error(f"SQLAlchemy 表发现失败: {e}")
            return set()
    
    @staticmethod
    def get_detailed_table_info() -> Dict[str, TableInfo]:
        """获取详细的表信息"""
        table_info = {}
        
        try:
            for table_name, table_obj in db.metadata.tables.items():
                # 分析表结构
                columns = [col.name for col in table_obj.columns]
                foreign_keys = list(table_obj.foreign_keys)
                
                # 判断是否是关联表（junction table）
                is_junction = SQLAlchemyTableDiscovery._is_junction_table(table_obj)
                
                # 分析表的重要性
                importance = SQLAlchemyTableDiscovery._assess_table_importance(
                    table_name, table_obj, is_junction
                )
                
                # 分析依赖关系
                dependencies = SQLAlchemyTableDiscovery._get_table_dependencies(table_obj)
                
                table_info[table_name] = TableInfo(
                    name=table_name,
                    importance=importance,
                    columns=columns,
                    has_foreign_keys=len(foreign_keys) > 0,
                    is_junction_table=is_junction,
                    dependencies=dependencies
                )
                
            current_app.logger.info(f"分析了 {len(table_info)} 张表的详细信息")
            return table_info
            
        except Exception as e:
            current_app.logger.error(f"详细表信息获取失败: {e}")
            return {}
    
    @staticmethod
    def _is_junction_table(table_obj) -> bool:
        """判断是否是关联表"""
        # 关联表通常有以下特征：
        # 1. 只有外键列（除了可能的时间戳）
        # 2. 表名包含下划线连接两个实体
        # 3. 列数较少
        
        columns = list(table_obj.columns)
        foreign_key_columns = [col for col in columns if col.foreign_keys]
        
        # 如果大部分列都是外键，可能是关联表
        if len(foreign_key_columns) >= 2 and len(foreign_key_columns) >= len(columns) * 0.5:
            return True
            
        # 检查表名模式
        if '_' in table_obj.name and len(table_obj.name.split('_')) == 2:
            # 如果表名形如 "article_tags", "user_roles" 等
            return True
            
        return False
    
    @staticmethod
    def _assess_table_importance(table_name: str, table_obj, is_junction: bool) -> TableImportance:
        """评估表的重要性"""
        name_lower = table_name.lower()
        
        # 关联表通常不是关键表，但也很重要
        if is_junction:
            return TableImportance.RELATIONSHIP
        
        # 核心业务表模式匹配
        critical_patterns = [
            r'^users?$',           # 用户表
            r'^articles?$',        # 文章表  
            r'^categor(y|ies)$',   # 分类表
            r'^posts?$',           # 文章表的另一种命名
        ]
        
        for pattern in critical_patterns:
            if re.match(pattern, name_lower):
                return TableImportance.CRITICAL
        
        # 重要功能表模式匹配
        important_patterns = [
            r'^comments?$',        # 评论表
            r'^tags?$',           # 标签表
            r'^media',            # 媒体相关表
            r'_version',          # 版本表
        ]
        
        for pattern in important_patterns:
            if re.search(pattern, name_lower):
                return TableImportance.IMPORTANT
        
        # 系统管理表模式匹配
        system_patterns = [
            r'^(backup|restore|audit|log)',  # 备份、审计、日志表
            r'^(admin|manage)',              # 管理相关表
            r'_config',                      # 配置表
        ]
        
        for pattern in system_patterns:
            if re.search(pattern, name_lower):
                return TableImportance.SYSTEM
        
        # 可选功能表模式匹配  
        optional_patterns = [
            r'^(visitor_stats|daily_stats)', # 统计表
            r'^(notification|message)',      # 通知消息表
            r'_cache',                       # 缓存表
        ]
        
        for pattern in optional_patterns:
            if re.search(pattern, name_lower):
                return TableImportance.OPTIONAL
        
        # 默认归类为重要表（保守策略）
        return TableImportance.IMPORTANT
    
    @staticmethod  
    def _get_table_dependencies(table_obj) -> List[str]:
        """获取表的依赖关系"""
        dependencies = []
        
        for fk in table_obj.foreign_keys:
            referenced_table = fk.column.table.name
            if referenced_table != table_obj.name:  # 避免自引用
                dependencies.append(referenced_table)
        
        return list(set(dependencies))  # 去重


class MigrationHistoryAnalyzer:
    """迁移历史分析器"""
    
    @staticmethod
    def get_tables_from_migrations() -> Set[str]:
        """从迁移历史中解析应该存在的表"""
        migrations_dir = Path("migrations/versions")
        
        if not migrations_dir.exists():
            current_app.logger.warning(f"迁移目录不存在: {migrations_dir}")
            return set()
        
        expected_tables = set()
        
        try:
            # 按文件名排序（基本按时间顺序）
            migration_files = sorted(migrations_dir.glob("*.py"))
            current_app.logger.info(f"找到 {len(migration_files)} 个迁移文件")
            
            for migration_file in migration_files:
                tables_in_migration = MigrationHistoryAnalyzer._parse_migration_file(migration_file)
                expected_tables.update(tables_in_migration['created'])
                expected_tables.difference_update(tables_in_migration['dropped'])
                
            current_app.logger.info(f"从迁移历史发现 {len(expected_tables)} 张表")
            return expected_tables
            
        except Exception as e:
            current_app.logger.error(f"迁移历史分析失败: {e}")
            return set()
    
    @staticmethod
    def _parse_migration_file(migration_path: Path) -> Dict[str, Set[str]]:
        """解析单个迁移文件，提取表操作信息"""
        result = {'created': set(), 'dropped': set()}
        
        try:
            with open(migration_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 分离 upgrade() 和 downgrade() 函数
            upgrade_section = ""
            downgrade_section = ""
            
            # 查找 upgrade() 函数内容
            upgrade_match = re.search(r'def upgrade\(\):.*?(?=def downgrade\(\):|\Z)', content, re.DOTALL)
            if upgrade_match:
                upgrade_section = upgrade_match.group(0)
            
            # 查找 downgrade() 函数内容
            downgrade_match = re.search(r'def downgrade\(\):.*', content, re.DOTALL)
            if downgrade_match:
                downgrade_section = downgrade_match.group(0)
            
            # 在 upgrade() 部分查找表创建操作
            create_patterns = [
                r"op\.create_table\(['\"](\w+)['\"]",                    # op.create_table('table_name'
                r"op\.create_table\(\s*['\"](\w+)['\"]",                # op.create_table( 'table_name'  
                r"op\.create_table\(\s*['\"](\w+)['\"]",                # with whitespace
                r"op\.create_table\(\s*[\r\n\s]*['\"](\w+)['\"]",       # multiline format
                r"CREATE TABLE ['\"]?(\w+)['\"]?",                      # CREATE TABLE table_name
                r"CREATE TABLE IF NOT EXISTS ['\"]?(\w+)['\"]?",        # CREATE TABLE IF NOT EXISTS
            ]
            
            for pattern in create_patterns:
                matches = re.findall(pattern, upgrade_section, re.IGNORECASE)
                result['created'].update(matches)
            
            # 在 upgrade() 部分查找表删除操作（升级时删除的表才是真正被删除的）
            drop_patterns = [
                r"op\.drop_table\(['\"](\w+)['\"]",       # op.drop_table('table_name'
                r"DROP TABLE ['\"]?(\w+)['\"]?",          # DROP TABLE table_name
            ]
            
            for pattern in drop_patterns:
                matches = re.findall(pattern, upgrade_section, re.IGNORECASE)
                result['dropped'].update(matches)
                
        except Exception as e:
            current_app.logger.warning(f"解析迁移文件失败 {migration_path}: {e}")
        
        return result


class SmartTableValidator:
    """智能表验证器 - 主类"""
    
    def __init__(self):
        self.logger = current_app.logger
        self.sqlalchemy_discovery = SQLAlchemyTableDiscovery()
        self.migration_analyzer = MigrationHistoryAnalyzer()
    
    def get_expected_tables_smart(self) -> Tuple[Set[str], Dict[str, TableInfo]]:
        """智能获取预期的表列表和详细信息"""
        all_tables = set()
        table_details = {}
        
        # 优先级1: SQLAlchemy模型 (最准确)
        try:
            model_tables = self.sqlalchemy_discovery.get_all_model_tables()
            table_details = self.sqlalchemy_discovery.get_detailed_table_info()
            all_tables.update(model_tables)
            self.logger.info(f"✅ 从 SQLAlchemy 模型获取了 {len(model_tables)} 张表")
        except Exception as e:
            self.logger.error(f"❌ SQLAlchemy 模型表获取失败: {e}")
        
        # 优先级2: 迁移历史 (补充验证)
        try:
            migration_tables = self.migration_analyzer.get_tables_from_migrations()
            new_from_migrations = migration_tables - all_tables
            if new_from_migrations:
                all_tables.update(new_from_migrations)
                self.logger.info(f"✅ 从迁移历史补充了 {len(new_from_migrations)} 张表: {new_from_migrations}")
        except Exception as e:
            self.logger.warning(f"⚠️ 迁移历史解析失败: {e}")
        
        # 优先级3: 当前数据库 (兜底方案)
        if not all_tables:
            try:
                current_tables = self._get_current_database_tables()
                all_tables.update(current_tables)
                self.logger.info(f"⚠️ 使用兜底方案，从当前数据库获取了 {len(current_tables)} 张表")
            except Exception as e:
                self.logger.error(f"❌ 所有表发现方案都失败了: {e}")
        
        return all_tables, table_details
    
    def _get_current_database_tables(self) -> Set[str]:
        """从当前数据库获取表列表（兜底方案）"""
        try:
            result = db.session.execute(text("SHOW TABLES"))
            tables = {row[0] for row in result.fetchall()}
            return tables
        except Exception as e:
            self.logger.error(f"获取当前数据库表失败: {e}")
            return set()
    
    def parse_backup_tables(self, sql_content: str) -> Set[str]:
        """从备份SQL内容中解析出包含的表"""
        backup_tables = set()
        
        # 查找 CREATE TABLE 语句
        create_patterns = [
            r"CREATE TABLE ['\"]?`?(\w+)['\"]?`?",
            r"CREATE TABLE IF NOT EXISTS ['\"]?`?(\w+)['\"]?`?",
        ]
        
        for pattern in create_patterns:
            matches = re.findall(pattern, sql_content, re.IGNORECASE | re.MULTILINE)
            backup_tables.update(matches)
        
        # 也检查 INSERT INTO 语句（某些备份可能不包含CREATE，只有数据）
        insert_patterns = [
            r"INSERT INTO ['\"]?`?(\w+)['\"]?`?",
        ]
        
        for pattern in insert_patterns:
            matches = re.findall(pattern, sql_content, re.IGNORECASE | re.MULTILINE)
            backup_tables.update(matches)
        
        self.logger.info(f"从备份内容中发现 {len(backup_tables)} 张表")
        return backup_tables
    
    def validate_backup_completeness(self, sql_content: str) -> Dict[str, Any]:
        """验证备份完整性 - 智能方式"""
        self.logger.info("开始智能备份完整性验证...")
        
        # Step 1: 获取预期表和详细信息
        expected_tables, table_details = self.get_expected_tables_smart()
        
        # Step 2: 解析备份内容
        backup_tables = self.parse_backup_tables(sql_content)
        
        # Step 3: 计算差异
        missing_tables = expected_tables - backup_tables
        extra_tables = backup_tables - expected_tables
        
        # Step 4: 分析缺失表的严重性
        severity_analysis = self._analyze_missing_severity(missing_tables, table_details)
        
        # Step 5: 生成验证结果
        result = {
            'complete': len(missing_tables) == 0,
            'total_expected': len(expected_tables),
            'total_in_backup': len(backup_tables),
            'missing_count': len(missing_tables),
            'extra_count': len(extra_tables),
            'missing_tables': list(missing_tables),
            'extra_tables': list(extra_tables),
            **severity_analysis,
            'can_proceed_safely': severity_analysis['severity'] in ['none', 'low'],
            'timestamp': current_app.logger.name or 'unknown'
        }
        
        self._log_validation_result(result)
        return result
    
    def _analyze_missing_severity(self, missing_tables: Set[str], table_details: Dict[str, TableInfo]) -> Dict[str, Any]:
        """分析缺失表的严重程度"""
        
        categorized_missing = {
            'critical': [],
            'important': [], 
            'system': [],
            'relationship': [],
            'optional': []
        }
        
        # 对缺失的表进行分类
        for table_name in missing_tables:
            if table_name in table_details:
                importance = table_details[table_name].importance.value
                categorized_missing[importance].append(table_name)
            else:
                # 对于没有详细信息的表，使用启发式分类
                heuristic_importance = self._heuristic_classify_table(table_name)
                categorized_missing[heuristic_importance].append(table_name)
        
        # 确定总体严重程度
        if categorized_missing['critical']:
            severity = 'critical'
            can_proceed = False
        elif categorized_missing['important']:
            severity = 'high'
            can_proceed = False
        elif categorized_missing['system'] or categorized_missing['relationship']:
            severity = 'medium'
            can_proceed = True  # 可以继续，但需要警告
        else:
            severity = 'low'
            can_proceed = True
        
        # 如果没有缺失表
        if not missing_tables:
            severity = 'none'
            can_proceed = True
        
        return {
            'severity': severity,
            'can_proceed': can_proceed,
            'critical_missing': categorized_missing['critical'],
            'important_missing': categorized_missing['important'],
            'system_missing': categorized_missing['system'],
            'relationship_missing': categorized_missing['relationship'],
            'optional_missing': categorized_missing['optional'],
            'recommendations': self._generate_recommendations(categorized_missing, severity)
        }
    
    def _heuristic_classify_table(self, table_name: str) -> str:
        """对未知表进行启发式分类"""
        name_lower = table_name.lower()
        
        # 使用与 SQLAlchemy 发现器相同的逻辑
        if any(pattern in name_lower for pattern in ['user', 'article', 'categor']):
            return 'critical'
        elif any(pattern in name_lower for pattern in ['comment', 'tag', 'media']):
            return 'important'
        elif any(pattern in name_lower for pattern in ['backup', 'audit', 'log']):
            return 'system'
        elif '_' in name_lower and len(name_lower.split('_')) == 2:
            return 'relationship'
        else:
            return 'optional'
    
    def _generate_recommendations(self, categorized_missing: Dict[str, List[str]], severity: str) -> List[str]:
        """生成建议和操作指南"""
        recommendations = []
        
        if severity == 'critical':
            recommendations.append("❌ 发现核心表缺失，强烈建议不要执行恢复操作")
            recommendations.append("🔧 请检查备份创建过程是否正确包含所有核心表")
            if categorized_missing['critical']:
                recommendations.append(f"🎯 缺失的核心表: {', '.join(categorized_missing['critical'])}")
        
        elif severity == 'high':
            recommendations.append("⚠️ 发现重要表缺失，建议谨慎执行恢复")
            recommendations.append("💾 考虑先创建当前数据库的快照作为安全措施")
            if categorized_missing['important']:
                recommendations.append(f"📋 缺失的重要表: {', '.join(categorized_missing['important'])}")
        
        elif severity == 'medium':
            recommendations.append("ℹ️ 发现系统表或关联表缺失，可以继续恢复但需要注意")
            recommendations.append("🔍 恢复后请检查相关功能是否正常")
        
        elif severity == 'low':
            recommendations.append("✅ 只有可选表缺失，恢复应该是安全的")
        
        else:
            recommendations.append("🎉 备份包含所有预期的表，可以安全执行恢复")
        
        return recommendations
    
    def _log_validation_result(self, result: Dict[str, Any]):
        """记录验证结果到日志"""
        if result['complete']:
            self.logger.info("✅ 备份完整性验证通过")
        else:
            self.logger.warning(f"⚠️ 备份完整性验证发现问题 - 严重程度: {result['severity']}")
            self.logger.warning(f"缺失 {result['missing_count']} 张表: {result['missing_tables']}")
            
            if result['critical_missing']:
                self.logger.error(f"❌ 核心表缺失: {result['critical_missing']}")
            if result['important_missing']:
                self.logger.warning(f"⚠️ 重要表缺失: {result['important_missing']}")