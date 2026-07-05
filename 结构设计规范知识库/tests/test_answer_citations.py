from src.app.rag.citations import normalize_answer_citations, remove_unsupported_precise_citations


def test_normalize_answer_citations_removes_unoffered_and_adds_verified_source():
    trace = {
        "sources": [{"code": "GB 50009-2012"}],
        "image_urls": ["https://kb.example/page-images/spec.pdf/30"],
    }
    answer = "【结论】内容。\n![错误](https://kb.example/page-images/spec.pdf/99)"

    result = normalize_answer_citations(answer, trace)

    assert "/99" not in result
    assert "![来源页面](https://kb.example/page-images/spec.pdf/30)" in result
    assert "GB 50009-2012" in result


def test_normalize_answer_citations_unwraps_markdown_image_code():
    trace = {
        "sources": [{"code": "GB 50009-2012"}],
        "image_urls": ["/page-images/spec.pdf/30"],
    }
    answer = "【依据】GB 50009-2012\n`![第30页](/page-images/spec.pdf/30)`"
    result = normalize_answer_citations(answer, trace)
    assert "`![" not in result
    assert "![第30页](/page-images/spec.pdf/30)" in result


def test_remove_unsupported_precise_table_citation():
    trace = {
        "sources": [{"code": "GB 50009-2012", "table_id": "8.1.1"}],
        "mentioned_tables": [],
    }
    result = remove_unsupported_precise_citations(
        "依据GB 50009-2012表8.1.1，参数另见表8.3.1。",
        trace,
    )
    assert "表8.1.1" in result
    assert "表8.3.1" not in result
    assert "相关表格" in result
