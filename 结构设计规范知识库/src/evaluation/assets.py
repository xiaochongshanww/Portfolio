from __future__ import annotations

from pathlib import Path

from src.evaluation.answer_runner import ANSWER_EVAL_PATH
from src.evaluation.runner import DEFAULT_EVAL_PATH, STRUCTURED_EVAL_PATH


BUILTIN_EVALUATION_ASSETS: dict[str, Path] = {
    "regular": DEFAULT_EVAL_PATH,
    "structured": STRUCTURED_EVAL_PATH,
    "answer": ANSWER_EVAL_PATH,
}
RETRIEVAL_EVALUATION_SET_IDS = frozenset({"regular", "structured"})
ANSWER_EVALUATION_SET_IDS = frozenset({"answer"})


def resolve_evaluation_asset(
    evaluation_set_id: str,
    *,
    allowed_ids: frozenset[str],
) -> Path:
    if evaluation_set_id not in allowed_ids:
        allowed = ", ".join(sorted(allowed_ids))
        raise ValueError(f"未知内置评估集 {evaluation_set_id!r}，允许值：{allowed}")
    return BUILTIN_EVALUATION_ASSETS[evaluation_set_id]
