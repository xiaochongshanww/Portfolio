import argparse
from pathlib import Path

from university_recruitment.source_config import DEFAULT_SOURCES_PATH, load_sources
from university_recruitment.sources.factory import build_source_adapter
from university_recruitment.storage import JobStore


def collect_sources(
    config_path: Path = DEFAULT_SOURCES_PATH,
    selected_source: str | None = None,
    include_disabled: bool = False,
    dry_run: bool = False,
    use_llm: bool = False,
) -> int:
    source_configs = load_sources(config_path, include_disabled=include_disabled)
    if selected_source:
        source_configs = [
            source
            for source in source_configs
            if selected_source in source.source_name
            or selected_source in source.school
            or (source.region is not None and selected_source in source.region)
            or (source.city is not None and selected_source in source.city)
        ]

    store = JobStore()
    if not dry_run:
        store.init_db()

    total_jobs = 0
    for source_config in source_configs:
        print(f"Collecting {source_config.source_name} ...")
        try:
            adapter = build_source_adapter(source_config, use_llm=use_llm)
            jobs = adapter.collect()
        except Exception as exc:
            print(f"  failed: {exc}")
            continue

        total_jobs += len(jobs)
        if dry_run:
            print(f"  collected {len(jobs)} jobs")
            for job in jobs[:5]:
                print(f"  - {job.position} | {job.source_url}")
            continue

        written = store.upsert_jobs(jobs)
        print(f"  collected {len(jobs)} jobs, upserted {written}")

    print(f"Finished. total_collected={total_jobs}, dry_run={dry_run}, use_llm={use_llm}")
    return total_jobs


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect university recruitment jobs.")
    parser.add_argument("--config", type=Path, default=DEFAULT_SOURCES_PATH)
    parser.add_argument("--source", help="Filter by school or source name substring.")
    parser.add_argument("--include-disabled", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--use-llm", action="store_true", help="Use DeepSeek LLM to enhance field extraction.")
    args = parser.parse_args()

    collect_sources(
        config_path=args.config,
        selected_source=args.source,
        include_disabled=args.include_disabled,
        dry_run=args.dry_run,
        use_llm=args.use_llm,
    )


if __name__ == "__main__":
    main()
