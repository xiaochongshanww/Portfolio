from datetime import date, datetime

from university_recruitment.models import RecruitmentJob, SourceType
from university_recruitment.storage import JobStore


SAMPLE_JOBS = [
    RecruitmentJob(
        id="sample-tsinghua-ai-001",
        school="示例大学",
        department="计算机学院",
        position="人工智能方向青年教师",
        discipline="计算机科学与技术、人工智能、机器学习",
        location="北京",
        education_requirement="博士",
        job_type="教学科研岗",
        deadline=date(2026, 12, 31),
        source_type=SourceType.UNIVERSITY_TALENT_SITE,
        source_name="示例大学人才招聘网",
        source_url="https://example.edu.cn/jobs/ai-faculty",
        published_at=date(2026, 6, 1),
        collected_at=datetime.utcnow(),
        description="招聘人工智能、机器学习、数据挖掘方向青年教师，要求博士学历，有高水平论文优先。",
    ),
    RecruitmentJob(
        id="sample-hangzhou-material-001",
        school="东部示例理工大学",
        department="材料科学与工程学院",
        position="材料方向博士后",
        discipline="材料科学、先进制造、新能源材料",
        location="杭州",
        education_requirement="博士",
        job_type="博士后",
        deadline=date(2026, 9, 30),
        source_type=SourceType.UNIVERSITY_TALENT_SITE,
        source_name="东部示例理工大学人事处",
        source_url="https://example.edu.cn/jobs/material-postdoc",
        published_at=date(2026, 5, 20),
        collected_at=datetime.utcnow(),
        description="面向新能源材料、先进制造方向招聘博士后，支持科研启动经费。",
    ),
]


def main() -> None:
    store = JobStore()
    store.init_db()
    count = store.upsert_jobs(SAMPLE_JOBS)
    print(f"Seeded {count} recruitment jobs.")


if __name__ == "__main__":
    main()
