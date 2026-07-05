from src.evaluation.runner import load_cases


def test_evaluation_cases_are_available():
    cases = load_cases()
    assert len(cases) >= 20


def test_vue_console_contains_required_workflows():
    from pathlib import Path

    app = Path("frontend/src/App.vue").read_text(encoding="utf-8")
    review = Path("frontend/src/components/ReviewTab.vue").read_text(encoding="utf-8")
    manual = Path("frontend/src/components/ManualStructuringTab.vue").read_text(encoding="utf-8")
    structured_editor = Path("frontend/src/components/StructuredDraftEditor.vue").read_text(encoding="utf-8")
    evaluation = Path("frontend/src/components/EvaluationTab.vue").read_text(encoding="utf-8")
    overview = Path("frontend/src/components/OverviewTab.vue").read_text(encoding="utf-8")
    api = Path("frontend/src/api.ts").read_text(encoding="utf-8")
    jobs = Path("frontend/src/components/JobsTab.vue").read_text(encoding="utf-8")
    package_json = Path("frontend/package.json").read_text(encoding="utf-8")

    assert "Vue" in package_json or '"vue"' in package_json
    assert "tailwindcss" in package_json
    assert "构建任务" in app
    assert "校对工作台" in app
    assert "结构化队列" in app
    assert "问答验证" in app
    assert "/knowledge/documents" in app
    assert "/admin/evaluation/status" in app
    assert "/admin/corrections/candidates" in app
    assert "/admin/manual-structuring" in app
    assert "/admin/jobs/rebuild" in jobs
    assert "/admin/jobs/review" in jobs
    assert "/admin/corrections/approved" in review
    assert "/admin/page-image/" in review
    assert "最终修正文" in review
    assert "原 PDF 页面" in review
    assert "/admin/manual-structuring/scan" in manual
    assert "人工结构化" in manual
    assert "/draft" in manual
    assert "结构化 JSON 草稿" in manual
    assert "保存草稿" in manual
    assert "/validate" in manual
    assert "/publish" in manual
    assert "/versions" in manual
    assert "/rollback" in manual
    assert "发布历史" in manual
    assert "生成合并草稿" in manual
    assert "跨页合并任务" in manual
    assert "groupMembers" in manual
    assert "StructuredDraftEditor" in manual
    assert "专注编辑" in manual
    assert "focusEditor" in manual
    assert "AI 生成建议" in manual
    assert "AI 结构化建议" in manual
    assert "/ai-suggestion" in manual
    assert "applyAiSuggestion" in manual
    assert "质量提醒" in manual
    assert "批量 AI 建议" in manual
    assert "/ai-suggestions/batch" in manual
    assert "无法应用" in manual
    assert "可视化编辑" in structured_editor
    assert "结构化结果预览" in structured_editor
    assert "value_type" in structured_editor
    assert "renderLatex" in structured_editor
    assert "updateColumnKey" in structured_editor
    assert "结构化专项" in evaluation
    assert "回答级盲测" in evaluation
    assert "/admin/jobs/evaluate-answers" in evaluation
    assert "截图可访问" in evaluation
    assert "complex_structured_tables.jsonl" in evaluation
    assert "质量运营" in overview
    assert "自动质量门禁" in overview
    assert "未解决失败任务" in overview
    assert "/admin/quality/status" in app
    assert "需要 API Key" in app
    assert "验证并进入" in app
    assert "AUTH_REQUIRED_EVENT" in app
    assert "rag-auth-required" in api
    assert Path("OPERATIONS.md").exists()
    assert "apiPut" in api
