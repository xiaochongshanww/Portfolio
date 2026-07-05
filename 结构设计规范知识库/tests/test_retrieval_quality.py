import json
from pathlib import Path

from src.app.rag.context import format_result_context
from src.app.rag.service import _image_url
from src.app.rerank.noop import NoopReranker
from src.app.retrieval.models import RetrievalCandidate, RetrievalResult
from src.app.retrieval.query import analyze_query, extract_content_keywords, extract_content_phrases
from src.app.retrieval.hybrid_search import (
    RetrievalState,
    infer_is_table,
    infer_section_type,
    matches_requested_spec,
    text_contains_clause_heading,
    text_mentions_clause,
)
from src.evaluation.runner import EvaluationCase, summarize_results


def test_query_analysis_extracts_clause_code_and_alias():
    info = analyze_query("GB50011 第 8.2.1 条，抗规怎么要求？")
    assert "8.2.1" in info.clause_numbers
    assert "GB 50011" in info.spec_codes
    assert "抗规" in info.spec_aliases
    assert "建筑抗震设计规范" in info.spec_names
    assert info.intent == "clause_requirement"


def test_query_analysis_prioritizes_explicit_clause_over_definition_words():
    info = analyze_query("抗震规范第 8.2.1 条是什么？")
    assert "8.2.1" in info.clause_numbers
    assert info.intent == "clause_requirement"


def test_query_analysis_detects_value_lookup_table_intent():
    info = analyze_query("办公楼的楼面活荷载标准值取多少")
    assert info.intent == "value_lookup"
    assert info.wants_table is True
    assert "办公楼" in info.content_phrases
    assert "楼面活荷载" in info.content_phrases
    assert "办公楼" in info.content_keywords
    assert "楼面" in info.content_keywords


def test_query_analysis_detects_terse_standard_value_lookup_without_verb():
    info = analyze_query("不上人屋面均布活荷载标准值")
    assert info.intent == "value_lookup"
    assert info.wants_table is True


def test_query_analysis_detects_classification_as_table_intent():
    info = analyze_query("建筑结构安全等级如何划分？")
    assert info.intent == "classification"
    assert info.wants_table is True
    assert "建筑结构安全等级" in info.content_phrases


def test_query_analysis_extracts_explicit_table_number():
    info = analyze_query("荷载规范表5.1.2的折减系数怎么取？")
    assert "5.1.2" in info.table_numbers
    assert "5.1.2" not in info.clause_numbers
    assert info.wants_table is True


def test_query_analysis_does_not_treat_standard_value_relationship_as_lookup():
    info = analyze_query("材料强度标准值和设计值有什么关系？")
    assert info.intent == "definition"
    assert info.wants_table is False


def test_query_analysis_prioritizes_formula_over_value_terms():
    info = analyze_query("雪荷载标准值的计算公式是什么？")
    assert info.intent == "formula"


def test_content_keyword_extraction_removes_intent_words():
    phrases = extract_content_phrases("办公楼的楼面活荷载标准值取多少")
    keywords = extract_content_keywords("办公楼的楼面活荷载标准值取多少")
    assert phrases == ["办公楼", "楼面活荷载"]
    assert "标准值" not in keywords
    assert "取多少" not in keywords
    assert "楼的" not in keywords
    assert "办公楼" in keywords


def test_clause_heading_can_be_found_inside_chunk_text():
    text = "8.2计算要点\n8.2.1钢结构应按本节规定调整地震作用效应。"
    assert text_contains_clause_heading(text, "8.2.1")
    assert text_contains_clause_heading("第 8.2.1 条 钢结构应符合要求", "8.2.1")
    assert text_mentions_clause("应符合第8.2.1条规定", "8.2.1")
    assert not text_contains_clause_heading(text, "8.2.10")


def test_image_url_is_encoded_for_markdown_targets():
    assert (
        _image_url("GB 50011-2010_建筑抗震设计规范_2016年版_mineru_0124.jpg")
        == "/images/GB%2050011-2010_%E5%BB%BA%E7%AD%91%E6%8A%97%E9%9C%87%E8%AE%BE%E8%AE%A1%E8%A7%84%E8%8C%83_2016%E5%B9%B4%E7%89%88_mineru_0124.jpg"
    )


