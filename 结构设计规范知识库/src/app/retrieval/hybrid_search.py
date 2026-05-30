import logging
import re
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
    from zhipuai import ZhipuAI
except ImportError:
    ZhipuAI = None

from ..core.config import Settings, settings
from ..rerank.factory import get_reranker
from .models import RetrievalCandidate, RetrievalResult
from .query import QueryInfo, analyze_query


def tokenize_chinese(text: str) -> list[str]:
    normalized = re.sub(r"[^一-鿿\w]", " ", text.lower())
    words = normalized.split()
    chars = list("".join(words))
    trigrams = ["".join(chars[i : i + 3]) for i in range(len(chars) - 2)]
    return words + trigrams


class RetrievalState:
    def __init__(self, config: Settings = settings) -> None:
        self.config = config
        self.zhipu_client: Any = None
        self.chroma_collection: Any = None
        self.bm25_index: Any = None
        self.bm25_texts: list[str] = []

    def initialize(self) -> None:
        self._initialize_embedding_client()
        self._initialize_chroma_and_bm25()

    def _initialize_embedding_client(self) -> None:
        if not self.config.zhipuai_api_key:
            return
        if ZhipuAI is None:
            logging.error("ZhipuAI SDK 未安装，无法初始化向量检索客户端")
            return
        try:
            self.zhipu_client = ZhipuAI(api_key=self.config.zhipuai_api_key)
            logging.info("ZhipuAI 初始化成功")
        except Exception as exc:
            logging.error("ZhipuAI 初始化失败: %s", exc)

    def _initialize_chroma_and_bm25(self) -> None:
        try:
            if chromadb is None:
                logging.error("ChromaDB 未安装，无法初始化知识库")
                return
            self.config.db_dir.mkdir(parents=True, exist_ok=True)
            db_client = chromadb.PersistentClient(path=str(self.config.db_dir))
            self.chroma_collection = db_client.get_or_create_collection(name=self.config.collection_name)
            count = self.chroma_collection.count()
            logging.info("ChromaDB: %s 条", count)

            if count > 0:
                if BM25Okapi is None:
                    logging.error("rank-bm25 未安装，跳过 BM25 索引构建")
                    return
                all_data = self.chroma_collection.get()
                all_texts = [doc or "" for doc in all_data["documents"]]
                tokenized = [tokenize_chinese(text) for text in all_texts]
                self.bm25_index = BM25Okapi(tokenized)
                self.bm25_texts = all_texts
                logging.info("BM25 索引构建完成: %s 条", len(self.bm25_texts))
        except Exception as exc:
            logging.error("ChromaDB/BM25 初始化失败: %s", exc)

    @property
    def ready(self) -> bool:
        return bool(self.chroma_collection and self.zhipu_client)

    def chroma_count(self) -> int:
        if not self.chroma_collection:
            return -1
        try:
            return self.chroma_collection.count()
        except Exception:
            return -1

    def hybrid_search(self, query: str, top_k: int) -> list[RetrievalResult]:
        if not self.chroma_collection:
            return []

        query_info = analyze_query(query)
        all_data = self.chroma_collection.get()
        id_to_doc = dict(zip(all_data["ids"], all_data["documents"]))
        id_to_meta = dict(zip(all_data["ids"], all_data["metadatas"]))
        results_pool: dict[str, RetrievalCandidate] = {}

        if self.zhipu_client:
            try:
                response = self.zhipu_client.embeddings.create(
                    model=self.config.embedding_model,
                    input=[query],
                )
                embedding = response.data[0].embedding
                results = self.chroma_collection.query(query_embeddings=[embedding], n_results=top_k * 5)
                for doc_id, distance in zip(results["ids"][0], results["distances"][0]):
                    if doc_id in id_to_doc:
                        candidate = self._candidate_for(doc_id, id_to_doc, id_to_meta, results_pool)
                        candidate.dense_score = 1 / (1 + float(distance))
                        candidate.meta["_distance"] = float(distance)
                        candidate.score += candidate.dense_score * self.config.retrieval_dense_weight
                        candidate.add_source("dense")
                        candidate.add_reason("dense semantic match")
            except Exception as exc:
                logging.error("向量检索失败: %s", exc)

        self._add_clause_matches(query_info, all_data, id_to_doc, id_to_meta, results_pool)
        self._add_bm25_matches(query_info, top_k, all_data, id_to_doc, id_to_meta, results_pool)

        results = [candidate.to_result() for candidate in results_pool.values()]
        results = sorted(results, key=lambda item: item.score, reverse=True)[:top_k]
        return get_reranker().rerank(query_info.normalized, results)

    def hybrid_search_legacy(self, query: str, top_k: int) -> list[tuple[str, dict[str, Any], float]]:
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
            spec_text = " ".join(str(meta.get(key, "")) for key in ("code", "name", "source_file"))
            if query_info.spec_codes and not any(code in spec_text for code in query_info.spec_codes):
                continue
            if query_info.spec_names and not any(name in spec_text for name in query_info.spec_names):
                continue
            for clause_num in query_info.clause_numbers:
                if clause_number == clause_num or title.startswith(clause_num) or title.startswith(f"{clause_num} "):
                    doc_id = all_data["ids"][index]
                    candidate = self._candidate_for(doc_id, id_to_doc, id_to_meta, results_pool)
                    candidate.clause_match = True
                    candidate.score += self.config.retrieval_clause_boost
                    candidate.add_source("clause")
                    candidate.add_reason(f"clause exact match {clause_num}")
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
        top_indices = sorted(range(len(bm25_scores)), key=lambda index: bm25_scores[index], reverse=True)[: top_k * 10]
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


retrieval_state = RetrievalState()
