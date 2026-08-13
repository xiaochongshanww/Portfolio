# 手动集成测试脚本

本目录存放**独立运行的集成验证脚本**，不属于 pytest 单元测试套件（`backend/tests/`）。

## 与单元测试的区别

- 这些脚本通过 `if __name__ == "__main__"` 独立执行，使用 `print` 输出结果并返回退出码；
- 会创建真实文件（如 `test_external_metadata.db`）或依赖外部元数据系统；
- 不依赖 `backend/tests/conftest.py` 的内存 SQLite / FakeRedis 隔离环境；
- 若被 pytest 收集会破坏测试隔离（历史上曾因此导致 pytest 崩溃）。

因此它们被**排除在 `testpaths`（backend/tests）之外**，由 CI 或人工手动执行。

## 运行方式

```bash
# 在 backend 目录下，使用 venv 解释器直接执行：
.venv/Scripts/python.exe tests_manual/manual_external_metadata.py
.venv/Scripts/python.exe tests_manual/manual_backup_integration.py
.venv/Scripts/python.exe tests_manual/manual_smart_routing.py
.venv/Scripts/python.exe tests_manual/manual_integration.py
```

退出码 `0` 表示通过，`1` 表示失败。

> 注：脚本以 `manual_` 前缀命名（而非 `test_`），使其不匹配 pytest 默认收集模式 `test_*.py`，避免被 `pytest` 无参运行时误收集（历史上曾因此导致 pytest 崩溃）。

## 迁移建议（后续）

若这些脚本的验证逻辑需要纳入自动化回归，应将其改写为 pytest 用例：
1. 使用 `backend/tests/conftest.py` 的 `app` / `client` fixtures；
2. 用 `assert` 替代 `print` + `return bool`；
3. 迁移到 `backend/tests/` 下，纳入 `testpaths`。