def test_retrieval_candidate_combines_reasons_and_sources():
    candidate = RetrievalCandidate(doc_id="1", text="正文", meta={"source": "a.pdf"})
    candidate.score += 1
    candidate.add_source("dense")
    candidate.add_source("bm25")
    candidate.add_reason("dense semantic match")
    candidate.add_reason("bm25 keyword match")
    result = candidate.to_result()
    assert result.source == "bm25+dense"
    assert "dense semantic match" in result.reason
    assert "bm25 keyword match" in result.reason


def test_noop_reranker_preserves_order():
    results = [
        RetrievalResult("a", "A", {}, 2.0, "dense", "dense"),
        RetrievalResult("b", "B", {}, 1.0, "bm25", "bm25"),
    ]
    assert NoopReranker().rerank("query", results) == results


def test_domain_ranking_prefers_body_table_for_value_lookup():
    state = RetrievalState()
    query_info = analyze_query("办公楼的楼面活荷载标准值取多少")
    table = RetrievalCandidate(
        doc_id="table",
        text="表5.1.1 办公室 2.0",
        meta={"name": "建筑结构荷载规范", "section_type": "body_table", "is_table": True, "table_id": "5.1.1"},
        score=1.0,
    )
    explanation = RetrievalCandidate(
        doc_id="explanation",
        text="条文说明 办公楼 2.0 至 2.5",
        meta={"name": "建筑结构荷载规范", "section_type": "explanation", "is_table": False},
        score=3.0,
    )
    pool = {"table": table, "explanation": explanation}
    state._apply_domain_ranking(query_info, pool)
    assert table.score > explanation.score
    assert "value lookup prefers body table" in table.reasons
    assert "value lookup de-prioritizes explanation" in explanation.reasons


def test_domain_ranking_prefers_body_for_clause_queries():
    state = RetrievalState()
    query_info = analyze_query("抗震规范第 8.2.1 条是什么？")
    body = RetrievalCandidate(
        doc_id="body",
        text="8.2.1 钢结构应按本节规定调整地震作用效应。",
        meta={"name": "建筑抗震设计规范", "section_type": "body", "is_table": False},
        score=1.0,
    )
    explanation = RetrievalCandidate(
        doc_id="explanation",
        text="条文说明 8.2.1 背景解释",
        meta={"name": "建筑抗震设计规范", "section_type": "explanation", "is_table": False},
        score=2.0,
    )
    pool = {"body": body, "explanation": explanation}
    state._apply_domain_ranking(query_info, pool)
    assert body.score > explanation.score
    assert "clause query accepts body evidence" in body.reasons
    assert "clause query de-prioritizes explanation" in explanation.reasons


def test_domain_ranking_prefers_exact_body_table_for_clause_queries():
    state = RetrievalState()
    query_info = analyze_query("抗震规范第4.1.3条关于土的类型如何规定？")
    table = RetrievalCandidate(
        doc_id="table",
        text="表4.1.3 土的类型划分和剪切波速范围",
        meta={"name": "建筑抗震设计规范", "section_type": "body_table", "is_table": True, "clause_match_kind": "heading"},
        score=1.0,
    )
    body_reference = RetrievalCandidate(
        doc_id="body-reference",
        text="可按第4.1.3条划分土的类型。",
        meta={"name": "建筑抗震设计规范", "section_type": "body", "clause_match_kind": "reference"},
        score=2.0,
    )
    pool = {"table": table, "body-reference": body_reference}
    state._apply_domain_ranking(query_info, pool)
    assert table.score > body_reference.score
    assert "clause query prefers exact body evidence" in table.reasons


