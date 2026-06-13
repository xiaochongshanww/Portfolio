"""Report generation — data quality and source health.

The source-health report now uses collection_run records as the primary
data source, falling back to job counts only when no runs exist.
"""

import argparse
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from university_recruitment.source_config import DEFAULT_SOURCES_PATH, SourceConfig, load_sources
from university_recruitment.storage import JobStore, ensure_utc


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
    """Build a source-health report using the most recent collection run.

    Priority: latest collection_run records → fallback to job existence.
    """
    store = JobStore()
    sources = load_sources(config_path, include_disabled=True)
    source_runs = store.get_source_health()  # from latest run
    run_map: dict[str, dict] = {r["source_name"]: r for r in source_runs}

    # Fallback: job counts for sources never seen in a run
    jobs, _ = store.list_jobs(include_expired=True, include_removed=True)
    job_counts = Counter(j.source_name for j in jobs)

    enabled = [s for s in sources if s.enabled]
    disabled = [s for s in sources if not s.enabled]

    lines: list[str] = []
    lines.append("# Source Health Report")
    lines.append("")

    # Summary
    lines.extend(_health_summary(enabled, disabled, run_map, job_counts))
    lines.append("")
    lines.extend(_enabled_health(enabled, run_map, job_counts, store))
    lines.append("")
    lines.extend(_disabled_health(disabled))
    return "\n".join(lines)


def _health_summary(
    enabled: list[SourceConfig],
    disabled: list[SourceConfig],
    run_map: dict[str, dict],
    job_counts: Counter,
) -> list[str]:
    ok_count = 0
    fail_count = 0
    never_run = 0
    for s in enabled:
        r = run_map.get(s.source_name)
        if r is None:
            never_run += 1
        elif r["status"] == "failed":
            fail_count += 1
        else:
            ok_count += 1

    lines = ["## Summary"]
    lines.append(f"- Configured sources: {len(enabled) + len(disabled)}")
    lines.append(f"- Enabled sources: {len(enabled)}")
    lines.append(f"- Disabled sources: {len(disabled)}")
    lines.append(f"- Last run succeeded: {ok_count}")
    lines.append(f"- Last run failed: {fail_count}")
    lines.append(f"- Never run: {never_run}")
    return lines


def _enabled_health(
    enabled: list[SourceConfig],
    run_map: dict[str, dict],
    job_counts: Counter,
    store: JobStore,
) -> list[str]:
    lines = ["## Enabled Source Health"]
    for source in sorted(enabled, key=lambda s: s.source_name):
        name = source.source_name
        run = run_map.get(name)
        active_jobs = store.count_jobs_by_source(name)

        if run is None:
            if active_jobs > 0:
                status = "has_jobs_no_run"
            else:
                status = "never_run"
            lines.append(
                f"- {name} | {source.school} | {source.parser} | "
                f"status={status} | active_jobs={active_jobs} | "
                f"latest_run=N/A | consecutive_failures=0 | next=run_collection"
            )
            continue

        latest_status = run.get("status", "unknown")
        error = run.get("error_message") or ""
        consecutive = store.get_consecutive_failures(name)

        status = latest_status
        if latest_status == "failed" and active_jobs > 0:
            status = "failed_with_existing_jobs"

        lines.append(
            f"- {name} | {source.school} | {source.parser} | "
            f"status={status} | active_jobs={active_jobs} | "
            f"latest_run={latest_status} | consecutive_failures={consecutive} | "
            f"collected={run.get('collected_count', 0)} | "
            f"inserted={run.get('inserted_count', 0)} | "
            f"updated={run.get('updated_count', 0)}"
            + (f" | error={error[:80]}" if error else "")
        )
    return lines


def _disabled_health(disabled: list[SourceConfig]) -> list[str]:
    lines = ["## Disabled Source Classification"]
    if not disabled:
        return lines + ["- None"]

    grouped: dict[str, list] = {}
    for source in disabled:
        grouped.setdefault(_disabled_source_category(source), []).append(source)

    for category in sorted(grouped):
        lines.append(f"- {category}:")
        for source in sorted(grouped[category], key=lambda item: item.source_name):
            lines.append(
                f"  - {source.source_name} | {source.school} | {source.parser} | "
                f"next={_disabled_source_recommendation(source)}"
            )
    return lines


# ── Legacy report sections ──────────────────────────────

def _summary_lines(jobs: list, sources: list) -> list[str]:
    enabled_sources = [s for s in sources if s.enabled]
    disabled_sources = [s for s in sources if not s.enabled]
    schools = {job.school for job in jobs}
    active_jobs = [j for j in jobs if j.status.value == "active"]
    expired_jobs = [j for j in jobs if j.status.value == "expired"]
    removed_jobs = [j for j in jobs if j.status.value == "removed"]
    return [
        "## Summary",
        f"- Jobs: {len(jobs)}",
        f"- Active jobs: {len(active_jobs)}",
        f"- Expired jobs: {len(expired_jobs)}",
        f"- Removed jobs: {len(removed_jobs)}",
        f"- Schools in database: {len(schools)}",
        f"- Configured sources: {len(sources)}",
        f"- Enabled sources: {len(enabled_sources)}",
        f"- Disabled sources: {len(disabled_sources)}",
    ]


