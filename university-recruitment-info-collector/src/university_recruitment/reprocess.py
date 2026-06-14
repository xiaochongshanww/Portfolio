"""Reprocess existing database jobs through the LLM analysis pipeline.

Usage:
    university-recruitment-reprocess --all
    university-recruitment-reprocess --source 中山大学
    university-recruitment-reprocess --only-low-quality --dry-run
    university-recruitment-reprocess --limit 50 --export-before
"""

import argparse
import csv
import json
from datetime import datetime, timezone

from university_recruitment.llm.extractor import get_llm_extractor
from university_recruitment.models import JobStatus, QualityStatus, SKIP_DOC_TYPES
from university_recruitment.quality.validators import (
    build_extraction_warnings_json, calculate_job_quality,
)
from university_recruitment.sources.attachment_parser import (
    prepare_llm_input_text,
)
from university_recruitment.storage import JobStore


def reprocess_jobs(
    source_filter: str | None = None,
    only_low_quality: bool = False,
    only_notice_like: bool = False,
    dry_run: bool = False,
    limit: int = 5000,
    export_before: bool = False,
) -> dict:
    store = JobStore()
    # Paginate to bypass the per-call cap in list_jobs
    all_jobs: list = []
    offset = 0
    page_size = 200
    while True:
        page, total = store.list_jobs(
            include_expired=True, include_removed=True,
            limit=page_size, offset=offset, quality_filter=False,
        )
        all_jobs.extend(page)
        offset += len(page)
        if offset >= total or len(page) < page_size or (limit and offset >= limit):
            break
    if limit:
        all_jobs = all_jobs[:limit]

    if source_filter:
        all_jobs = [j for j in all_jobs if source_filter in j.school or source_filter in j.source_name]
    if only_low_quality:
        all_jobs = [j for j in all_jobs if j.quality_status != QualityStatus.NORMAL.value]
    if only_notice_like:
        from university_recruitment.quality.validators import looks_like_specific_position
        all_jobs = [j for j in all_jobs if not looks_like_specific_position(j.position)[0]]

    if export_before:
        _export_to_csv(all_jobs, "before_reprocess.csv")

    llm = get_llm_extractor()
    if not llm.available:
        print("LLM not available")
        return {"source_count": len(all_jobs), "reprocessed": 0, "error": "LLM not available"}

    stats = {
        "source_count": len(all_jobs),
        "reprocessed": 0,
        "hidden": 0,
        "needs_review": 0,
        "normal": 0,
        "llm_failed": 0,
        "multi_split": 0,
        "warnings": [],
    }

    for job in all_jobs:
        analysis_text, used_attachment_text, aug_warnings = prepare_llm_input_text(
            body_text=job.description or "",
            notice_url=str(job.source_url),
        )
        if len((analysis_text or "").strip()) < 60:
            if aug_warnings:
                stats.get("warnings", []).append(
                    f"skipped {job.id}: description too short and attachment text unavailable"
                )
                for warning in aug_warnings:
                    stats.get("warnings", []).append(f"{job.id}: {warning}")
            else:
                stats.get("warnings", []).append(f"skipped {job.id}: description too short")
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
            doc_type = analysis.get("document_type", "unknown")
            llm_positions = analysis.get("positions", [])

            if not analysis.get("review_accepted", True) and not llm_positions:
                stats["llm_failed"] += 1
                print("❌ no positions and review rejected")
                continue
            elif not analysis.get("review_accepted", True):
                # Stage C rejected, but we have Stage B positions — still use them
                print(f"⚠️ Stage B positions ({len(llm_positions)}) used despite Stage C rejection")

            if doc_type in {s.value for s in SKIP_DOC_TYPES}:
                stats["hidden"] += 1
                print(f"skipped: {doc_type}")
                continue

            if len(llm_positions) > 1:
                stats["multi_split"] += 1

            if dry_run:
                print(f"analyzed: {len(llm_positions)} positions, type={doc_type}")
                continue

            # Build new jobs
            new_jobs = []
            for extracted in llm_positions:
                from university_recruitment.url_utils import build_position_job_id
                pos_id = build_position_job_id(
                    str(job.source_url), extracted.get("position_raw", job.position),
                    extracted.get("department"),
                )
                dept = extracted.get("department")
                disc = extracted.get("discipline")
                if isinstance(disc, list):
                    disc = disc[0] if disc else None

                deadline_str = extracted.get("deadline")
                deadline = job.deadline
                if deadline_str:
                    try:
                        deadline = datetime.fromisoformat(deadline_str).date()
                    except (ValueError, TypeError):
                        pass  # Keep original deadline if LLM returns non-date string

                new_jobs.append(RecruitmentJob(
                    id=pos_id, school=job.school,
                    position=extracted.get("position_raw", job.position),
                    normalized_position=extracted.get("position_normalized"),
                    department=dept, discipline=disc,
                    location=extracted.get("location") or job.location,
                    education_requirement=extracted.get("education_requirement"),
                    job_type=extracted.get("job_type"),
                    deadline=deadline,
                    source_type=job.source_type,
                    source_name=job.source_name,
                    source_url=job.source_url,
                    published_at=job.published_at,
                    description=analysis_text,
                    status=JobStatus.EXPIRED if deadline and deadline < datetime.now(timezone.utc).date() else JobStatus.ACTIVE,
                    document_type=doc_type,
                    extraction_method=("llm_reprocess_attachment" if used_attachment_text else "llm_reprocess"),
                    extraction_confidence=analysis.get("confidence"),
                    content_hash=job.content_hash,
                    notice_title=job.notice_title or job.position,
                    notice_url=str(job.source_url),
                ))

                qscore, qstatus, qwarnings = calculate_job_quality(new_jobs[-1], doc_type=doc_type)
                new_jobs[-1].quality_score = qscore
                new_jobs[-1].quality_status = qstatus
                new_jobs[-1].extraction_warnings = build_extraction_warnings_json(qwarnings)

                if qstatus == QualityStatus.NORMAL.value:
                    stats["normal"] += 1
                elif qstatus == QualityStatus.HIDDEN.value:
                    stats["hidden"] += 1
                else:
                    stats["needs_review"] += 1

            # Write with upsert
            store.upsert_jobs(new_jobs)
            stats["reprocessed"] += len(new_jobs)
            if new_jobs:
                qstatus = new_jobs[-1].quality_status
                qscore = new_jobs[-1].quality_score
                print(f"✅ {len(new_jobs)} positions, quality={qstatus}, score={qscore}")
            else:
                stats["llm_failed"] += 1
                print("❌ no positions extracted")

        except Exception as exc:
            stats["llm_failed"] += 1
            print(f"❌ error: {exc}")

    print(f"\nReprocess complete: {stats}")
    return stats


