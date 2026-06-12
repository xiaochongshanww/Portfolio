import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from university_recruitment.config import DEFAULT_DB_PATH
from university_recruitment.models import RecruitmentJob, SourceType


class JobStore:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def init_db(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS recruitment_jobs (
                    id TEXT PRIMARY KEY,
                    school TEXT NOT NULL,
                    position TEXT NOT NULL,
                    department TEXT,
                    discipline TEXT,
                    location TEXT,
                    longitude REAL,
                    latitude REAL,
                    education_requirement TEXT,
                    job_type TEXT,
                    deadline TEXT,
                    source_type TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_url TEXT NOT NULL UNIQUE,
                    published_at TEXT,
                    collected_at TEXT NOT NULL,
                    description TEXT NOT NULL
                )
                """
            )

    def upsert_jobs(self, jobs: Iterable[RecruitmentJob]) -> int:
        rows = [self._job_to_row(job) for job in jobs]
        if not rows:
            return 0
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO recruitment_jobs (
                    id, school, position, department, discipline, location,
                    longitude, latitude, education_requirement, job_type, deadline,
                    source_type, source_name, source_url, published_at, collected_at,
                    description
                )
                VALUES (
                    :id, :school, :position, :department, :discipline, :location,
                    :longitude, :latitude, :education_requirement, :job_type, :deadline,
                    :source_type, :source_name, :source_url, :published_at, :collected_at,
                    :description
                )
                ON CONFLICT(source_url) DO UPDATE SET
                    school = excluded.school,
                    position = excluded.position,
                    department = excluded.department,
                    discipline = excluded.discipline,
                    location = excluded.location,
                    longitude = excluded.longitude,
                    latitude = excluded.latitude,
                    education_requirement = excluded.education_requirement,
                    job_type = excluded.job_type,
                    deadline = excluded.deadline,
                    source_type = excluded.source_type,
                    source_name = excluded.source_name,
                    published_at = excluded.published_at,
                    collected_at = excluded.collected_at,
                    description = excluded.description
                """,
                rows,
            )
        return len(rows)

    def list_jobs(self, include_expired: bool = False) -> list[RecruitmentJob]:
        query = "SELECT * FROM recruitment_jobs"
        params: tuple[str, ...] = ()
        if not include_expired:
            query += " WHERE deadline IS NULL OR deadline >= ?"
            params = (date.today().isoformat(),)
        query += " ORDER BY deadline IS NULL, deadline ASC, collected_at DESC"
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_job(row) for row in rows]

    @staticmethod
    def _job_to_row(job: RecruitmentJob) -> dict[str, object]:
        return {
            "id": job.id,
            "school": job.school,
            "position": job.position,
            "department": job.department,
            "discipline": job.discipline,
            "location": job.location,
            "longitude": job.longitude,
            "latitude": job.latitude,
            "education_requirement": job.education_requirement,
            "job_type": job.job_type,
            "deadline": job.deadline.isoformat() if job.deadline else None,
            "source_type": job.source_type.value,
            "source_name": job.source_name,
            "source_url": str(job.source_url),
            "published_at": job.published_at.isoformat() if job.published_at else None,
            "collected_at": job.collected_at.isoformat(),
            "description": job.description,
        }

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> RecruitmentJob:
        return RecruitmentJob(
            id=row["id"],
            school=row["school"],
            position=row["position"],
            department=row["department"],
            discipline=row["discipline"],
            location=row["location"],
            longitude=row["longitude"],
            latitude=row["latitude"],
            education_requirement=row["education_requirement"],
            job_type=row["job_type"],
            deadline=date.fromisoformat(row["deadline"]) if row["deadline"] else None,
            source_type=SourceType(row["source_type"]),
            source_name=row["source_name"],
            source_url=row["source_url"],
            published_at=date.fromisoformat(row["published_at"]) if row["published_at"] else None,
            collected_at=datetime.fromisoformat(row["collected_at"]),
            description=row["description"],
        )