def _coverage_lines(jobs: list) -> list[str]:
    total = len(jobs)
    fields = (
        ("description", lambda j: len(j.description) > len(j.position) + 20),
        ("published_at", lambda j: bool(j.published_at)),
        ("deadline", lambda j: bool(j.deadline)),
        ("department", lambda j: bool(j.department)),
        ("discipline", lambda j: bool(j.discipline)),
        ("education_requirement", lambda j: bool(j.education_requirement)),
        ("job_type", lambda j: bool(j.job_type)),
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
    for st, count in by_source_type.most_common():
        lines.append(f"  - {st}: {count}")
    lines.append("- By source name:")
    for sn, count in by_source_name.most_common():
        lines.append(f"  - {sn}: {count}")
    return lines


def _school_lines(jobs: list) -> list[str]:
    by_school = Counter(job.school for job in jobs)
    lines = ["## School Coverage"]
    for school, count in by_school.most_common():
        lines.append(f"- {school}: {count}")
    return lines


def _quality_lines(jobs: list) -> list[str]:
    bad_school_names = sorted({
        j.school for j in jobs
        if "已下线" in j.school or "面议" in j.school or len(j.school) > 40
    })
    duplicate_keys = [
        key for key, count
        in Counter((j.school, j.position) for j in jobs).items()
        if count > 1
    ]
    lines = ["## Quality Checks"]
    lines.append(f"- Suspicious school names: {len(bad_school_names)}")
    for school in bad_school_names[:10]:
        lines.append(f"  - {school}")
    lines.append(f"- Duplicate school+position pairs: {len(duplicate_keys)}")
    for school, position in duplicate_keys[:10]:
        lines.append(f"  - {school} | {position}")
    return lines


def _disabled_source_lines(sources: list) -> list[str]:
    disabled = [s for s in sources if not s.enabled]
    lines = ["## Disabled Sources"]
    if not disabled:
        return lines + ["- None"]
    gz = [s for s in disabled if s.city == "广州" or s.region == "广东" or "广州" in s.source_name]
    hist = [s for s in disabled if s not in gz]
    if gz:
        lines.append("- Guangzhou-related:")
        for s in gz:
            lines.append(f"  - {s.source_name} | {s.parser} | {s.list_url}")
    if hist:
        lines.append("- Other:")
        for s in hist:
            lines.append(f"  - {s.source_name} | {s.parser} | {s.list_url}")
    return lines


def _sample_lines(jobs: list) -> list[str]:
    lines = ["## Samples"]
    for job in jobs[:10]:
        deadline = job.deadline.isoformat() if job.deadline else "N/A"
        lines.append(f"- [{job.source_type.value}] {job.school} | {job.position} | deadline={deadline}")
    return lines


# ── Disabled source helpers ─────────────────────────────

def _disabled_source_category(source) -> str:
    text = f"{source.source_name} {source.list_url}".lower()
    markers = {
        "北京大学": "historical_or_out_of_scope",
        "复旦": "historical_or_out_of_scope",
        "中国科学技术大学": "historical_or_out_of_scope",
        "南京大学": "historical_or_out_of_scope",
    }
    for kw, cat in markers.items():
        if kw in source.source_name:
            return cat
    if "登录" in source.source_name or "login" in text:
        return "requires_login"
    if any(kw in source.source_name for kw in ("动态", "系统")) or \
       any(kw in text for kw in ("recruit", "rszp", "hrzp")):
        return "dynamic_or_system_adapter_needed"
    if "并入" in source.source_name or "统一招聘" in source.source_name:
        return "merged_or_duplicate_management"
    if "高校人才网-广州站" in source.source_name:
        return "aggregator_too_broad"
    return "manual_review"


def _disabled_source_recommendation(source) -> str:
    return {
        "aggregator_too_broad": "keep_disabled_use_narrow_aggregators",
        "dynamic_or_system_adapter_needed": "build_dedicated_adapter",
        "historical_or_out_of_scope": "keep_disabled",
        "manual_review": "inspect_manually",
        "merged_or_duplicate_management": "keep_disabled_use_parent_school_source",
        "requires_login": "keep_disabled_until_public_api",
    }.get(_disabled_source_category(source), "manual_review")


def _percent(count: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{count / total * 100:.1f}%"


def main() -> None:
    parser = argparse.ArgumentParser(description="Report recruitment data quality.")
    parser.add_argument("--config", type=Path, default=DEFAULT_SOURCES_PATH)
    parser.add_argument("--no-samples", action="store_true")
    parser.add_argument("--source-health", action="store_true")
    args = parser.parse_args()
    if args.source_health:
        print(build_source_health_report(config_path=args.config))
        return
    print(build_report(config_path=args.config, include_samples=not args.no_samples))


if __name__ == "__main__":
    main()
