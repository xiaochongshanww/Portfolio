from src.evaluation.runner import load_cases


def test_evaluation_cases_are_available():
    cases = load_cases()
    assert len(cases) >= 20


def test_static_console_contains_required_sections():
    from pathlib import Path

    html = Path("src/static/index.html").read_text(encoding="utf-8")
    assert "服务状态" in html
    assert "轻量问答测试" in html
    assert "知识库文档" in html
    assert "/knowledge/documents" in html
    assert "/evaluation/status" in html
    assert "Open WebUI" in html
