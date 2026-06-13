import argparse
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from university_recruitment.source_config import DEFAULT_SOURCES_PATH, load_sources
from university_recruitment.storage import JobStore


def build_report(config_path: Path = DEFAULT_SOURCES_PATH, include_samples: bool = True) -> str:
    jobs, _ = JobStore().list_jobs(include_expired=True, include_removed=True)
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


def build_source_health_report(config_path: Path = DEFAULT_SOURCES_PATH) -> str:
    jobs, _ = JobStore().list_jobs(include_expired=True, include_removed=True)
    sources = load_sources(config_path, include_disabled=True)
    jobs_by_source = _jobs_by_source_name(jobs)

    lines: list[str] = []
    lines.append("# Source Health Report")
    lines.append("")
    lines.extend(_source_health_summary_lines(sources, jobs_by_source))
    lines.append("")
    lines.extend(_enabled_source_health_lines(sources, jobs_by_source))
    lines.append("")
    lines.extend(_disabled_source_health_lines(sources))
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


def _jobs_by_source_name(jobs: list) -> dict[str, list]:
    jobs_by_source: dict[str, list] = {}
    for job in jobs:
        jobs_by_source.setdefault(job.source_name, []).append(job)
    return jobs_by_source


def _source_health_summary_lines(sources: list, jobs_by_source: dict[str, list]) -> list[str]:
    enabled_sources = [source for source in sources if source.enabled]
    disabled_sources = [source for source in sources if not source.enabled]
    enabled_with_jobs = [
        source for source in enabled_sources if len(jobs_by_source.get(source.source_name, [])) > 0
    ]
    enabled_without_jobs = [
        source for source in enabled_sources if len(jobs_by_source.get(source.source_name, [])) == 0
    ]
    disabled_by_category = Counter(_disabled_source_category(source) for source in disabled_sources)
    lines = ["## Summary"]
    lines.append(f"- Configured sources: {len(sources)}")
    lines.append(f"- Enabled sources: {len(enabled_sources)}")
    lines.append(f"- Enabled sources with jobs: {len(enabled_with_jobs)}")
    lines.append(f"- Enabled sources without jobs: {len(enabled_without_jobs)}")
    lines.append(f"- Disabled sources: {len(disabled_sources)}")
    lines.append("- Disabled by category:")
    for category, count in disabled_by_category.most_common():
        lines.append(f"  - {category}: {count}")
    return lines


def _enabled_source_health_lines(sources: list, jobs_by_source: dict[str, list]) -> list[str]:
    lines = ["## Enabled Source Health"]
    for source in sorted((source for source in sources if source.enabled), key=lambda item: item.source_name):
        source_jobs = jobs_by_source.get(source.source_name, [])
        collected_at = _latest_collected_at(source_jobs)
        status = "ok" if source_jobs else "no_jobs"
        recommendation = _enabled_source_recommendation(source, source_jobs)
        lines.append(
            "- "
            f"{source.source_name} | {source.school} | {source.parser} | "
            f"status={status} | jobs={len(source_jobs)} | latest={collected_at} | "
            f"next={recommendation}"
        )
    return lines


def _disabled_source_health_lines(sources: list) -> list[str]:
    disabled_sources = [source for source in sources if not source.enabled]
    lines = ["## Disabled Source Classification"]
    if not disabled_sources:
        return lines + ["- None"]

    grouped: dict[str, list] = {}
    for source in disabled_sources:
        grouped.setdefault(_disabled_source_category(source), []).append(source)

    for category in sorted(grouped):
        lines.append(f"- {category}:")
        for source in sorted(grouped[category], key=lambda item: item.source_name):
            lines.append(
                f"  - {source.source_name} | {source.school} | {source.parser} | "
                f"next={_disabled_source_recommendation(source)} | {source.list_url}"
            )
    return lines


def _latest_collected_at(jobs: list) -> str:
    if not jobs:
        return "N/A"
    latest = max(job.collected_at for job in jobs)
    if isinstance(latest, datetime):
        return latest.isoformat(timespec="seconds")
    return str(latest)


def _enabled_source_recommendation(source, jobs: list) -> str:
    if not jobs:
        if source.parser == "gaoxiaojob_browser":
            return "verify_browser_source_or_disable"
        return "verify_entry_or_add_adapter"
    if source.parser == "gaoxiaojob_browser":
        return "monitor_duplicates_and_offline_jobs"
    return "monitor"


def _disabled_source_category(source) -> str:
    text = f"{source.source_name} {source.list_url}".lower()
    if "北京大学" in source.source_name or "复旦" in source.source_name or "中国科学技术大学" in source.source_name or "南京大学" in source.source_name:
        return "historical_or_out_of_scope"
    if "登录" in source.source_name or "login" in text:
        return "requires_login"
    if "动态" in source.source_name or "系统" in source.source_name or "recruit" in text or "rszp" in text or "hrzp" in text:
        return "dynamic_or_system_adapter_needed"
    if "403" in source.source_name or "403" in text:
        return "blocked_or_forbidden"
    if "静态采集为空" in source.source_name or "无静态" in source.source_name:
        return "no_static_list"
    if "并入" in source.source_name or "统一招聘" in source.source_name:
        return "merged_or_duplicate_management"
    if "高校人才网-广州站" in source.source_name:
        return "aggregator_too_broad"
    return "manual_review"


def _disabled_source_recommendation(source) -> str:
    category = _disabled_source_category(source)
    recommendations = {
        "aggregator_too_broad": "keep_disabled_use_narrow_aggregators",
        "blocked_or_forbidden": "retry_with_browser_or_headers",
        "dynamic_or_system_adapter_needed": "build_dedicated_adapter",
        "historical_or_out_of_scope": "keep_disabled",
        "manual_review": "inspect_manually",
        "merged_or_duplicate_management": "keep_disabled_use_parent_school_source",
        "no_static_list": "build_browser_or_api_adapter",
        "requires_login": "keep_disabled_until_credentials_or_public_api",
    }
    return recommendations[category]


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
    parser.add_argument("--source-health", action="store_true", help="Report source-level health and next actions.")
    args = parser.parse_args()
    if args.source_health:
        print(build_source_health_report(config_path=args.config))
        return
    print(build_report(config_path=args.config, include_samples=not args.no_samples))


if __name__ == "__main__":
    main()
