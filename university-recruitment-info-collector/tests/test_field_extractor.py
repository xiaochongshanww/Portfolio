"""Tests for field extractor (field_extractor.py)."""

from university_recruitment.sources.field_extractor import (
    extract_address,
    extract_department,
    extract_discipline,
    extract_education_requirement,
    extract_job_type,
)


class TestExtractJobType:
    def test_postdoc(self) -> None:
        assert extract_job_type("博士后招聘", "招聘博士后研究人员") == "博士后"

    def test_teaching_research(self) -> None:
        assert extract_job_type("教学科研岗招聘", "招聘专任教师") == "教学科研岗"

    def test_research_only(self) -> None:
        assert extract_job_type("科研岗招聘", "专职科研人员") == "科研岗"

    def test_counselor(self) -> None:
        assert extract_job_type("辅导员招聘", "招聘辅导员") == "辅导员"

    def test_labeled_match(self) -> None:
        assert extract_job_type("岗位招聘", "岗位类别：博士后") == "博士后"

    def test_no_match(self) -> None:
        assert extract_job_type("招聘会", "欢迎参加招聘会") is None


class TestExtractEducationRequirement:
    def test_doctor(self) -> None:
        assert extract_education_requirement("要求博士研究生学历") == "博士研究生"

    def test_master(self) -> None:
        assert extract_education_requirement("硕士研究生及以上学历") == "硕士研究生及以上"

    def test_bachelor(self) -> None:
        assert extract_education_requirement("本科及以上学历") == "本科及以上"

    def test_first_match(self) -> None:
        text = "博士研究生或硕士研究生均可"
        assert extract_education_requirement(text) == "博士研究生"

    def test_no_requirement(self) -> None:
        assert extract_education_requirement("招聘教师若干") is None


class TestExtractDiscipline:
    def test_standard_label(self) -> None:
        text = "需求学科：计算机科学与技术、人工智能"
        assert extract_discipline(text) is not None
        assert "计算机" in extract_discipline(text)  # type: ignore[operator]

    def test_no_label(self) -> None:
        assert extract_discipline("招聘教师") is None

    def test_bad_value_ignored(self) -> None:
        text = "需求学科：15"
        assert extract_discipline(text) is None


class TestExtractDepartment:
    def test_from_title(self) -> None:
        title = "计算机学院诚聘教学科研岗教师"
        assert extract_department(title, "", "测试大学") == "计算机学院"

    def test_excludes_school_name(self) -> None:
        title = "测试大学计算机学院招聘"
        assert extract_department(title, "", "测试大学") == "计算机学院"

    def test_no_department(self) -> None:
        assert extract_department("招聘教师", "", "测试大学") is None

    def test_department_equals_school(self) -> None:
        assert extract_department("测试大学招聘", "", "测试大学") is None


class TestExtractAddress:
    def test_full_address(self) -> None:
        text = "学校位于广州市番禺区广州大学城外环西路100号"
        assert extract_address(text) is not None
        assert "番禺区" in extract_address(text)  # type: ignore[operator]

    def test_no_address(self) -> None:
        assert extract_address("招聘计算机方向教师") is None

    def test_city_and_road(self) -> None:
        text = "工作地点：广州市天河区五山路381号"
        addr = extract_address(text)
        assert addr is not None
        assert "天河区" in addr
