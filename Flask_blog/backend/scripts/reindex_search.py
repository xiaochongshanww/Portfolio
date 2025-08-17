"""管理脚本：重建 MeiliSearch 文章索引并可选更新 ranking rules。
用法:
  python -m scripts.reindex_search [--all] [--skip-ranking]
参数:
  --all            包含所有未删除文章（含未发布），默认只索引已发布
  --skip-ranking   跳过 ranking rules 更新（等同设置环境变量 MEILI_SKIP_RANKING_RULES=1）
"""
from __future__ import annotations
import os, sys
from pathlib import Path
import argparse

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app  # noqa
from app.search.indexer import reindex_all  # noqa
from app.search.client import ensure_index, DEFAULT_RANKING_RULES  # noqa


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all', action='store_true', help='包含未发布文章')
    parser.add_argument('--skip-ranking', action='store_true', help='跳过 ranking rules 更新')
    args = parser.parse_args()

    app = create_app(os.getenv('FLASK_CONFIG','development'))
    with app.app_context():
        idx = ensure_index()
        if not args.skip_ranking and not os.getenv('MEILI_SKIP_RANKING_RULES'):
            try:
                current = []
                try:
                    settings = idx.get_settings()
                    current = settings.get('rankingRules') or []
                except Exception:
                    pass
                if set(current) != set(DEFAULT_RANKING_RULES):
                    print('[ranking] updating ranking rules...')
                    idx.update_ranking_rules(DEFAULT_RANKING_RULES)
            except Exception as e:
                print('[ranking] update failed:', e)
        print('[reindex] start')
        reindex_all(published_only=not args.all)
        print('[reindex] done')

if __name__ == '__main__':
    main()
