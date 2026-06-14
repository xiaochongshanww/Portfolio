"""Post-processing: enrich existing database jobs with LLM document analysis.

Usage:
    university-recruitment-enrich                    # enrich all jobs
    university-recruitment-enrich --source 中山大学   # enrich jobs from specific school
    university-recruitment-enrich --missing-only      # only jobs with missing fields
    university-recruitment-enrich --dry-run           # preview without writing
"""

import argparse
import json as json_mod
from datetime import date, datetime, timezone

from university_recruitment.llm.extractor import get_llm_extractor
from university_recruitment.models import JobStatus, RecruitmentJob, SKIP_DOC_TYPES, SourceType, QualityStatus
from university_recruitment.quality.validators import (
    build_extraction_warnings_json, calculate_job_quality,
)
from university_recruitment.sources.attachment_parser import prepare_llm_input_text
from university_recruitment.storage import JobStore
from university_recruitment.url_utils import build_position_job_id, content_hash
from university_recruitment.sources.title_cleaner import clean_position_title


def enrich_jobs(
    source_filter: str | None = None,
    missing_only: bool = True,
    dry_run: bool = False,
) -> int:
    store = JobStore()
    jobs, _ = store.list_jobs(
        include_expired=True,
        include_removed=True,
        limit=5000,
        quality_filter=False,
    )

    if source_filter:
        jobs = [j for j in jobs if source_filter in j.school or source_filter in j.source_name]

    if missing_only:
        jobs = [
            j for j in jobs
            if not j.department
            or not j.discipline
            or not j.education_requirement
            or not j.job_type
        ]

    llm = get_llm_extractor()
    if not llm.available:
        print("LLM not available. Set LLM_API_KEY or check config.")
        return 0

    enriched = 0
    for job in jobs:
        analysis_text, used_attachment_text, _ = prepare_llm_input_text(
            body_text=job.description,
            notice_url=str(job.source_url),
        )
        if len(analysis_text) < 60:
            continue

        print(f"  [{job.school}] {job.position[:50]}...", end=" ", flush=True)
        try:
            metadata = {
                "title": job.notice_title or job.position,
                "source_url": str(job.source_url),
                "school": job.school,
                "published_at_hint": str(job.published_at) if job.published_at else "",
            }
            analysis = llm.analyze_document(analysis_text, metadata)
        except Exception as exc:
            print(f"LLM error: {exc}")
            continue

        doc_type = analysis.get("document_type", "unknown")
        skippable = {s.value for s in SKIP_DOC_TYPES}
        if doc_type in skippable:
            print(f"— skipped: {doc_type}")
            continue

        llm_positions = analysis.get("positions", [])
        if not llm_positions:
            print("— no positions")
            continue

        changed = False
        new_split_jobs: list[RecruitmentJob] = []

        # Use first position for backward-compatible single-job enrichment
        for pi, extracted in enumerate(llm_positions):
            pos_id = build_position_job_id(
                str(job.source_url), extracted.get("position_raw", job.position),
                extracted.get("department"),
            )

            dept = extracted.get("department")
            disc = extracted.get("discipline")
            if isinstance(disc, list):
                disc = disc[0] if disc else None

            edu = extracted.get("education_requirement")
            jt = extracted.get("job_type")
            loc = extracted.get("location") or job.location
            np = extracted.get("position_normalized")
            deadline_str = extracted.get("deadline")
            deadline_val = None
            if deadline_str:
                try:
                    deadline_val = date.fromisoformat(deadline_str)
                except (ValueError, TypeError):
                    pass

            evidence = extracted.get("evidence", {})
            evidence_json = json_mod.dumps(evidence, ensure_ascii=False) if evidence else None

            if pi == 0:
                # Only fill missing fields (don't overwrite existing good data)
                if not job.department and dept:
                    job.department = dept
                    changed = True
                if not job.discipline and disc:
                    job.discipline = disc
                    changed = True
                if not job.education_requirement and edu:
                    job.education_requirement = edu
                    changed = True
                if not job.job_type and jt:
                    job.job_type = jt
                    changed = True
                if not job.location or job.location == "未知高校":
                    if loc:
                        job.location = loc
                        changed = True
                if np and len(np) > 3 and np != job.position:
                    job.normalized_position = np
                    changed = True
                if deadline_val and not job.deadline:
                    job.deadline = deadline_val
                    changed = True
                if evidence_json:
                    job.evidence_json = evidence_json
                    changed = True
                if used_attachment_text and analysis_text != job.description:
                    job.description = analysis_text
                    changed = True

                # Always update quality fields when we have LLM analysis
                qscore, qstatus, qwarnings = calculate_job_quality(job, doc_type=doc_type)
                job.quality_score = qscore
                job.quality_status = qstatus
                job.extraction_warnings = build_extraction_warnings_json(qwarnings)
                job.document_type = doc_type
                job.extraction_method = "llm_enrich"
                job.extraction_confidence = analysis.get("confidence")
                changed = True  # quality fields always written when LLM runs

            else:
                # Additional positions from a multi-position notice → create new job records
                position_raw = extracted.get("position_raw", job.position)
                position = clean_position_title(position_raw, job.school)
                job_status = JobStatus.ACTIVE
                if deadline_val and deadline_val < date.today():
                    job_status = JobStatus.EXPIRED

                new_job = RecruitmentJob(
                    id=pos_id,
                    school=job.school,
                    position=position,
                    normalized_position=np,
                    department=dept,
                    discipline=disc,
                    location=loc,
                    longitude=job.longitude,
                    latitude=job.latitude,
                    education_requirement=edu,
                    job_type=jt,
                    deadline=deadline_val,
                    source_type=job.source_type,
                    source_name=job.source_name,
                    source_url=job.source_url,
                    published_at=job.published_at,
                    collected_at=datetime.now(timezone.utc),
                    description=analysis_text,
                    status=job_status,
                    content_hash=content_hash(analysis_text),
                    document_type=doc_type,
                    extraction_method="llm_enrich_split",
                    extraction_confidence=analysis.get("confidence"),
                    notice_title=job.notice_title,
                    notice_url=job.notice_url,
                    evidence_json=evidence_json,
                )
                qscore, qstatus, qwarnings = calculate_job_quality(new_job, doc_type=doc_type)
                new_job.quality_score = qscore
                new_job.quality_status = qstatus
                new_job.extraction_warnings = build_extraction_warnings_json(qwarnings)
                new_split_jobs.append(new_job)

        if changed:
            enriched += 1
            if not dry_run:
                store.update_enriched_fields(job)
            split_count = len(new_split_jobs)
            if split_count:
                if not dry_run:
                    store.upsert_jobs(new_split_jobs)
                print(f"✅ enriched +{split_count} split")
            else:
                print(f"✅ enriched")
        else:
            print("— skipped")

    print(f"\nEnriched {enriched}/{len(jobs)} jobs (dry_run={dry_run})")
    return enriched


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich existing jobs with LLM field extraction.")
    parser.add_argument("--source", help="Filter by school or source name substring.")
    parser.add_argument("--missing-only", action="store_true", default=True,
                        help="Only enrich jobs with missing fields (default: True).")
    parser.add_argument("--all", action="store_true",
                        help="Re-extract all jobs, even those with existing fields.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    enrich_jobs(
        source_filter=args.source,
        missing_only=not args.all,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