def _export_to_csv(jobs, filename: str) -> None:
    import csv
    from pathlib import Path
    path = Path(f"data/exports/{filename}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        if not jobs:
            return
        w = csv.writer(f)
        w.writerow([
            "id", "school", "position", "normalized_position", "department",
            "discipline", "education_requirement", "job_type", "location",
            "deadline", "published_at", "status", "quality_score",
            "quality_status", "document_type", "extraction_method",
            "extraction_confidence", "extraction_warnings",
            "notice_title", "notice_url", "source_url",
        ])
        for j in jobs:
            w.writerow([
                j.id, j.school, j.position, j.normalized_position or "",
                j.department or "", j.discipline or "", j.education_requirement or "",
                j.job_type or "", j.location or "", j.deadline or "",
                j.published_at or "", j.status.value,
                j.quality_score or "", j.quality_status or "",
                j.document_type or "", j.extraction_method or "",
                j.extraction_confidence or "", j.extraction_warnings or "",
                j.notice_title or "", j.notice_url or "",
                str(j.source_url),
            ])
    print(f"Exported {len(jobs)} jobs to {filename}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reprocess existing jobs with LLM pipeline.")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--source", help="Filter by school or source name.")
    parser.add_argument("--only-low-quality", action="store_true")
    parser.add_argument("--only-notice-like", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=510)
    parser.add_argument("--export-before", action="store_true")
    args = parser.parse_args()
    reprocess_jobs(
        source_filter=args.source,
        only_low_quality=args.only_low_quality,
        only_notice_like=args.only_notice_like,
        dry_run=args.dry_run,
        limit=args.limit,
        export_before=args.export_before,
    )


if __name__ == "__main__":
    # Avoid circular import
    from university_recruitment.models import RecruitmentJob
    main()