def test_domain_ranking_promotes_specific_content_for_classification_queries():
    state = RetrievalState()
    query_info = analyze_query("中小学校舍抗震设防类别如何确定？")
    generic = RetrievalCandidate(
        doc_id="generic",
        text="建筑抗震设防类别划分应根据社会影响确定。",
        meta={"name": "建筑工程抗震设防分类标准", "section_type": "body"},
        score=5.0,
    )
    specific = RetrievalCandidate(
        doc_id="specific",
        text="所有幼儿园、小学和中学的教学用房设防类别均予以提高。",
        meta={"name": "建筑工程抗震设防分类标准", "section_type": "body"},
        score=4.5,
    )
    pool = {"generic": generic, "specific": specific}
    state._apply_domain_ranking(query_info, pool)
    assert specific.score > generic.score
    assert "body evidence matches specific query content" in specific.reasons
    assert "body evidence misses specific query content" in generic.reasons


def test_domain_ranking_prefers_formula_chunks_for_formula_queries():
    state = RetrievalState()
    query_info = analyze_query("雪荷载标准值的计算公式是什么？")
    formula = RetrievalCandidate(
        doc_id="formula",
        text="s_k = mu_r s_0",
        meta={"section_type": "formula", "is_table": False},
        score=1.0,
    )
    table = RetrievalCandidate(
        doc_id="table",
        text="表3.2.5 调整系数",
        meta={"section_type": "body_table", "is_table": True},
        score=3.0,
    )
    pool = {"formula": formula, "table": table}
    state._apply_domain_ranking(query_info, pool)
    assert formula.score > table.score
    assert "formula query prefers formula chunk" in formula.reasons
    assert "formula query de-prioritizes table" in table.reasons


def test_domain_ranking_infers_legacy_table_metadata():
    assert infer_section_type({"chunk_type": "table", "title": "表5.1.1 民用建筑楼面均布活荷载"}) == "body_table"
    assert infer_is_table({"chunk_type": "text", "title": "表5.1.1 民用建筑楼面均布活荷载"}) is True
    assert infer_is_table({"chunk_type": "text", "title": "5.1.2", "table_id": ""}, "本规范表5.1.1中楼面活荷载标准值") is False
    assert infer_section_type({"chunk_type": "explanation", "title": "5.1民用建筑楼面均布活荷载"}) == "explanation"
    assert (
        infer_section_type({"chunk_type": "table", "title": "表2全国部分城市建筑楼面活荷载统计分析表", "clause_number": "0.386"})
        == "explanation"
    )


def test_value_table_match_adds_relevant_body_table_candidate():
    state = RetrievalState()
    query_info = analyze_query("办公楼的楼面活荷载标准值取多少")
    all_data = {
        "ids": ["table", "explanation"],
        "metadatas": [
            {"chunk_type": "table", "title": "表5.1.1 民用建筑楼面均布活荷载标准值", "clause_number": "5.1.1", "name": "建筑结构荷载规范"},
            {"chunk_type": "table", "title": "表2全国部分城市建筑楼面活荷载统计分析表", "clause_number": "0.386", "name": "建筑结构荷载规范"},
        ],
    }
    id_to_doc = {
        "table": "表5.1.1 民用建筑楼面均布活荷载标准值 办公楼 2.0",
        "explanation": "办公室 楼面活荷载 标准值 2.0",
    }
    id_to_meta = dict(zip(all_data["ids"], all_data["metadatas"]))
    pool: dict[str, RetrievalCandidate] = {}
    state._add_value_table_matches(query_info, 5, all_data, id_to_doc, id_to_meta, pool)
    assert "table" in pool
    assert "explanation" not in pool
    assert "value lookup table keyword match" in pool["table"].reasons


def test_table_intent_match_adds_classification_table_candidate():
    state = RetrievalState()
    query_info = analyze_query("建筑工程分部工程和分项工程划分在哪个表？")
    all_data = {
        "ids": ["clause", "table"],
        "metadatas": [
            {"chunk_type": "text", "title": "4建筑工程质量验收的划分", "code": "GB 50300-2013", "name": "建筑工程施工质量验收统一标准"},
            {"chunk_type": "table", "title": "表B建筑工程的分部工程、分项工程划分", "code": "GB 50300-2013", "name": "建筑工程施工质量验收统一标准"},
        ],
    }
    id_to_doc = {
        "clause": "4.0.1 建筑工程施工质量验收应划分为单位工程、分部工程、分项工程和检验批。",
        "table": "表B建筑工程的分部工程、分项工程划分 <table><tr><td>分部工程</td><td>分项工程</td></tr></table>",
    }
    id_to_meta = dict(zip(all_data["ids"], all_data["metadatas"]))
    pool: dict[str, RetrievalCandidate] = {}
    state._add_table_intent_matches(query_info, 5, all_data, id_to_doc, id_to_meta, pool)
    assert "table" in pool
    assert "clause" not in pool
    assert "table intent supplemental match" in pool["table"].reasons


