from ..retrieval.models import RetrievalResult


def format_result_context(result: RetrievalResult) -> str:
    meta = result.meta
    header = [
        f"来源规范：{meta.get('name', '')}",
        f"规范编号：{meta.get('code', '')}",
        f"版本：{meta.get('version', '')}",
        f"条文号：{meta.get('clause_number', '')}",
        f"页码：{meta.get('pages', '')}",
        f"命中原因：{result.reason}",
    ]
    return "\n".join(header) + "\n正文：\n" + result.text

