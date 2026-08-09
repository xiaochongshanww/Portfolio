import logging
import re
from pathlib import Path
from threading import RLock
from typing import Any

try:
    import chromadb
except ImportError:
    chromadb = None

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

try:
    from zai import ZhipuAiClient
except ImportError:
    ZhipuAiClient = None

from src.pipeline.active_db import active_db_dir
from src.pipeline.chunks import extract_table_info

from ..core.config import Settings, settings
from ..rerank.factory import get_reranker
from .models import RetrievalCandidate, RetrievalResult
from .query import QueryInfo, analyze_query

GENERIC_CONTENT_KEYWORDS = {
    "建筑",
    "工程",
    "结构",
    "规范",
    "标准",
    "抗震",
    "设防",
    "类别",
    "分类",
    "规定",
    "要求",
    "荷载",
    "设计",
    "施工",
    "质量",
    "验收",
}

EXPLICIT_TABLE_QUESTION_TERMS = (
    "哪个表",
    "哪张表",
    "哪个表格",
    "在哪个表",
    "查哪个表",
    "采用哪个表",
)


def tokenize_chinese(text: str) -> list[str]:
    normalized = re.sub(r"[^一-鿿\w]", " ", text.lower())
    words = normalized.split()
    chars = list("".join(words))
    trigrams = ["".join(chars[i : i + 3]) for i in range(len(chars) - 2)]
    return words + trigrams


def text_contains_clause_heading(text: str, clause_num: str) -> bool:
    pattern = rf"(^|\n)\s*(?:第\s*)?{re.escape(clause_num)}\s*(?:条)?(?=\D|$)"
    return re.search(pattern, text) is not None


def text_mentions_clause(text: str, clause_num: str) -> bool:
    pattern = rf"(?<!\d)(?:第\s*)?{re.escape(clause_num)}\s*(?:条)?(?!\d)"
    return re.search(pattern, text) is not None


def matches_requested_spec(query_info: QueryInfo, meta: dict[str, Any]) -> bool:
    if not query_info.spec_codes and not query_info.spec_names:
        return True
    spec_text = " ".join(str(meta.get(key, "")) for key in ("code", "name", "source_file"))
    if query_info.spec_codes and any(code in spec_text for code in query_info.spec_codes):
        return True
    if query_info.spec_names and any(name in spec_text for name in query_info.spec_names):
        return True
    return False


def infer_section_type(meta: dict[str, Any], text: str = "") -> str:
    section_type = str(meta.get("section_type") or "")
    if section_type:
        return section_type
    chunk_type = str(meta.get("chunk_type") or "")
    title = str(meta.get("title") or "")
    clause_number = str(meta.get("clause_number") or "")
    combined = f"{title}\n{text}"
    if clause_number.startswith("0.") or chunk_type == "explanation" or "条文说明" in combined:
        return "explanation"
    if chunk_type == "table" or title.strip().startswith("表"):
        return "body_table"
    if chunk_type in {"figure", "formula"}:
        return chunk_type
    return "body"


def infer_is_table(meta: dict[str, Any], text: str = "") -> bool:
    if bool(meta.get("is_table")):
        return True
    title = str(meta.get("title") or "")
    return (
        str(meta.get("chunk_type") or "") == "table"
        or bool(meta.get("table_id"))
        or bool(extract_table_info(title, "")[0])
    )


def compact_evidence(text: str) -> str:
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]+", "", text)


def evidence_contains(evidence: str, piece: str) -> bool:
    if not piece:
        return False
    return piece in evidence or compact_evidence(piece) in compact_evidence(evidence)


def specific_content_keywords(query_info: QueryInfo) -> list[str]:
    spec_terms = "".join(query_info.spec_names + query_info.spec_aliases)
    compact_spec_terms = compact_evidence(spec_terms)
    return [
        keyword
        for keyword in query_info.content_keywords
        if keyword not in GENERIC_CONTENT_KEYWORDS
        and len(keyword) >= 2
        and compact_evidence(keyword) not in compact_spec_terms
    ]


def asks_for_table_identifier(query_info: QueryInfo) -> bool:
    return any(term in query_info.normalized for term in EXPLICIT_TABLE_QUESTION_TERMS)