def test_domain_ranking_prefers_table_when_query_asks_which_table():
    state = RetrievalState()
    query_info = analyze_query("建筑工程分部工程和分项工程划分在哪个表？")
    body = RetrievalCandidate(
        doc_id="body",
        text="建筑工程施工质量验收应划分为单位工程、分部工程、分项工程和检验批。",
        meta={"name": "建筑工程施工质量验收统一标准", "section_type": "body"},
        score=10.0,
    )
    table = RetrievalCandidate(
        doc_id="table",
        text="表B建筑工程的分部工程、分项工程划分",
        meta={"name": "建筑工程施工质量验收统一标准", "section_type": "body_table", "is_table": True},
        score=8.0,
    )
    pool = {"body": body, "table": table}
    state._apply_domain_ranking(query_info, pool)
    assert table.score > body.score
    assert "table query prefers body table" in table.reasons


def test_value_table_match_uses_table_title_as_evidence():
    state = RetrievalState()
    query_info = analyze_query("活荷载按楼层的折减系数应查哪个表")
    all_data = {
        "ids": ["table"],
        "metadatas": [
            {
                "chunk_type": "table",
                "title": "表5.1.2 活荷载按楼层的折减系数",
                "clause_number": "5.1.2",
                "code": "GB 50009-2012",
                "name": "建筑结构荷载规范",
            },
        ],
    }
    id_to_doc = {"table": "<table><tr><td>1</td><td>0.9</td></tr></table>"}
    id_to_meta = dict(zip(all_data["ids"], all_data["metadatas"]))
    pool: dict[str, RetrievalCandidate] = {}
    state._add_value_table_matches(query_info, 5, all_data, id_to_doc, id_to_meta, pool)
    assert "table" in pool
    assert "value lookup table keyword match" in pool["table"].reasons


def test_value_table_match_prioritizes_explicit_table_id():
    state = RetrievalState()
    query_info = analyze_query("荷载规范表5.1.2的折减系数怎么取？")
    all_data = {
        "ids": ["table-a", "table-b"],
        "metadatas": [
            {
                "chunk_type": "table",
                "title": "表5.1.1 民用建筑楼面均布活荷载标准值",
                "table_id": "5.1.1",
                "code": "GB 50009-2012",
                "name": "建筑结构荷载规范",
            },
            {
                "chunk_type": "table",
                "title": "表5.1.2 活荷载按楼层的折减系数",
                "table_id": "5.1.2",
                "code": "GB 50009-2012",
                "name": "建筑结构荷载规范",
            },
        ],
    }
    id_to_doc = {"table-a": "折减系数", "table-b": "折减系数"}
    id_to_meta = dict(zip(all_data["ids"], all_data["metadatas"]))
    pool: dict[str, RetrievalCandidate] = {}
    state._add_value_table_matches(query_info, 5, all_data, id_to_doc, id_to_meta, pool)
    assert pool["table-b"].score > pool["table-a"].score


def test_value_lookup_evidence_ranking_prefers_content_keyword_match():
    state = RetrievalState()
    query_info = analyze_query("办公楼的楼面活荷载标准值取多少")
    matching_table = RetrievalCandidate(
        doc_id="matching",
        text="表5.1.1 民用建筑楼面均布活荷载标准值 办公楼 2.0",
        meta={"name": "建筑结构荷载规范", "title": "表5.1.1 民用建筑楼面均布活荷载标准值"},
        score=5.0,
    )
    generic_table = RetrievalCandidate(
        doc_id="generic",
        text="表5.3.1 均布活荷载标准值",
        meta={"name": "建筑结构荷载规范", "title": "表5.3.1 均布活荷载标准值"},
        score=6.0,
    )
    state._apply_value_lookup_evidence_ranking(query_info, matching_table)
    state._apply_value_lookup_evidence_ranking(query_info, generic_table)
    assert matching_table.score > generic_table.score
    assert "value lookup matches query content phrases" in matching_table.reasons
    assert "value lookup matches query content keywords" in matching_table.reasons
    assert "value lookup misses primary query phrase" in generic_table.reasons


