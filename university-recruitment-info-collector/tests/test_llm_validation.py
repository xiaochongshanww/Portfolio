"""Tests for LLM extraction models and security (no real API calls)."""

import json
from datetime import date

import pytest


class TestExtractedPosition:
    def test_valid_fields_pass(self):
        from university_recruitment.llm.extractor import ExtractedPosition
        fields = ExtractedPosition(
            position_raw="专任教师",
            position_normalized="专任教师",
            department="计算机学院",
            discipline=["人工智能"],
            education_requirement="博士",
            job_type="教学科研岗",
            location="广州天河区",
            deadline=date(2026, 12, 31),
        )
        assert fields.education_requirement == "博士"
        assert fields.job_type == "教学科研岗"

    def test_invalid_education_rejected(self):
        from university_recruitment.llm.extractor import ExtractedPosition
        fields = ExtractedPosition(position_raw="X", education_requirement="学士学位")
        assert fields.education_requirement is None

    def test_invalid_job_type_rejected(self):
        from university_recruitment.llm.extractor import ExtractedPosition
        fields = ExtractedPosition(position_raw="X", job_type="管理岗")
        assert fields.job_type is None

    def test_department_without_suffix_rejected(self):
        from university_recruitment.llm.extractor import ExtractedPosition
        fields = ExtractedPosition(position_raw="X", department="用人部门")
        assert fields.department is None

    def test_blacklisted_department_rejected(self):
        from university_recruitment.llm.extractor import ExtractedPosition
        for bad in ["用人部门", "招聘单位", "各学院", "学校", "本校"]:
            fields = ExtractedPosition(position_raw="X", department=bad)
            assert fields.department is None, f"Should reject: {bad}"

    def test_valid_department_suffixes_accepted(self):
        from university_recruitment.llm.extractor import ExtractedPosition
        for dept in ["计算机学院", "物理系", "人工智能研究院"]:
            fields = ExtractedPosition(position_raw="X", department=dept)
            assert fields.department == dept

    def test_missing_fields_are_none(self):
        from university_recruitment.llm.extractor import ExtractedPosition
        fields = ExtractedPosition(position_raw="test")
        assert fields.education_requirement is None
        assert fields.discipline == []


class TestDocumentAnalysis:
    def test_valid_doc_type(self):
        from university_recruitment.llm.extractor import DocumentAnalysis
        doc = DocumentAnalysis(document_type="single_position", confidence=0.9)
        assert doc.document_type == "single_position"

    def test_invalid_doc_type_defaults_to_unknown(self):
        from university_recruitment.llm.extractor import DocumentAnalysis
        doc = DocumentAnalysis(document_type="invalid_type")
        assert doc.document_type == "unknown"


class TestLlmParseResponse:
    def test_parse_json_basic(self):
        from university_recruitment.llm.extractor import LlmFieldExtractor
        resp = '{"document_type": "single_position", "confidence": 0.9}'
        result = LlmFieldExtractor._parse_json(LlmFieldExtractor, resp)
        assert result["document_type"] == "single_position"

    def test_parse_json_markdown_wrapped(self):
        from university_recruitment.llm.extractor import LlmFieldExtractor
        resp = '```json\n{"document_type": "multi_position_notice"}\n```'
        result = LlmFieldExtractor._parse_json(LlmFieldExtractor, resp)
        assert result["document_type"] == "multi_position_notice"

    def test_parse_json_non_json_returns_none(self):
        from university_recruitment.llm.extractor import LlmFieldExtractor
        result = LlmFieldExtractor._parse_json(LlmFieldExtractor, "not json")
        assert result is None

    def test_parse_json_array(self):
        from university_recruitment.llm.extractor import LlmFieldExtractor
        resp = '[{"a": 1}, {"b": 2}]'
        result = LlmFieldExtractor._parse_json(LlmFieldExtractor, resp)
        assert isinstance(result, list)
        assert len(result) == 2


class TestConfigSecurity:
    def test_llm_not_available_without_key(self, monkeypatch):
        """When no API key is configured, LLM client is None."""
        import university_recruitment.llm.extractor as ext_mod
        monkeypatch.setattr(ext_mod, "LLM_API_KEY", None)
        ext = ext_mod.LlmFieldExtractor()
        assert ext.client is None
        assert not ext.available


class TestUrlIdStability:
    def test_query_order_independent(self):
        from university_recruitment.url_utils import build_job_id
        u1 = "https://example.edu.cn/jobs?id=1&articleid=2"
        u2 = "https://example.edu.cn/jobs?articleid=2&id=1"
        assert build_job_id(u1) == build_job_id(u2)

    def test_fragment_ignored(self):
        from university_recruitment.url_utils import build_job_id
        assert build_job_id("https://x.com/j#a") == build_job_id("https://x.com/j#b")

    def test_tracking_params_stripped(self):
        from university_recruitment.url_utils import canonicalize_url
        u = "https://x.com/j?utm_source=ga&id=5&utm_medium=email"
        c = canonicalize_url(u)
        assert "utm_source" not in c
        assert "id=5" in c

    def test_different_params_different_id(self):
        from university_recruitment.url_utils import build_job_id
        assert build_job_id("https://x.com/j?id=1") != build_job_id("https://x.com/j?id=2")


class TestNormalizedPosition:
    def test_enrich_does_not_overwrite_position(self):
        from university_recruitment.models import RecruitmentJob, SourceType
        job = RecruitmentJob(
            id="t", school="T", position="原始标题",
            source_type=SourceType.UNIVERSITY_TALENT_SITE,
            source_name="S", source_url="https://x.com/t", description="",
        )
        job.normalized_position = "清洗后标题"
        assert job.position == "原始标题"
