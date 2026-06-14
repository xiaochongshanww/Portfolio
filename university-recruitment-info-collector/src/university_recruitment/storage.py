import logging
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path


def ensure_utc(value: datetime) -> datetime:
    """Normalize a datetime to UTC-aware.

    Naive datetimes (from old SQLite data) are interpreted as UTC.
    Already-aware datetimes are converted to UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

from university_recruitment.config import DEFAULT_DB_PATH
from university_recruitment.models import (
    CollectionRun,
    CollectionSourceRun,
    JobStatus,
    RecruitmentJob,
    RunStatus,
    SourceType,
)

logger = logging.getLogger(__name__)

CURRENT_SCHEMA_VERSION = 2


def _row_get(row: sqlite3.Row, key: str, default: object = None) -> object:
    """Safely fetch a column from a sqlite3.Row, returning default if absent."""
    return row[key] if key in row.keys() else default


class JobStore:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path))
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    # ── Schema ──────────────────────────────────────────

    def init_db(self) -> None:
        with self.connect() as conn:
            self._create_tables(conn)
            self._run_migrations(conn)

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recruitment_jobs (
                id TEXT PRIMARY KEY,
                school TEXT NOT NULL,
                position TEXT NOT NULL,
                normalized_position TEXT,
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
                source_url TEXT NOT NULL,
                published_at TEXT,
                collected_at TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                first_seen_at TEXT,
                last_seen_at TEXT,
                last_changed_at TEXT,
                content_hash TEXT,
                removed_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS collection_runs (
                id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                selected_source TEXT,
                total_sources INTEGER NOT NULL DEFAULT 0,
                successful_sources INTEGER NOT NULL DEFAULT 0,
                failed_sources INTEGER NOT NULL DEFAULT 0,
                total_collected INTEGER NOT NULL DEFAULT 0,
                total_inserted INTEGER NOT NULL DEFAULT 0,
                total_updated INTEGER NOT NULL DEFAULT 0,
                total_unchanged INTEGER NOT NULL DEFAULT 0,
                total_removed INTEGER NOT NULL DEFAULT 0,
                error_summary TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS collection_source_runs (
                run_id TEXT NOT NULL,
                source_name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                collected_count INTEGER NOT NULL DEFAULT 0,
                inserted_count INTEGER NOT NULL DEFAULT 0,
                updated_count INTEGER NOT NULL DEFAULT 0,
                unchanged_count INTEGER NOT NULL DEFAULT 0,
                removed_count INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                PRIMARY KEY (run_id, source_name),
                FOREIGN KEY (run_id) REFERENCES collection_runs(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """)

    def _run_migrations(self, conn: sqlite3.Connection) -> None:
        current = conn.execute(
            "SELECT MAX(version) FROM schema_version"
        ).fetchone()[0] or 0

        if current < 1:
            self._migrate_v1_add_indexes(conn)
        if current < 2:
            self._migrate_v2_add_lifecycle_columns(conn)

    def _migrate_v1_add_indexes(self, conn: sqlite3.Connection) -> None:
        logger.info("Running migration v1: add indexes")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_source_url ON recruitment_jobs(source_url)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_status ON recruitment_jobs(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_jobs_school ON recruitment_jobs(school)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_source_url_unique ON recruitment_jobs(source_url)"
        )
        conn.execute(
            "INSERT OR REPLACE INTO schema_version (version) VALUES (1)"
        )

    def _migrate_v2_add_lifecycle_columns(self, conn: sqlite3.Connection) -> None:
        logger.info("Running migration v2: lifecycle + quality columns")
        existing = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(recruitment_jobs)").fetchall()
        }
        migrations = {
            "status": "ALTER TABLE recruitment_jobs ADD COLUMN status TEXT NOT NULL DEFAULT 'active'",
            "first_seen_at": "ALTER TABLE recruitment_jobs ADD COLUMN first_seen_at TEXT",
            "last_seen_at": "ALTER TABLE recruitment_jobs ADD COLUMN last_seen_at TEXT",
            "last_changed_at": "ALTER TABLE recruitment_jobs ADD COLUMN last_changed_at TEXT",
            "content_hash": "ALTER TABLE recruitment_jobs ADD COLUMN content_hash TEXT",
            "removed_at": "ALTER TABLE recruitment_jobs ADD COLUMN removed_at TEXT",
            "normalized_position": "ALTER TABLE recruitment_jobs ADD COLUMN normalized_position TEXT",
            "document_type": "ALTER TABLE recruitment_jobs ADD COLUMN document_type TEXT",
            "extraction_method": "ALTER TABLE recruitment_jobs ADD COLUMN extraction_method TEXT",
            "extraction_confidence": "ALTER TABLE recruitment_jobs ADD COLUMN extraction_confidence REAL",
            "quality_score": "ALTER TABLE recruitment_jobs ADD COLUMN quality_score INTEGER",
            "quality_status": "ALTER TABLE recruitment_jobs ADD COLUMN quality_status TEXT NOT NULL DEFAULT 'needs_review'",
            "extraction_warnings": "ALTER TABLE recruitment_jobs ADD COLUMN extraction_warnings TEXT",
            "evidence_json": "ALTER TABLE recruitment_jobs ADD COLUMN evidence_json TEXT",
            "notice_title": "ALTER TABLE recruitment_jobs ADD COLUMN notice_title TEXT",
            "notice_url": "ALTER TABLE recruitment_jobs ADD COLUMN notice_url TEXT",
        }
        for col, stmt in migrations.items():
            if col not in existing:
                conn.execute(stmt)
                logger.info("Added column: %s", col)
        conn.execute(
            "INSERT OR REPLACE INTO schema_version (version) VALUES (2)"
        )

    # ── Job CRUD ────────────────────────────────────────

    def upsert_jobs(self, jobs: list[RecruitmentJob]) -> dict[str, int]:
        """Insert or update jobs. Returns counts of inserted/updated/unchanged.

        Handles: old-ID → new-ID migration, removed→active recovery,
        and field-level change detection (not just content_hash).
        """
        if not jobs:
            return {"inserted": 0, "updated": 0, "unchanged": 0}

        now = datetime.now(timezone.utc).isoformat()
        inserted = 0
        updated = 0
        unchanged = 0

        # Comparable fields beyond content_hash — must be in the SELECT
        _COMPARE_FIELDS = (
            "position", "normalized_position", "department", "discipline",
            "location", "education_requirement", "job_type", "deadline",
            "status", "source_url", "published_at", "content_hash",
        )

        with self.connect() as conn:
            for job in jobs:
                row = self._job_to_row(job)
                # ── Normalize incoming status from deadline ──
                # The model default is always ACTIVE, but actual status
                # must be derived from the deadline field.
                row["status"] = self._resolve_incoming_status(row)

                existing = conn.execute(
                    f"SELECT id, first_seen_at, {', '.join(_COMPARE_FIELDS)} "
                    "FROM recruitment_jobs WHERE id = ?",
                    (row["id"],),
                ).fetchone()

                # Old-ID compat: if not found by new ID, check source_url
                if existing is None:
                    existing = conn.execute(
                        f"SELECT id, first_seen_at, {', '.join(_COMPARE_FIELDS)} "
                        "FROM recruitment_jobs WHERE source_url = ?",
                        (row["source_url"],),
                    ).fetchone()
                    if existing:
                        # Found by URL — migrate old ID to new stable ID
                        conn.execute(
                            "UPDATE recruitment_jobs SET id = ? WHERE id = ?",
                            (row["id"], existing["id"]),
                        )
                        # Re-query with new ID
                        existing = conn.execute(
                            f"SELECT id, first_seen_at, {', '.join(_COMPARE_FIELDS)} "
                            "FROM recruitment_jobs WHERE id = ?",
                            (row["id"],),
                        ).fetchone()

                was_removed = existing and existing["status"] == "removed"

                if existing is None:
                    # Truly new job
                    row["first_seen_at"] = now
                    row["last_seen_at"] = now
                    row["collected_at"] = now
                    conn.execute(self._insert_sql(), row)
                    inserted += 1
                else:
                    # Preserve first_seen_at
                    if existing["first_seen_at"]:
                        row["first_seen_at"] = existing["first_seen_at"]
                    else:
                        row["first_seen_at"] = now

                    # Only removed jobs count as "reactivation"
                    # Status already normalized from deadline above
                    if was_removed:
                        row["removed_at"] = None
                        row["last_seen_at"] = now
                        row["last_changed_at"] = now
                        row["collected_at"] = now
                        conn.execute(self._update_sql(), row)
                        updated += 1
                    elif self._job_fields_changed(existing, row, _COMPARE_FIELDS):
                        # Any field changed — full update
                        # Status is already normalized; deadline extension
                        # from expired→active is naturally detected
                        row["last_seen_at"] = now
                        row["last_changed_at"] = now
                        row["collected_at"] = now
                        conn.execute(self._update_sql(), row)
                        updated += 1
                    else:
                        # No fields changed — just update last_seen
                        conn.execute(
                            "UPDATE recruitment_jobs SET last_seen_at = ?, collected_at = ? WHERE id = ?",
                            (now, now, row["id"]),
                        )
                        unchanged += 1
        return {"inserted": inserted, "updated": updated, "unchanged": unchanged}

    @staticmethod
    def _resolve_incoming_status(row: dict[str, object]) -> str:
        """Derive the correct job status from the deadline field.

        The Pydantic model's default is always ACTIVE, but the real status
        must be computed from the deadline value.  This is the sole source
        of truth for incoming status during upsert.
        """
        deadline = row.get("deadline")
        if deadline and isinstance(deadline, str) and deadline < date.today().isoformat():
            return JobStatus.EXPIRED.value
        return JobStatus.ACTIVE.value

    @staticmethod
    def _job_fields_changed(
        existing: sqlite3.Row, row: dict, field_names: tuple[str, ...]
    ) -> bool:
        """Compare existing DB row with incoming data row for any changes."""
        for field in field_names:
            old_val = existing[field]
            new_val = row.get(field)
            # Normalize None vs empty string
            if old_val is None and (new_val is None or new_val == ""):
                continue
            if (old_val or "") != (new_val or ""):
                return True
        return False

    def _insert_sql(self) -> str:
        return """
            INSERT INTO recruitment_jobs (
                id, school, position, normalized_position, department, discipline, location,
                longitude, latitude, education_requirement, job_type, deadline,
                source_type, source_name, source_url, published_at, collected_at,
                description, status, first_seen_at, last_seen_at, last_changed_at,
                content_hash, removed_at, quality_score, quality_status, extraction_method,
                extraction_confidence, extraction_warnings, document_type, notice_title, notice_url
            ) VALUES (
                :id, :school, :position, :normalized_position, :department, :discipline, :location,
                :longitude, :latitude, :education_requirement, :job_type, :deadline,
                :source_type, :source_name, :source_url, :published_at, :collected_at,
                :description, :status, :first_seen_at, :last_seen_at, :last_changed_at,
                :content_hash, :removed_at, :quality_score, :quality_status, :extraction_method,
                :extraction_confidence, :extraction_warnings, :document_type, :notice_title, :notice_url
            )
        """

    def _update_sql(self) -> str:
        return """
            UPDATE recruitment_jobs SET
                school = :school,
                position = :position,
                normalized_position = :normalized_position,
                department = :department,
                discipline = :discipline,
                location = :location,
                longitude = :longitude,
                latitude = :latitude,
                education_requirement = :education_requirement,
                job_type = :job_type,
                deadline = :deadline,
                source_type = :source_type,
                source_name = :source_name,
                source_url = :source_url,
                published_at = :published_at,
                collected_at = :collected_at,
                description = :description,
                status = :status,
                last_seen_at = :last_seen_at,
                last_changed_at = :last_changed_at,
                content_hash = :content_hash,
                removed_at = :removed_at,
                quality_score = :quality_score,
                quality_status = :quality_status,
                extraction_method = :extraction_method,
                extraction_confidence = :extraction_confidence,
                extraction_warnings = :extraction_warnings,
                document_type = :document_type,
                notice_title = :notice_title,
                notice_url = :notice_url
            WHERE id = :id
        """

    def update_enriched_fields(self, job: RecruitmentJob) -> bool:
        """Update only LLM-enriched fields. Returns True if any field changed.

        Never overwrites: id, position, source_url, first_seen_at, collected_at.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as conn:
            existing = conn.execute(
                """SELECT id, normalized_position, department, discipline,
                          education_requirement, job_type, location, deadline,
                          evidence_json
                   FROM recruitment_jobs WHERE id = ?""",
                (job.id,),
            ).fetchone()
            if not existing:
                return False

            changed = False
            for field in ("normalized_position", "department", "discipline",
                          "education_requirement", "job_type", "location",
                          "evidence_json"):
                old_val = existing[field]
                new_val = getattr(job, field, None)
                if old_val != new_val and new_val is not None:
                    changed = True

            deadline_changed = False
            old_deadline = existing["deadline"]
            new_deadline = job.deadline.isoformat() if job.deadline else None
            if old_deadline != new_deadline and job.deadline is not None:
                deadline_changed = True

            if not changed and not deadline_changed:
                return False

            conn.execute(
                """UPDATE recruitment_jobs
                   SET normalized_position = ?,
                       department = ?,
                       discipline = ?,
                       education_requirement = ?,
                       job_type = ?,
                       location = ?,
                       deadline = ?,
                       last_changed_at = ?,
                       quality_score = ?,
                       quality_status = ?,
                       extraction_warnings = ?,
                       document_type = ?,
                       extraction_method = ?,
                       extraction_confidence = ?,
                       evidence_json = ?
                   WHERE id = ?""",
                (
                    job.normalized_position,
                    job.department,
                    job.discipline,
                    job.education_requirement,
                    job.job_type,
                    job.location,
                    job.deadline.isoformat() if job.deadline else None,
                    now,
                    job.quality_score,
                    job.quality_status if job.quality_status is not None else "needs_review",
                    job.extraction_warnings,
                    job.document_type,
                    job.extraction_method,
                    job.extraction_confidence,
                    job.evidence_json,
                    job.id,
                ),
            )
            return True

    def count_jobs_by_source(self, source_name: str, include_removed: bool = False) -> int:
        """Count non-removed jobs for a given source."""
        with self.connect() as conn:
            if include_removed:
                return conn.execute(
                    "SELECT COUNT(*) FROM recruitment_jobs WHERE source_name = ?",
                    (source_name,),
                ).fetchone()[0]
            return conn.execute(
                "SELECT COUNT(*) FROM recruitment_jobs WHERE source_name = ? AND status != 'removed'",
                (source_name,),
            ).fetchone()[0]

    def list_jobs(
        self,
        status: JobStatus | None = None,
        include_expired: bool = False,
        include_removed: bool = False,
        school: str | None = None,
        source_name: str | None = None,
        location: str | None = None,
        limit: int = 100,
        offset: int = 0,
        quality_filter: bool = True,
    ) -> tuple[list[RecruitmentJob], int]:
        """List jobs with filtering and pagination. Returns (jobs, total_count)."""
        conditions: list[str] = []
        params: dict[str, object] = {}

        if status:
            conditions.append("status = :status")
            params["status"] = status.value
        else:
            active_conditions = ["status = 'active'"]
            if include_expired:
                active_conditions.append("status = 'expired'")
            if include_removed:
                active_conditions.append("status = 'removed'")
            conditions.append(f"({' OR '.join(active_conditions)})")

        if school:
            conditions.append("school = :school")
            params["school"] = school
        if source_name:
            conditions.append("source_name = :source_name")
            params["source_name"] = source_name
        if location:
            conditions.append("location LIKE :location")
            params["location"] = f"%{location}%"

        if quality_filter:
            # Only filter when quality_status has been explicitly set
            # Legacy records have quality_status='needs_review' (migration default)
            # so we show everything except 'hidden'
            conditions.append("(quality_status IS NULL OR quality_status NOT IN ('hidden'))")

        where = " AND ".join(conditions) if conditions else "1=1"

        with self.connect() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM recruitment_jobs WHERE {where}", params
            ).fetchone()[0]

            params["limit"] = min(limit, 200)
            params["offset"] = offset
            rows = conn.execute(
                f"""SELECT * FROM recruitment_jobs
                    WHERE {where}
                    ORDER BY
                        CASE WHEN deadline IS NULL THEN 1 ELSE 0 END,
                        deadline ASC,
                        collected_at DESC
                    LIMIT :limit OFFSET :offset""",
                params,
            ).fetchall()

        return [self._row_to_job(row) for row in rows], total

    def mark_removed(self, run_id: str, source_name: str, active_ids: set[str]) -> int:
        """Mark jobs from a source as removed if not in active_ids.

        Only safe to call when the source collection succeeded.
        """
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as conn:
            if active_ids:
                placeholders = ",".join("?" for _ in active_ids)
                cursor = conn.execute(
                    f"""UPDATE recruitment_jobs
                       SET status = 'removed', removed_at = ?
                       WHERE source_name = ? AND status != 'removed' AND id NOT IN ({placeholders})""",
                    [now, source_name, *active_ids],
                )
            else:
                # No active IDs means all jobs from this source should be marked removed
                cursor = conn.execute(
                    """UPDATE recruitment_jobs
                       SET status = 'removed', removed_at = ?
                       WHERE source_name = ? AND status != 'removed'""",
                    [now, source_name],
                )
            return cursor.rowcount

    def update_expired_status(self) -> int:
        """Mark jobs with past deadlines as expired."""
        today = date.today().isoformat()
        with self.connect() as conn:
            cursor = conn.execute(
                """UPDATE recruitment_jobs
                   SET status = 'expired'
                   WHERE deadline IS NOT NULL AND deadline < ? AND status = 'active'""",
                (today,),
            )
            return cursor.rowcount

    def count(self, status: JobStatus | None = None) -> int:
        with self.connect() as conn:
            if status:
                return conn.execute(
                    "SELECT COUNT(*) FROM recruitment_jobs WHERE status = ?",
                    (status.value,),
                ).fetchone()[0]
            return conn.execute(
                "SELECT COUNT(*) FROM recruitment_jobs"
            ).fetchone()[0]

    # ── Collection Runs ─────────────────────────────────

    def create_run(
        self, run_id: str, selected_source: str | None, total_sources: int
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO collection_runs (id, started_at, status, selected_source, total_sources)
                   VALUES (?, ?, ?, ?, ?)""",
                (run_id, now, RunStatus.RUNNING.value, selected_source, total_sources),
            )

    def finish_run(self, run_id: str, status: RunStatus, **counts: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        fields = ["finished_at = ?", f"status = '{status.value}'"]
        params: list[object] = [now]
        for key in (
            "successful_sources", "failed_sources", "total_collected",
            "total_inserted", "total_updated", "total_unchanged", "total_removed",
            "error_summary",
        ):
            if key in counts:
                fields.append(f"{key} = ?")
                params.append(counts[key])
        params.append(run_id)
        with self.connect() as conn:
            conn.execute(
                f"UPDATE collection_runs SET {', '.join(fields)} WHERE id = ?",
                params,
            )

    def upsert_source_run(self, sr: CollectionSourceRun) -> None:
        with self.connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO collection_source_runs
                   (run_id, source_name, started_at, finished_at, status,
                    collected_count, inserted_count, updated_count,
                    unchanged_count, removed_count, error_message)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    sr.run_id, sr.source_name, sr.started_at.isoformat(),
                    sr.finished_at.isoformat() if sr.finished_at else None,
                    sr.status.value, sr.collected_count, sr.inserted_count,
                    sr.updated_count, sr.unchanged_count, sr.removed_count,
                    sr.error_message,
                ),
            )

    def get_source_health(self) -> list[dict]:
        """Get per-source health — each source's own most recent run."""
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT source_name, status, collected_count, inserted_count,
                          updated_count, error_message, started_at
                   FROM collection_source_runs csr
                   WHERE csr.started_at = (
                       SELECT MAX(inner_csr.started_at)
                       FROM collection_source_runs inner_csr
                       WHERE inner_csr.source_name = csr.source_name
                   )
                   ORDER BY source_name"""
            ).fetchall()
            return [dict(r) for r in rows]

    def get_consecutive_failures(self, source_name: str) -> int:
        """Count consecutive failed runs for a source."""
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT status FROM collection_source_runs
                   WHERE source_name = ?
                   ORDER BY started_at DESC LIMIT 10""",
                (source_name,),
            ).fetchall()
        count = 0
        for r in rows:
            if r["status"] == "failed":
                count += 1
            else:
                break
        return count

    def get_latest_collection_runs(self, limit: int = 20) -> list[CollectionRun]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM collection_runs ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_run(r) for r in rows]

    def get_collection_run(self, run_id: str) -> CollectionRun | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM collection_runs WHERE id = ?", (run_id,)
            ).fetchone()
        return self._row_to_run(row) if row else None

    def get_source_runs_for_run(self, run_id: str) -> list[CollectionSourceRun]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM collection_source_runs WHERE run_id = ? ORDER BY source_name",
                (run_id,),
            ).fetchall()
        return [self._row_to_source_run(r) for r in rows]

    # ── Row conversion ──────────────────────────────────

    @staticmethod
    def _job_to_row(job: RecruitmentJob) -> dict[str, object]:
        return {
            "id": job.id,
            "school": job.school,
            "position": job.position,
            "normalized_position": job.normalized_position,
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
            "status": job.status.value,
            "first_seen_at": job.first_seen_at.isoformat() if job.first_seen_at else None,
            "last_seen_at": job.last_seen_at.isoformat() if job.last_seen_at else None,
            "last_changed_at": job.last_changed_at.isoformat() if job.last_changed_at else None,
            "content_hash": job.content_hash,
            "removed_at": job.removed_at.isoformat() if job.removed_at else None,
            "quality_score": job.quality_score,
            "quality_status": job.quality_status if job.quality_status is not None else "needs_review",
            "extraction_method": job.extraction_method,
            "extraction_confidence": job.extraction_confidence,
            "extraction_warnings": job.extraction_warnings,
            "document_type": job.document_type,
            "notice_title": job.notice_title,
            "notice_url": job.notice_url,
        }

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> RecruitmentJob:
        return RecruitmentJob(
            id=row["id"],
            school=row["school"],
            position=row["position"],
            normalized_position=_row_get(row, "normalized_position"),
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
            collected_at=ensure_utc(datetime.fromisoformat(row["collected_at"])),
            description=row["description"] or "",
            status=JobStatus(row["status"]) if row["status"] else JobStatus.ACTIVE,
            first_seen_at=ensure_utc(datetime.fromisoformat(row["first_seen_at"])) if row["first_seen_at"] else None,
            last_seen_at=ensure_utc(datetime.fromisoformat(row["last_seen_at"])) if row["last_seen_at"] else None,
            last_changed_at=ensure_utc(datetime.fromisoformat(row["last_changed_at"])) if row["last_changed_at"] else None,
            content_hash=row["content_hash"],
            removed_at=ensure_utc(datetime.fromisoformat(row["removed_at"])) if row["removed_at"] else None,
            quality_score=_row_get(row, "quality_score"),
            quality_status=_row_get(row, "quality_status"),
            extraction_method=_row_get(row, "extraction_method"),
            extraction_confidence=_row_get(row, "extraction_confidence"),
            extraction_warnings=_row_get(row, "extraction_warnings"),
            document_type=_row_get(row, "document_type"),
            notice_title=_row_get(row, "notice_title"),
            notice_url=_row_get(row, "notice_url"),
        )

    @staticmethod
    def _row_to_run(row: sqlite3.Row) -> CollectionRun:
        return CollectionRun(
            id=row["id"],
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            status=RunStatus(row["status"]),
            selected_source=row["selected_source"],
            total_sources=row["total_sources"],
            successful_sources=row["successful_sources"],
            failed_sources=row["failed_sources"],
            total_collected=row["total_collected"],
            total_inserted=row["total_inserted"],
            total_updated=row["total_updated"],
            total_unchanged=row["total_unchanged"],
            total_removed=row["total_removed"],
            error_summary=row["error_summary"],
        )

    @staticmethod
    def _row_to_source_run(row: sqlite3.Row) -> CollectionSourceRun:
        return CollectionSourceRun(
            run_id=row["run_id"],
            source_name=row["source_name"],
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            status=RunStatus(row["status"]),
            collected_count=row["collected_count"],
            inserted_count=row["inserted_count"],
            updated_count=row["updated_count"],
            unchanged_count=row["unchanged_count"],
            removed_count=row["removed_count"],
            error_message=row["error_message"],
        )
