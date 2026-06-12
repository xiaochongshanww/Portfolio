import argparse
from collections import Counter
from datetime import date
from pathlib import Path

from university_recruitment.source_config import DEFAULT_SOURCES_PATH, load_sources
from university_recruitment.storage import JobStore


def build_report(config_path: Path = DEFAULT_SOURCES_PATH, include_samples: bool = True) -> str:
    jobs = JobStore().list_jobs(include_expired=True)
    sources = load_sources(config_path, include_disabled=True)

    lines: list[str] = []
    lines.append("# University Recruitment Data Report")
    lines.append("")
    lines.extend(_summary_lines(jobs, sources))
    lines.append("")
    lines.extend(_coverage_lines(jobs))
    lines.append("")
    lines.extend(_source_lines(jobs))
    lines.append("")
    lines.extend(_school_lines(jobs))
    lines.append("")
    lines.extend(_quality_lines(jobs))
    lines.append("")
    lines.extend(_disabled_source_lines(sources))
    if include_samples:
        lines.append("")
        lines.extend(_sample_lines(jobs))
    return "\n".join(lines)


def _summary_lines(jobs: list, sources: list) -> list[str]:
    enabled_sources = [source for source in sources if source.enabled]
    disabled_sources = [source for source in sources if not source.enabled]
    schools = {job.school for job in jobs}
    active_jobs = [job for job in jobs if not job.deadline or job.deadline >= date.today()]
    expired_jobs = [job for job in jobs if job.deadline and job.deadline < date.today()]
    return [
        "## Summary",
        f"- Jobs: {len(jobs)}",
        f"- Active or undated jobs: {len(active_jobs)}",
        f"- Expired jobs: {len(expired_jobs)}",
        f"- Schools in database: {len(schools)}",
        f"- Configured sources: {len(sources)}",
        f"- Enabled sources: {len(enabled_sources)}",
        f"- Disabled sources: {len(disabled_sources)}",
    ]


def _coverage_lines(jobs: list) -> list[str]:
    total = len(jobs)
    fields = (
        ("description", lambda job: len(job.description) > len(job.position) + 20),
        ("published_at", lambda job: bool(job.published_at)),
        ("deadline", lambda job: bool(job.deadline)),
        ("department", lambda job: bool(job.department)),
        ("discipline", lambda job: bool(job.discipline)),
        ("education_requirement", lambda job: bool(job.education_requirement)),
        ("job_type", lambda job: bool(job.job_type)),
    )
    lines = ["## Field Coverage"]
    for name, predicate in fields:
        count = sum(1 for job in jobs if predicate(job))
        lines.append(f"- {name}: {count}/{total} ({_percent(count, total)})")
    return lines


def _source_lines(jobs: list) -> list[str]:
    by_source_type = Counter(job.source_type.value for job in jobs)
    by_source_name = Counter(job.source_name for job in jobs)
    lines = ["## Source Distribution"]
    lines.append("- By source type:")
    for source_type, count in by_source_type.most_common():
        lines.append(f"  - {source_type}: {count}")
    lines.append("- By source name:")
    for source_name, count in by_source_name.most_common():
        lines.append(f"  - {source_name}: {count}")
    return lines


def _school_lines(jobs: list) -> list[str]:
    by_school = Counter(job.school for job in jobs)
    lines = ["## School Coverage"]
    for school, count in by_school.most_common():
        lines.append(f"- {school}: {count}")
    return lines


def _quality_lines(jobs: list) -> list[str]:
    bad_school_names = sorted(
        {
            job.school
            for job in jobs
            if "已下线" in job.school or "面议" in job.school or len(job.school) > 40
        }
    )
    duplicate_keys = [
        key
        for key, count in Counter((job.school, job.position) for job in jobs).items()
        if count > 1
    ]
    undated_jobs = [job for job in jobs if not job.deadline]
    expired_jobs = [job for job in jobs if job.deadline and job.deadline < date.today()]

    lines = ["## Quality Checks"]
    lines.append(f"- Suspicious school names: {len(bad_school_names)}")
    for school in bad_school_names[:10]:
        lines.append(f"  - {school}")
    lines.append(f"- Duplicate school+position pairs: {len(duplicate_keys)}")
    for school, position in duplicate_keys[:10]:
        lines.append(f"  - {school} | {position}")
    lines.append(f"- Jobs without deadline: {len(undated_jobs)}")
    lines.append(f"- Expired jobs: {len(expired_jobs)}")
    return lines


def _disabled_source_lines(sources: list) -> list[str]:
    disabled_sources = [source for source in sources if not source.enabled]
    lines = ["## Disabled Sources"]
    if not disabled_sources:
        return lines + ["- None"]

    guangzhou_sources = [
        source
        for source in disabled_sources
        if source.city == "广州" or source.region == "广东" or "广州" in source.source_name
    ]
    historical_sources = [source for source in disabled_sources if source not in guangzhou_sources]

    if guangzhou_sources:
        lines.append("- Guangzhou-related:")
        for source in guangzhou_sources:
            lines.append(f"  - {source.source_name} | {source.parser} | {source.list_url}")
    if historical_sources:
        lines.append("- Historical or out-of-scope:")
        for source in historical_sources:
            lines.append(f"  - {source.source_name} | {source.parser} | {source.list_url}")
    return lines


def _sample_lines(jobs: list) -> list[str]:
    lines = ["## Samples"]
    for job in jobs[:10]:
        deadline = job.deadline.isoformat() if job.deadline else "N/A"
        lines.append(f"- [{job.source_type.value}] {job.school} | {job.position} | deadline={deadline}")
    return lines


def _percent(count: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{count / total * 100:.1f}%"


def main() -> None:
    parser = argparse.ArgumentParser(description="Report recruitment data quality.")
    parser.add_argument("--config", type=Path, default=DEFAULT_SOURCES_PATH)
    parser.add_argument("--no-samples", action="store_true")
    args = parser.parse_args()
    print(build_report(config_path=args.config, include_samples=not args.no_samples))


if __name__ == "__main__":
    main()
