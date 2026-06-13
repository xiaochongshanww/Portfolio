"""Collection runner with concurrency, run tracking, and lifecycle management."""

import argparse
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from university_recruitment.config import (
    BROWSER_CONCURRENCY, COLLECT_MAX_RETRIES, COLLECT_TIMEOUT_SECONDS,
    DETAIL_CONCURRENCY, HTTP_CONCURRENCY,
)
from university_recruitment.models import RunStatus
from university_recruitment.source_config import DEFAULT_SOURCES_PATH, load_sources
from university_recruitment.sources.factory import build_source_adapter
from university_recruitment.storage import JobStore

logger = logging.getLogger(__name__)


def _collect_source(
    source_config,
    run_id: str,
    use_llm: bool,
    dry_run: bool,
) -> dict:
    """Collect a single source. Returns result dict. Never raises."""
    source_name = source_config.source_name
    started = datetime.now(timezone.utc)
    result = {
        "source_name": source_name,
        "started_at": started,
        "status": "failed",
        "collected": 0,
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "removed": 0,
        "error": None,
        "active_ids": set(),
    }

    logger.info("[%s] Collecting %s", run_id[:8], source_name)
    for attempt in range(COLLECT_MAX_RETRIES + 1):
        try:
            adapter = build_source_adapter(source_config, use_llm=use_llm)
            jobs = adapter.collect()
            result["collected"] = len(jobs)
            result["active_ids"] = {j.id for j in jobs}
            break
        except Exception as exc:
            logger.warning(
                "[%s] %s attempt %d failed: %s",
                run_id[:8], source_name, attempt + 1, exc,
            )
            if attempt < COLLECT_MAX_RETRIES:
                wait = 2 ** attempt
                time.sleep(wait)
            else:
                result["error"] = str(exc)[:500]
                result["finished_at"] = datetime.now(timezone.utc)
                return result

    if not dry_run and jobs:
        store = JobStore()
        counts = store.upsert_jobs(jobs)
        result["inserted"] = counts.get("inserted", 0)
        result["updated"] = counts.get("updated", 0)
        result["unchanged"] = counts.get("unchanged", 0)

    # Mark removed: only if collection succeeded (no error)
    if not dry_run and result["error"] is None:
        try:
            store = JobStore()
            removed = store.mark_removed(run_id, source_name, result["active_ids"])
            result["removed"] = removed
        except Exception as exc:
            logger.warning("[%s] mark_removed failed for %s: %s", run_id[:8], source_name, exc)

    result["status"] = "ok" if result["error"] is None else "failed"
    result["finished_at"] = datetime.now(timezone.utc)
    return result


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
            s for s in source_configs
            if selected_source in s.source_name
            or selected_source in s.school
            or (s.region is not None and selected_source in s.region)
            or (s.city is not None and selected_source in s.city)
        ]

    run_id = f"run-{uuid.uuid4().hex[:16]}"
    store = JobStore()
    if not dry_run:
        store.init_db()
        store.create_run(run_id, selected_source, len(source_configs))
        store.update_expired_status()

    # Determine concurrency per source type
    http_sources = [s for s in source_configs if s.parser not in ("browser_list", "hkust_gz_career", "gaoxiaojob_browser")]
    browser_sources = [s for s in source_configs if s.parser in ("browser_list", "hkust_gz_career", "gaoxiaojob_browser")]

    total_collected = 0
    total_inserted = 0
    total_updated = 0
    total_unchanged = 0
    total_removed = 0
    successful = 0
    failed = 0
    errors: list[str] = []

    # HTTP sources with concurrency
    if http_sources:
        http_workers = min(HTTP_CONCURRENCY, len(http_sources))
        with ThreadPoolExecutor(max_workers=http_workers) as pool:
            futures = {
                pool.submit(_collect_source, s, run_id, use_llm, dry_run): s
                for s in http_sources
            }
            for future in as_completed(futures):
                r = future.result()
                total_collected += r["collected"]
                total_inserted += r["inserted"]
                total_updated += r["updated"]
                total_unchanged += r["unchanged"]
                total_removed += r["removed"]
                if r["status"] == "ok":
                    successful += 1
                else:
                    failed += 1
                    if r["error"]:
                        errors.append(f"{r['source_name']}: {r['error'][:120]}")

                # Write source run record
                if not dry_run:
                    from university_recruitment.models import CollectionSourceRun
                    sr = CollectionSourceRun(
                        run_id=run_id,
                        source_name=r["source_name"],
                        started_at=r["started_at"],
                        finished_at=r["finished_at"],
                        status=RunStatus.SUCCESS if r["status"] == "ok" else RunStatus.FAILED,
                        collected_count=r["collected"],
                        inserted_count=r["inserted"],
                        updated_count=r["updated"],
                        unchanged_count=r["unchanged"],
                        removed_count=r["removed"],
                        error_message=r["error"],
                    )
                    store.upsert_source_run(sr)

    # Browser sources serial (Playwright is not thread-safe)
    for s in browser_sources:
        r = _collect_source(s, run_id, use_llm, dry_run)
        total_collected += r["collected"]
        total_inserted += r["inserted"]
        total_updated += r["updated"]
        total_unchanged += r["unchanged"]
        total_removed += r["removed"]
        if r["status"] == "ok":
            successful += 1
        else:
            failed += 1
            if r["error"]:
                errors.append(f"{r['source_name']}: {r['error'][:120]}")

        if not dry_run:
            from university_recruitment.models import CollectionSourceRun
            sr = CollectionSourceRun(
                run_id=run_id,
                source_name=r["source_name"],
                started_at=r["started_at"],
                finished_at=r["finished_at"],
                status=RunStatus.SUCCESS if r["status"] == "ok" else RunStatus.FAILED,
                collected_count=r["collected"],
                inserted_count=r["inserted"],
                updated_count=r["updated"],
                unchanged_count=r["unchanged"],
                removed_count=r["removed"],
                error_message=r["error"],
            )
            store.upsert_source_run(sr)

    # Finalize run
    run_status = RunStatus.SUCCESS
    if failed > 0 and successful > 0:
        run_status = RunStatus.PARTIAL_SUCCESS
    elif successful == 0:
        run_status = RunStatus.FAILED

    if not dry_run:
        store.finish_run(
            run_id,
            run_status,
            successful_sources=successful,
            failed_sources=failed,
            total_collected=total_collected,
            total_inserted=total_inserted,
            total_updated=total_updated,
            total_unchanged=total_unchanged,
            total_removed=total_removed,
        )

    error_summary = "; ".join(errors[:5]) if errors else None
    print(f"Finished. run_id={run_id} total_collected={total_collected} "
          f"inserted={total_inserted} updated={total_updated} "
          f"unchanged={total_unchanged} removed={total_removed} "
          f"status={run_status.value}")
    if error_summary:
        print(f"Errors: {error_summary}")

    return total_collected


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect university recruitment jobs.")
    parser.add_argument("--config", type=Path, default=DEFAULT_SOURCES_PATH)
    parser.add_argument("--source", help="Filter by school or source name substring.")
    parser.add_argument("--include-disabled", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--use-llm", action="store_true")
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
