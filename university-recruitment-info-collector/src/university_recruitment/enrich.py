"""Post-processing: enrich existing database jobs with LLM field extraction.

Usage:
    university-recruitment-enrich                    # enrich all jobs
    university-recruitment-enrich --source 中山大学   # enrich jobs from specific school
    university-recruitment-enrich --missing-only      # only jobs with missing fields
    university-recruitment-enrich --dry-run           # preview without writing
"""

import argparse
from datetime import date

from university_recruitment.llm.extractor import get_llm_extractor
from university_recruitment.storage import JobStore


def enrich_jobs(
    source_filter: str | None = None,
    missing_only: bool = True,
    dry_run: bool = False,
) -> int:
    store = JobStore()
    jobs = store.list_jobs(include_expired=True)

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
        # Skip jobs without enough content for meaningful LLM extraction
        if len(job.description) < 60:
            continue

        print(f"  [{job.school}] {job.position[:50]}...", end=" ", flush=True)
        try:
            result = llm.extract(job.description)
        except Exception as exc:
            print(f"LLM error: {exc}")
            continue

        changed = False

        # Only fill in missing fields (don't overwrite existing good data)
        if not job.department and result.get("department"):
            job.department = result["department"]
            changed = True
        if not job.discipline and result.get("discipline"):
            job.discipline = result["discipline"]
            changed = True
        if not job.education_requirement and result.get("education_requirement"):
            job.education_requirement = result["education_requirement"]
            changed = True
        if not job.job_type and result.get("job_type"):
            job.job_type = result["job_type"]
            changed = True
        if not job.location or job.location == "未知高校":
            if result.get("location"):
                job.location = result["location"]
                changed = True

        # Position: always prefer LLM cleaned version if it looks better
        llm_position = result.get("clean_position")
        if llm_position and len(llm_position) > 3:
            job.position = llm_position
            changed = True

        # Deadline: LLM can parse Chinese date formats
        llm_deadline = result.get("deadline")
        if llm_deadline and not job.deadline:
            try:
                job.deadline = date.fromisoformat(llm_deadline)
                changed = True
            except (ValueError, TypeError):
                pass

        if changed:
            enriched += 1
            if not dry_run:
                store.upsert_jobs([job])
            print("✅ enriched")
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
