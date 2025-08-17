"""导出当前运行代码动态生成的 OpenAPI 规范为静态 JSON 文件。
用法:
    python -m scripts.export_openapi [output_path]
默认输出: ./openapi.json (项目 backend 目录下)
"""
from __future__ import annotations
import os, json, sys
from pathlib import Path

# 确保可导入 app
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app  # noqa: E402


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DIR / 'openapi.json'
    app = create_app(os.getenv('FLASK_CONFIG','development'))
    with app.app_context():
        # 直接导入动态 spec 构建模块
        from app.docs.openapi import OPENAPI_SPEC  # noqa
        # 更新版本号同步
        OPENAPI_SPEC['info']['version'] = app.config.get('VERSION') or OPENAPI_SPEC['info'].get('version')
        # 补充生成时间元信息 (非标准扩展字段)
        import datetime
        OPENAPI_SPEC['x-generated-at'] = datetime.datetime.utcnow().isoformat() + 'Z'
        data = json.dumps(OPENAPI_SPEC, ensure_ascii=False, indent=2)
        out_path.write_text(data, encoding='utf-8')
        print(f"Exported OpenAPI spec -> {out_path}")

if __name__ == '__main__':
    main()