def test_requested_spec_matching_filters_other_codes():
    query_info = analyze_query("GB50009 里的雪荷载怎么取值？")
    assert matches_requested_spec(query_info, {"code": "GB 50009-2012", "name": "建筑结构荷载规范"})
    assert not matches_requested_spec(query_info, {"code": "GB 50011-2010", "name": "建筑抗震设计规范"})


def test_domain_ranking_boosts_requested_spec_and_penalizes_other_specs():
    state = RetrievalState()
    query_info = analyze_query("GB50009 里的雪荷载怎么取值？")
    requested = RetrievalCandidate(
        doc_id="requested",
        text="雪荷载标准值",
        meta={"code": "GB 50009-2012", "name": "建筑结构荷载规范", "section_type": "body"},
        score=3.0,
    )
    other = RetrievalCandidate(
        doc_id="other",
        text="雪荷载标准值",
        meta={"code": "GB 50011-2010", "name": "建筑抗震设计规范", "section_type": "body_table", "is_table": True},
        score=6.0,
    )
    pool = {"requested": requested, "other": other}
    state._apply_domain_ranking(query_info, pool)
    assert requested.score > other.score
    assert "requested spec match" in requested.reasons
    assert "de-prioritizes non-requested spec" in other.reasons


def test_table_evidence_ranking_boosts_table_id_and_name_matches():
    state = RetrievalState()
    query_info = analyze_query("表5.1.2活荷载按楼层的折减系数")
    candidate = RetrievalCandidate(
        doc_id="table",
        text="<table><tr><td>折减系数</td></tr></table>",
        meta={"table_id": "5.1.2", "title": "表5.1.2 活荷载按楼层的折减系数"},
        score=1.0,
    )
    state._apply_table_evidence_ranking(query_info, candidate)
    assert candidate.score > 6.0
    assert "table id exact match" in candidate.reasons
    assert "table evidence matches query content phrases" in candidate.reasons


def test_clause_reference_match_gets_weaker_boost_than_heading_match():
    state = RetrievalState()
    query_info = analyze_query("抗震规范第8.2.1条是什么？")
    all_data = {
        "ids": ["heading", "reference"],
        "metadatas": [
            {"title": "8.2计算要点", "clause_number": "8.2", "name": "建筑抗震设计规范"},
            {"title": "8.3其他要求", "clause_number": "8.3", "name": "建筑抗震设计规范"},
        ],
    }
    id_to_doc = {
        "heading": "8.2.1 钢结构应按本节规定调整地震作用效应。",
        "reference": "本条可参照第8.2.1条执行。",
    }
    id_to_meta = dict(zip(all_data["ids"], all_data["metadatas"]))
    pool: dict[str, RetrievalCandidate] = {}
    state._add_clause_matches(query_info, all_data, id_to_doc, id_to_meta, pool)
    assert pool["heading"].score > pool["reference"].score
    assert "clause exact match 8.2.1" in pool["heading"].reasons
    assert "clause reference match 8.2.1" in pool["reference"].reasons


