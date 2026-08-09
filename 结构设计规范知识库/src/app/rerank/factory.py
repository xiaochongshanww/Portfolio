from ..core.config import Settings, settings
from .base import BaseReranker
from .noop import NoopReranker
from .safe import FailOpenReranker
from .zhipu import ZhipuReranker


def get_reranker(config: Settings = settings) -> BaseReranker:
    if not config.rerank_enabled:
        return NoopReranker()
    if config.rerank_provider == "zhipu":
        return FailOpenReranker(
            ZhipuReranker(
                api_key=config.zhipuai_api_key,
                base_url=config.rerank_base_url,
                model=config.rerank_model,
                timeout_seconds=config.rerank_timeout_seconds,
                model_weight=config.rerank_model_weight,
            )
        )
    raise ValueError(f"不支持的 reranker 提供方：{config.rerank_provider}")
