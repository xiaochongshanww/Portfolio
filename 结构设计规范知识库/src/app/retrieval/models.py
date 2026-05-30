from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievalCandidate:
    doc_id: str
    text: str
    meta: dict[str, Any]
    score: float = 0.0
    dense_score: float | None = None
    bm25_score: float | None = None
    clause_match: bool = False
    sources: set[str] = field(default_factory=set)
    reasons: list[str] = field(default_factory=list)

    def add_reason(self, reason: str) -> None:
        if reason and reason not in self.reasons:
            self.reasons.append(reason)

    def add_source(self, source: str) -> None:
        if source:
            self.sources.add(source)

    def to_result(self) -> "RetrievalResult":
        reason = " + ".join(self.reasons) if self.reasons else "combined"
        source = "+".join(sorted(self.sources)) if self.sources else "unknown"
        return RetrievalResult(
            doc_id=self.doc_id,
            text=self.text,
            meta=self.meta,
            score=self.score,
            source=source,
            reason=reason,
            dense_score=self.dense_score,
            bm25_score=self.bm25_score,
            clause_match=self.clause_match,
        )


@dataclass(frozen=True)
class RetrievalResult:
    doc_id: str
    text: str
    meta: dict[str, Any]
    score: float
    source: str
    reason: str
    dense_score: float | None = None
    bm25_score: float | None = None
    clause_match: bool = False

    @property
    def distance(self) -> float:
        return self.meta.get("_distance", 1.0)