def test_clause_heading_does_not_treat_explanation_reference_as_exact_match():
    state = RetrievalState()
    query_info = analyze_query("荷载规范第5.1.3条对消防车活荷载有什么规定？")
    all_data = {
        "ids": ["explanation", "body"],
        "metadatas": [
            {"title": "条文说明", "clause_number": "0.386", "chunk_type": "explanation", "name": "建筑结构荷载规范"},
            {"title": "5.1民用建筑楼面均布活荷载", "clause_number": "5.1", "chunk_type": "text", "name": "建筑结构荷载规范"},
        ],
    }
    id_to_doc = {
        "explanation": "本次修订单独列为第5.1.3条。5.1.3消防车荷载标准值很大。",
        "body": "5.1.2 活荷载折减。\n5.1.3 消防车活荷载折减应根据经验确定。",
    }
    id_to_meta = dict(zip(all_data["ids"], all_data["metadatas"]))
    pool: dict[str, RetrievalCandidate] = {}
    state._add_clause_matches(query_info, all_data, id_to_doc, id_to_meta, pool)
    assert pool["body"].score > pool["explanation"].score
    assert pool["body"].meta["clause_match_kind"] == "heading"
    assert pool["explanation"].meta["clause_match_kind"] == "reference"


def test_rag_context_includes_source_header():
    result = RetrievalResult(
        doc_id="1",
        text="条文正文",
        meta={
            "name": "建筑抗震设计规范",
            "code": "GB 50011-2010",
            "version": "2016年版",
            "clause_number": "8.2.1",
            "pages": "10",
            "section_type": "body",
            "authority_level": 90,
            "table_id": "",
            "table_name": "",
        },
        score=5.0,
        source="clause",
        reason="clause exact match 8.2.1",
        clause_match=True,
    )
    context = format_result_context(result)
    assert "来源规范：建筑抗震设计规范" in context
    assert "规范编号：GB 50011-2010" in context
    assert "条文号：8.2.1" in context
    assert "依据类型：body" in context
    assert "权威等级：90" in context
    assert "命中原因：clause exact match 8.2.1" in context


def test_evaluation_summary_detects_hits():
    case = EvaluationCase(
        id="case-1",
        query="抗震规范第 8.2.1 条",
        expected_sources=["建筑抗震设计规范"],
        expected_clause="8.2.1",
        expected_keywords=["构件"],
    )
    result = RetrievalResult(
        doc_id="1",
        text="构件要求",
        meta={"name": "建筑抗震设计规范", "clause_number": "8.2.1"},
        score=5.0,
        source="clause",
        reason="clause exact match",
    )
    summary = summarize_results([case], {"case-1": [result]})
    assert summary["source_hit_rate"] == 1
    assert summary["top1_source_hit_rate"] == 1
    assert summary["clause_hit_rate"] == 1
    assert summary["keyword_hit_rate"] == 1
    assert summary["table_hit_rate"] == 1
    assert summary["authority_hit_rate"] == 1
    assert summary["cases_by_type"] == {"general": 1}
    assert summary["failures_by_check"] == {
        "source": 0,
        "top1_source": 0,
        "clause": 0,
        "keyword": 0,
        "table": 0,
        "authority": 0,
        "structured_table": 0,
    }


def test_evaluation_summary_accepts_clause_found_in_text():
    case = EvaluationCase(
        id="case-1",
        query="抗震规范第 8.2.1 条",
        expected_sources=["建筑抗震设计规范"],
        expected_clause="8.2.1",
        expected_keywords=["构件"],
    )
    result = RetrievalResult(
        doc_id="1",
        text="8.2 计算要点\n8.2.1 构件应按本节规定调整地震作用效应。",
        meta={"name": "建筑抗震设计规范", "clause_number": "8.2"},
        score=5.0,
        source="clause",
        reason="clause exact match",
    )
    summary = summarize_results([case], {"case-1": [result]})
    assert summary["clause_hit_rate"] == 1


def test_evaluation_summary_groups_failures():
    case = EvaluationCase(
        id="case-1",
        query="查表",
        expected_sources=["建筑结构荷载规范"],
        expected_keywords=["办公楼"],
        type="table",
    )
    result = RetrievalResult(
        doc_id="1",
        text="住宅 2.0",
        meta={"name": "建筑抗震设计规范"},
        score=1.0,
        source="dense",
        reason="dense semantic match",
    )
    summary = summarize_results([case], {"case-1": [result]})
    assert summary["failures_by_type"] == {"table": 1}
    assert summary["failures_by_check"] == {
        "source": 1,
        "top1_source": 1,
        "clause": 0,
        "keyword": 1,
        "table": 1,
        "authority": 1,
        "structured_table": 0,
    }
    assert summary["failures"][0]["failed_checks"] == ["source", "top1_source", "keyword", "table", "authority"]


