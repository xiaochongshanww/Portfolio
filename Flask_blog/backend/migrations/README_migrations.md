# Migrations Guide

## 初始化
```
flask db init  # 已执行后会生成 migrations 目录
```

## 生成迁移脚本
```
flask db migrate -m "init"
```

## 应用迁移
```
flask db upgrade
```

## 常见变更流程
1. 修改/新增模型字段 (app/models.py)
2. 生成迁移: `flask db migrate -m "add field xxx"`
3. 审查生成的版本文件 (migrations/versions/*.py)
4. 升级: `flask db upgrade`
5. 如需回滚: `flask db downgrade -1`

## 对比检测
Alembic 已启用 compare_type / compare_server_default，字段类型或默认值变更会被检测。

## 知识点
执行`flask db migrate`和`flask db upgrade`时，`Alembic`会调用`env.py`，完成实际的迁移操作。

## 注意
- 避免在生产直接使用 `db.create_all()`，使用迁移保持一致性。
- 索引或约束手动调整需确认生成脚本正确。
