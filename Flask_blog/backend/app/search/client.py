import os
from meilisearch import Client

MEILI_URL = os.getenv('MEILI_URL','http://127.0.0.1:7700')
MEILI_KEY = os.getenv('MEILI_KEY')

client = Client(MEILI_URL, MEILI_KEY)
INDEX_NAME = 'articles'

SEARCHABLE_FIELDS = ['title','content','tags']
# 新增 views_count 到可过滤字段，便于后续统计或筛选（尽管目前主要用于排序）
FILTERABLE_FIELDS = ['status','tags','category_id','author_id','published_at','created_at','likes_count','views_count']
# Facet 使用同一批可过滤字段中的子集（高基数字段可酌情排除）
FACET_FIELDS = ['tags','category_id','author_id']
# 新增 views_count 到可排序字段
SORTABLE_FIELDS = ['published_at','created_at','likes_count','views_count']
# 排序/相关性增强：自定义 ranking rules，将互动与新鲜度注入默认相关性之后
# 说明：MeiliSearch 评估顺序从前到后，一旦决出胜负即停止。
# 放在 exactness 之后可以确保基础文本匹配完成后再比较业务权重；如果希望业务权重影响更大，可上移。
DEFAULT_RANKING_RULES = [
    'words',        # 词匹配
    'typo',         # 拼写容错
    'proximity',    # 词间距离
    'attribute',    # 属性权重
    'sort',         # 显式 sort 参数
    'exactness',    # 精确度
    'desc(likes_count)',
    'desc(views_count)',
    'desc(published_at)'
]
# 示例 synonyms，可后续通过管理接口动态更新
DEFAULT_SYNONYMS = {
    'ai': ['artificial intelligence','人工智能'],
    'tutorial': ['guide','howto','教程']
}

def ensure_index():
    try:
        idx = client.get_index(INDEX_NAME)
    except Exception:
        client.create_index(INDEX_NAME, {'primaryKey':'id'})
        idx = client.get_index(INDEX_NAME)
    try:
        idx.update_searchable_attributes(SEARCHABLE_FIELDS)
        idx.update_filterable_attributes(FILTERABLE_FIELDS)
        try:
            # MeiliSearch v1 统一通过 filterable_attributes & sortable；若存在专门 facets 配置则调用
            idx.update_faceting({'maxValuesPerFacet': 100})
        except Exception:
            pass
        idx.update_sortable_attributes(SORTABLE_FIELDS)
        # 自定义 ranking rules（受环境变量控制，可跳过）
        if not os.getenv('MEILI_SKIP_RANKING_RULES'):
            try:
                current_rules = []
                try:
                    # MeiliSearch v1 API: get settings
                    settings = idx.get_settings()
                    current_rules = settings.get('rankingRules') or []
                except Exception:
                    pass
                # 仅当差异存在时更新，减少不必要任务
                if set(current_rules) != set(DEFAULT_RANKING_RULES):
                    idx.update_ranking_rules(DEFAULT_RANKING_RULES)
            except Exception:
                pass
        # 同义词
        try:
            idx.update_synonyms(DEFAULT_SYNONYMS)
        except Exception:
            pass
        # Typo 容错（示例：允许 2 个错字，最小词长配置）
        try:
            idx.update_typo_tolerance({
                'minWordSizeForTypos': {'oneTypo': 5, 'twoTypos': 9},
                'disableOnWords': [],
                'disableOnAttributes': []
            })
        except Exception:
            pass
    except Exception:
        pass
    return idx