class RetrievalState:
    def __init__(self, config: Settings = settings) -> None:
        self.config = config
        self._state_lock = RLock()
        self.zhipu_client: Any = None
        self.chroma_client: Any = None
        self.chroma_collection: Any = None
        self.bm25_index: Any = None
        self.bm25_texts: list[str] = []
        self.db_dir: Path | None = None

    def initialize(self) -> None:
        self._initialize_embedding_client()
        self._initialize_chroma_and_bm25()

    def _initialize_embedding_client(self) -> None:
        if not self.config.zhipuai_api_key:
            return
        if ZhipuAiClient is None:
            logging.error("ZhipuAI SDK 未安装，无法初始化向量检索客户端")
            return
        try:
            self.zhipu_client = ZhipuAiClient(api_key=self.config.zhipuai_api_key)
            logging.info("ZhipuAI 初始化成功")
        except Exception as exc:
            logging.error("ZhipuAI 初始化失败: %s", exc)

    def _initialize_chroma_and_bm25(self) -> None:
        try:
            if chromadb is None:
                logging.error("ChromaDB 未安装，无法初始化知识库")
                return
            db_dir = active_db_dir()
            db_dir.mkdir(parents=True, exist_ok=True)
            self._load_chroma_from(db_dir)
        except Exception as exc:
            logging.error("ChromaDB/BM25 初始化失败: %s", exc)

    def _load_chroma_from(self, db_dir: Path) -> None:
        if chromadb is None:
            logging.error("ChromaDB 未安装，无法初始化知识库")
            return
        chroma_client = chromadb.PersistentClient(path=str(db_dir))
        chroma_collection = chroma_client.get_or_create_collection(name=self.config.collection_name)
        count = chroma_collection.count()
        logging.info("ChromaDB: %s 条 (%s)", count, db_dir)

        bm25_index = None
        bm25_texts: list[str] = []
        if count > 0:
            if BM25Okapi is None:
                logging.error("rank-bm25 未安装，跳过 BM25 索引构建")
            else:
                all_data = chroma_collection.get()
                bm25_texts = [doc or "" for doc in all_data["documents"]]
                tokenized = [tokenize_chinese(text) for text in bm25_texts]
                bm25_index = BM25Okapi(tokenized)
                logging.info("BM25 索引构建完成: %s 条", len(bm25_texts))

        with self._state_lock:
            self.chroma_client = chroma_client
            self.chroma_collection = chroma_collection
            self.bm25_index = bm25_index
            self.bm25_texts = bm25_texts
            self.db_dir = db_dir

    def reload(self, db_dir: Path | None = None) -> None:
        target = db_dir or active_db_dir()
        target.mkdir(parents=True, exist_ok=True)
        try:
            self._load_chroma_from(target)
        except Exception as exc:
            logging.error("ChromaDB/BM25 重载失败: %s", exc)
            raise

    @classmethod
    def load_candidate(cls, db_dir: Path, config: Settings = settings) -> "RetrievalState":
        candidate = cls(config)
        candidate._initialize_embedding_client()
        candidate.reload(db_dir)
        return candidate

    def adopt(self, candidate: "RetrievalState") -> None:
        if candidate.config.collection_name != self.config.collection_name:
            raise ValueError("候选检索状态的 collection_name 与运行配置不一致")
        if not candidate.chroma_collection:
            raise ValueError("候选检索状态没有可用的 Chroma collection")
        with self._state_lock:
            self.zhipu_client = candidate.zhipu_client
            self.chroma_client = candidate.chroma_client
            self.chroma_collection = candidate.chroma_collection
            self.bm25_index = candidate.bm25_index
            self.bm25_texts = candidate.bm25_texts
            self.db_dir = candidate.db_dir

    @property
    def ready(self) -> bool:
        with self._state_lock:
            return bool(self.chroma_collection and self.zhipu_client)

    def chroma_count(self) -> int:
        with self._state_lock:
            if not self.chroma_collection:
                return -1
            try:
                return self.chroma_collection.count()
            except Exception:
                return -1

    def hybrid_search(self, query: str, top_k: int) -> list[RetrievalResult]:
        with self._state_lock:
            return self._hybrid_search_unlocked(query, top_k)

    def _hybrid_search_unlocked(self, query: str, top_k: int) -> list[RetrievalResult]:
        if not self.chroma_collection:
            return []

        query_info = analyze_query(query)
        all_data = self.chroma_collection.get()
        id_to_doc = dict(zip(all_data["ids"], all_data["documents"], strict=True))
        id_to_meta = dict(zip(all_data["ids"], all_data["metadatas"], strict=True))
        results_pool: dict[str, RetrievalCandidate] = {}

        if self.zhipu_client:
            try:
                response = self.zhipu_client.embeddings.create(
                    model=self.config.embedding_model,
                    input=[query],
                )
                embedding = response.data[0].embedding
                results = self.chroma_collection.query(
                    query_embeddings=[embedding], n_results=top_k * 5
                )
                for doc_id, distance in zip(
                    results["ids"][0], results["distances"][0], strict=True
                ):
                    if doc_id in id_to_doc:
                        candidate = self._candidate_for(doc_id, id_to_doc, id_to_meta, results_pool)
                        candidate.dense_score = 1 / (1 + float(distance))
                        candidate.meta["_distance"] = float(distance)
                        candidate.score += (
                            candidate.dense_score * self.config.retrieval_dense_weight
                        )
                        candidate.add_source("dense")
                        candidate.add_reason("dense semantic match")
            except Exception as exc:
                logging.error("向量检索失败: %s", exc)

        self._add_clause_matches(query_info, all_data, id_to_doc, id_to_meta, results_pool)
        self._add_bm25_matches(query_info, top_k, all_data, id_to_doc, id_to_meta, results_pool)
        self._add_table_intent_matches(
            query_info, top_k, all_data, id_to_doc, id_to_meta, results_pool
        )
        self._add_value_table_matches(
            query_info, top_k, all_data, id_to_doc, id_to_meta, results_pool
        )
        self._apply_domain_ranking(query_info, results_pool)

        results = [candidate.to_result() for candidate in results_pool.values()]
        results = sorted(results, key=lambda item: item.score, reverse=True)[:top_k]
        return get_reranker().rerank(query_info.normalized, results)

    def hybrid_search_legacy(
        self, query: str, top_k: int
    ) -> list[tuple[str, dict[str, Any], float]]:
        legacy_results = []
        for result in self.hybrid_search(query, top_k):
            distance = result.meta.get("_distance")
            if distance is None:
                distance = 0.1 if result.clause_match else 0.45 if result.bm25_score else 1.0
            legacy_results.append((result.text, result.meta, float(distance)))
        return legacy_results

    def _candidate_for(
        self,
        doc_id: str,
        id_to_doc: dict[str, str],
        id_to_meta: dict[str, dict[str, Any]],
        results_pool: dict[str, RetrievalCandidate],
    ) -> RetrievalCandidate:
        if doc_id not in results_pool:
            results_pool[doc_id] = RetrievalCandidate(
                doc_id=doc_id,
                text=id_to_doc[doc_id],
                meta=dict(id_to_meta.get(doc_id, {})),
            )
        return results_pool[doc_id]

    def _add_clause_matches(
        self,
        query_info: QueryInfo,
        all_data: dict[str, Any],
        id_to_doc: dict[str, str],
        id_to_meta: dict[str, dict[str, Any]],
        results_pool: dict[str, RetrievalCandidate],
    ) -> None:
        if not query_info.clause_numbers:
            return

        for index, meta in enumerate(all_data["metadatas"]):
            title = meta.get("title", "")
            clause_number = meta.get("clause_number", "")
            if not matches_requested_spec(query_info, meta):
                continue
            for clause_num in query_info.clause_numbers:
                doc_id = all_data["ids"][index]
                text = id_to_doc.get(doc_id, "")
                title_text = str(title or "")
                section_type = infer_section_type(meta, text)
                has_clause_heading = (
                    clause_number == clause_num
                    or title_text.startswith(clause_num)
                    or title_text.startswith(f"{clause_num} ")
                    or text_contains_clause_heading(title_text, clause_num)
                    or (section_type == "body" and text_contains_clause_heading(text, clause_num))
                )
                has_clause_reference = text_mentions_clause(
                    title_text, clause_num
                ) or text_mentions_clause(text, clause_num)
                if has_clause_heading or has_clause_reference:
                    candidate = self._candidate_for(doc_id, id_to_doc, id_to_meta, results_pool)
                    candidate.clause_match = True
                    candidate.meta["matched_clause_number"] = clause_num
                    candidate.meta["clause_match_kind"] = (
                        "heading" if has_clause_heading else "reference"
                    )
                    boost = (
                        self.config.retrieval_clause_boost
                        if has_clause_heading
                        else self.config.retrieval_clause_boost * 0.45
                    )
                    candidate.score += boost
                    candidate.add_source("clause")
                    reason = (
                        "clause exact match" if has_clause_heading else "clause reference match"
                    )
                    candidate.add_reason(f"{reason} {clause_num}")
                    logging.info("条文号精准匹配: %s -> 块%s", clause_num, index)
                    break

    def _add_bm25_matches(
        self,
        query_info: QueryInfo,
        top_k: int,
        all_data: dict[str, Any],
        id_to_doc: dict[str, str],
        id_to_meta: dict[str, dict[str, Any]],
        results_pool: dict[str, RetrievalCandidate],
    ) -> None:
        if not self.bm25_index:
            return

        bm25_scores = self.bm25_index.get_scores(tokenize_chinese(query_info.normalized))
        top_indices = sorted(
            range(len(bm25_scores)), key=lambda index: bm25_scores[index], reverse=True
        )[: top_k * 10]
        for index in top_indices:
            doc_id = all_data["ids"][index]
            score = float(bm25_scores[index])
            if score > 0:
                candidate = self._candidate_for(doc_id, id_to_doc, id_to_meta, results_pool)
                candidate.bm25_score = score
                candidate.score += score * self.config.retrieval_bm25_weight
                candidate.add_source("bm25")
                reason = "bm25 strong keyword match" if score > 5 else "bm25 keyword match"
                candidate.add_reason(reason)

    def _add_table_intent_matches(
        self,
        query_info: QueryInfo,
        top_k: int,
        all_data: dict[str, Any],
        id_to_doc: dict[str, str],
        id_to_meta: dict[str, dict[str, Any]],
        results_pool: dict[str, RetrievalCandidate],
    ) -> None:
        if not query_info.wants_table:
            return

        scored: list[tuple[float, int]] = []
        for index, doc_id in enumerate(all_data["ids"]):
            text = id_to_doc.get(doc_id, "")
            meta = id_to_meta.get(doc_id, {})
            if not matches_requested_spec(query_info, meta) or not infer_is_table(meta, text):
                continue
            meta_text = " ".join(
                str(meta.get(key, ""))
                for key in ("name", "code", "title", "table_id", "table_name", "clause_number")
            )
            evidence = f"{meta_text}\n{text}"
            score = 0.0
            table_id = str(meta.get("table_id") or "")
            if table_id and table_id in query_info.table_numbers:
                score += 10.0
            score += sum(
                2.0 for phrase in query_info.content_phrases if evidence_contains(evidence, phrase)
            )
            score += (
                min(
                    sum(
                        1
                        for keyword in set(query_info.content_keywords)
                        if evidence_contains(evidence, keyword)
                    ),
                    12,
                )
                * 0.4
            )
            if query_info.intent == "classification":
                score += 0.8
            if score > 0:
                scored.append((score, index))

        for score, index in sorted(scored, reverse=True)[: top_k * 5]:
            doc_id = all_data["ids"][index]
            candidate = self._candidate_for(doc_id, id_to_doc, id_to_meta, results_pool)
            candidate.score += min(score, 12.0) * 0.35
            candidate.add_source("table")
            candidate.add_reason("table intent supplemental match")

    def _add_value_table_matches(
        self,
        query_info: QueryInfo,
        top_k: int,
        all_data: dict[str, Any],
        id_to_doc: dict[str, str],
        id_to_meta: dict[str, dict[str, Any]],
        results_pool: dict[str, RetrievalCandidate],
    ) -> None:
        if query_info.intent != "value_lookup":
            return

        query_tokens = [
            token for token in tokenize_chinese(query_info.normalized) if len(token) >= 2
        ]
        scored: list[tuple[int, int]] = []
        for index, doc_id in enumerate(all_data["ids"]):
            text = id_to_doc.get(doc_id, "")
            meta = id_to_meta.get(doc_id, {})
            if not matches_requested_spec(query_info, meta):
                continue
            if infer_section_type(meta, text) == "explanation" or not infer_is_table(meta, text):
                continue
            evidence = " ".join(
                str(meta.get(key, ""))
                for key in ("name", "code", "title", "table_id", "table_name")
            )
            evidence = f"{evidence}\n{text}"
            hit_count = sum(1 for token in set(query_tokens) if token in evidence)
            if (
                query_info.table_numbers
                and str(meta.get("table_id") or "") in query_info.table_numbers
            ):
                hit_count += 10
            if hit_count:
                scored.append((hit_count, index))

        for hit_count, index in sorted(scored, reverse=True)[: top_k * 3]:
            doc_id = all_data["ids"][index]
            candidate = self._candidate_for(doc_id, id_to_doc, id_to_meta, results_pool)
            candidate.score += min(hit_count, 8) * 0.35
            candidate.add_source("table")
            candidate.add_reason("value lookup table keyword match")

    def _apply_domain_ranking(
        self,
        query_info: QueryInfo,
        results_pool: dict[str, RetrievalCandidate],
    ) -> None:
        for candidate in results_pool.values():
            meta = candidate.meta
            section_type = infer_section_type(meta, candidate.text)
            is_table = infer_is_table(meta, candidate.text)
            spec_matches = matches_requested_spec(query_info, meta)

            if not spec_matches:
                candidate.score -= 5.0
                candidate.add_source("domain")
                candidate.add_reason("de-prioritizes non-requested spec")
                if query_info.spec_codes or query_info.spec_names:
                    continue
            elif query_info.spec_codes or query_info.spec_names:
                candidate.score += 1.5
                candidate.add_source("domain")
                candidate.add_reason("requested spec match")

            if query_info.intent == "value_lookup":
                if section_type == "explanation":
                    candidate.score -= 1.5
                    candidate.add_source("domain")
                    candidate.add_reason("value lookup de-prioritizes explanation")
                elif section_type == "body_table" or is_table:
                    candidate.score += 3.0
                    candidate.add_source("domain")
                    candidate.add_reason("value lookup prefers body table")
                    self._apply_value_lookup_evidence_ranking(query_info, candidate)
                elif section_type == "body":
                    candidate.score += 1.0
                    candidate.add_source("domain")
                    candidate.add_reason("value lookup prefers body clause")
            elif query_info.wants_table:
                if section_type == "explanation":
                    candidate.score -= 1.5
                    candidate.add_source("domain")
                    candidate.add_reason("table query de-prioritizes explanation")
                elif section_type == "body_table" or is_table:
                    candidate.score += 7.5 if asks_for_table_identifier(query_info) else 5.0
                    candidate.add_source("domain")
                    candidate.add_reason("table query prefers body table")
                    self._apply_table_evidence_ranking(query_info, candidate)
                elif section_type == "body":
                    candidate.score -= 2.0 if asks_for_table_identifier(query_info) else 0.5
                    candidate.add_source("domain")
                    candidate.add_reason("table query accepts body clause")
                    self._apply_body_content_evidence_ranking(query_info, candidate)
            elif query_info.intent == "clause_requirement":
                clause_match_kind = str(meta.get("clause_match_kind") or "")
                if section_type == "explanation":
                    candidate.score -= 3.5
                    candidate.add_source("domain")
                    candidate.add_reason("clause query de-prioritizes explanation")
                elif clause_match_kind == "heading" and section_type in {"body", "body_table"}:
                    candidate.score += 2.5
                    candidate.add_source("domain")
                    candidate.add_reason("clause query prefers exact body evidence")
                elif section_type in {"body", "body_table"}:
                    candidate.score += 0.5
                    candidate.add_source("domain")
                    candidate.add_reason("clause query accepts body evidence")
            elif query_info.intent == "definition":
                if section_type == "explanation":
                    candidate.score -= 1.2
                    candidate.add_source("domain")
                    candidate.add_reason("definition query de-prioritizes explanation")
                elif section_type in {"body", "body_table"}:
                    candidate.score += 0.8
                    candidate.add_source("domain")
                    candidate.add_reason("definition query prefers normative body")
                    self._apply_body_content_evidence_ranking(query_info, candidate)
            elif query_info.intent == "formula":
                if section_type == "formula":
                    candidate.score += 3.0
                    candidate.add_source("domain")
                    candidate.add_reason("formula query prefers formula chunk")
                elif section_type == "body":
                    candidate.score += 1.0
                    candidate.add_source("domain")
                    candidate.add_reason("formula query accepts body clause")
                elif is_table:
                    candidate.score -= 1.0
                    candidate.add_source("domain")
                    candidate.add_reason("formula query de-prioritizes table")

    def _apply_value_lookup_evidence_ranking(
        self, query_info: QueryInfo, candidate: RetrievalCandidate
    ) -> None:
        meta_text = " ".join(
            str(candidate.meta.get(key, "")) for key in ("name", "code", "title", "table_name")
        )
        evidence = f"{meta_text}\n{candidate.text}"
        matched_phrases = [
            phrase for phrase in query_info.content_phrases if evidence_contains(evidence, phrase)
        ]
        matched_keywords = [
            keyword
            for keyword in query_info.content_keywords
            if evidence_contains(evidence, keyword)
        ]

        if len(query_info.content_phrases) > 1 and not evidence_contains(
            evidence, query_info.content_phrases[0]
        ):
            candidate.score -= 1.0
            candidate.add_reason("value lookup misses primary query phrase")
        if matched_phrases:
            phrase_score = 0.0
            for index, phrase in enumerate(query_info.content_phrases):
                if evidence_contains(evidence, phrase):
                    phrase_score += 3.0 if index == 0 else 1.0
            candidate.score += phrase_score
            candidate.add_reason("value lookup matches query content phrases")
        if matched_keywords:
            candidate.score += min(len(matched_keywords), 10) * 0.25
            candidate.add_reason("value lookup matches query content keywords")

    def _apply_table_evidence_ranking(
        self, query_info: QueryInfo, candidate: RetrievalCandidate
    ) -> None:
        meta_text = " ".join(
            str(candidate.meta.get(key, ""))
            for key in ("name", "code", "title", "table_id", "table_name")
        )
        evidence = f"{meta_text}\n{candidate.text}"
        table_id = str(candidate.meta.get("table_id") or "")
        matched_phrases = [
            phrase for phrase in query_info.content_phrases if evidence_contains(evidence, phrase)
        ]
        matched_keywords = [
            keyword
            for keyword in query_info.content_keywords
            if evidence_contains(evidence, keyword)
        ]

        if table_id and table_id in query_info.table_numbers:
            candidate.score += 5.0
            candidate.add_reason("table id exact match")
        if matched_phrases:
            candidate.score += min(len(matched_phrases), 5) * 1.0
            candidate.add_reason("table evidence matches query content phrases")
        if matched_keywords:
            candidate.score += min(len(matched_keywords), 10) * 0.15
            candidate.add_reason("table evidence matches query content keywords")

    def _apply_body_content_evidence_ranking(
        self, query_info: QueryInfo, candidate: RetrievalCandidate
    ) -> None:
        if query_info.intent not in {"classification", "definition"} and not query_info.wants_table:
            return
        meta_text = " ".join(
            str(candidate.meta.get(key, "")) for key in ("name", "code", "title", "clause_number")
        )
        evidence = f"{meta_text}\n{candidate.text}"
        specific_keywords = specific_content_keywords(query_info)
        if not specific_keywords:
            return

        matched_specific = [
            keyword for keyword in specific_keywords if evidence_contains(evidence, keyword)
        ]
        if matched_specific:
            candidate.score += min(len(matched_specific), 4) * 0.7
            candidate.add_reason("body evidence matches specific query content")
        else:
            candidate.score -= 0.8
            candidate.add_reason("body evidence misses specific query content")


retrieval_state = RetrievalState()