def test_evaluation_summary_can_relax_top1_for_cross_spec_cases():
    case = EvaluationCase(
        id="case-1",
        query="荷载组合应考虑哪些情况？",
        expected_sources=["建筑结构荷载规范"],
        expected_keywords=["荷载组合"],
        top1_source_required=False,
    )
    results = [
        RetrievalResult(
            doc_id="1",
            text="荷载组合",
            meta={"name": "建筑结构可靠性设计统一标准", "section_type": "body"},
            score=5.0,
            source="dense",
            reason="dense semantic match",
        ),
        RetrievalResult(
            doc_id="2",
            text="荷载组合",
            meta={"name": "建筑结构荷载规范", "section_type": "body"},
            score=4.0,
            source="bm25",
            reason="bm25 keyword match",
        ),
    ]
    summary = summarize_results([case], {"case-1": results})
    assert summary["source_hit_rate"] == 1
    assert summary["top1_source_hit_rate"] == 1
    assert summary["failures"] == []


def test_evaluation_summary_uses_expected_authority_type():
    case = EvaluationCase(
        id="case-1",
        query="查表",
        expected_sources=["建筑结构荷载规范"],
        expected_keywords=["活荷载"],
        type="table",
        expected_authority_type="body_table",
    )
    result = RetrievalResult(
        doc_id="1",
        text="表5.1.1 活荷载",
        meta={"name": "建筑结构荷载规范", "section_type": "body_table", "is_table": True},
        score=5.0,
        source="table",
        reason="table query prefers body table",
    )
    summary = summarize_results([case], {"case-1": [result]})
    assert summary["authority_hit_rate"] == 1


def test_evaluation_summary_reports_top1_table_and_authority_metrics():
    case = EvaluationCase(
        id="case-1",
        query="办公楼活荷载取多少",
        expected_sources=["建筑结构荷载规范"],
        expected_keywords=["办公楼"],
        type="table",
    )
    result = RetrievalResult(
        doc_id="1",
        text="表5.1.1 民用建筑楼面均布活荷载标准值 办公楼 2.0",
        meta={"name": "建筑结构荷载规范", "section_type": "body_table", "is_table": True, "table_id": "5.1.1"},
        score=10.0,
        source="table",
        reason="value lookup prefers body table",
    )
    summary = summarize_results([case], {"case-1": [result]})
    assert summary["top1_source_hit_rate"] == 1
    assert summary["table_hit_rate"] == 1
    assert summary["authority_hit_rate"] == 1


def test_evaluation_summary_accepts_body_table_as_clause_authority():
    case = EvaluationCase(
        id="case-1",
        query="抗震规范第4.1.3条",
        expected_sources=["建筑抗震设计规范"],
        expected_clause="4.1.3",
        expected_keywords=["土的类型"],
        type="clause",
    )
    result = RetrievalResult(
        doc_id="1",
        text="表4.1.3 土的类型划分和剪切波速范围",
        meta={"name": "建筑抗震设计规范", "section_type": "body_table", "is_table": True, "clause_number": "4.1.3"},
        score=10.0,
        source="clause",
        reason="clause exact match",
    )
    summary = summarize_results([case], {"case-1": [result]})
    assert summary["authority_hit_rate"] == 1


def test_structured_table_5_1_1_sample_contains_key_live_load_rows():
    path = Path("data/structured_tables/GB_50009_2012_table_5_1_1_live_loads.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["source"]["code"] == "GB 50009-2012"
    assert payload["source"]["table_id"] == "5.1.1"
    rows = payload["rows"]

    def find_by_alias(alias: str):
        return [row for row in rows if alias in row.get("aliases", [])]

    assert find_by_alias("办公楼")[0]["standard_value"] == 2.0
    assert find_by_alias("教室")[0]["standard_value"] == 2.5
    assert find_by_alias("可能出现人员密集情况的阳台")[0]["standard_value"] == 3.5
    assert find_by_alias("其他阳台")[0]["standard_value"] == 2.5
