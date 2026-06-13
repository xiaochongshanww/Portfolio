"""Post-processing: enrich existing database jobs with LLM document analysis.

Usage:
    university-recruitment-enrich                    # enrich all jobs
    university-recruitment-enrich --source 中山大学   # enrich jobs from specific school
    university-recruitment-enrich --missing-only      # only jobs with missing fields
    university-recruitment-enrich --dry-run           # preview without writing
"""

import argparse
import json as json_mod
from datetime import date

from university_recruitment.llm.extractor import get_llm_extractor
from university_recruitment.models import SKIP_DOC_TYPES, QualityStatus
from university_recruitment.quality.validators import (
    build_extraction_warnings_json, calculate_job_quality,
)
from university_recruitment.storage import JobStore
from university_recruitment.url_utils import build_position_job_id


def enrich_jobs(
    source_filter: str | None = None,
    missing_only: bool = True,
    dry_run: bool = False,
) -> int:
    store = JobStore()
    jobs, _ = store.list_jobs(include_expired=True, include_removed=True, limit=5000)

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
        if len(job.description) < 60:
            continue

        print(f"  [{job.school}] {job.position[:50]}...", end=" ", flush=True)
        try:
            metadata = {
                "title": job.notice_title or job.position,
                "source_url": str(job.source_url),
                "school": job.school,
                "published_at_hint": str(job.published_at) if job.published_at else "",
            }
            analysis = llm.analyze_document(job.description, metadata)
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

            # For the first/enriched position, update the current job
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
                if deadline_str and not job.deadline:
                    try:
                        job.deadline = date.fromisoformat(deadline_str)
                        changed = True
                    except (ValueError, TypeError):
                        pass

                # Quality score
                if changed and not dry_run:
                    qscore, qstatus, qwarnings = calculate_job_quality(job, doc_type=doc_type)
                    job.quality_score = qscore
                    job.quality_status = qstatus
                    job.extraction_warnings = build_extraction_warnings_json(qwarnings)
                    job.document_type = doc_type
                    job.extraction_method = "llm_enrich"
                    job.extraction_confidence = analysis.get("confidence")

            # For additional positions (multi-position notice), create new jobs
            # This is handled by reprocess command for now

        if changed:
            enriched += 1
            if not dry_run:
                store.update_enriched_fields(job)
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
