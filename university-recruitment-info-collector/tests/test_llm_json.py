"""Tests for LLM JSON response parsing edge cases."""
import unittest

from university_recruitment.llm.extractor import LlmFieldExtractor


class TestParseJson(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = LlmFieldExtractor.__new__(LlmFieldExtractor)

    def test_valid_json_with_smart_quotes_in_values(self) -> None:
        content = (
            '{\n'
            '  "reason": "文档明确招聘“专任教师”岗位，要求博士学历。",\n'
            '  "confidence": 0.9\n'
            '}'
        )
        result = self.parser._parse_json(content)
        self.assertIsNotNone(result)
        self.assertIn("专任教师", result["reason"])
        self.assertEqual(result["confidence"], 0.9)

    def test_smart_quotes_as_delimiters(self) -> None:
        content = "{\n  “document_type”: “single_position”,\n  “confidence”: 0.8\n}"
        result = self.parser._parse_json(content)
        self.assertIsNotNone(result)
        self.assertEqual(result["document_type"], "single_position")

    def test_markdown_code_fence(self) -> None:
        content = '```json\n{"document_type": "unknown", "confidence": 0.5}\n```'
        result = self.parser._parse_json(content)
        self.assertIsNotNone(result)
        self.assertEqual(result["document_type"], "unknown")

    def test_truncated_json_repaired(self) -> None:
        content = '{"document_type": "single_position", "position_count_estimate": 1, "confidence": 0.'
        result = self.parser._parse_json(content)
        self.assertIsNotNone(result)
        self.assertEqual(result["document_type"], "single_position")


if __name__ == "__main__":
    unittest.main()
