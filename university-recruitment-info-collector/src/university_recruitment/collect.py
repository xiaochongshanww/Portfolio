"""Collection runner with concurrency, run tracking, and lifecycle management."""

import argparse
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from university_recruitment.config import (
    BROWSER_CONCURRENCY, COLLECT_MAX_RETRIES, COLLECT_TIMEOUT_SECONDS,
    DETAIL_CONCURRENCY, HTTP_CONCURRENCY, LOG_LEVEL,
)
from university_recruitment.models import RunStatus
from university_recruitment.source_config import DEFAULT_SOURCES_PATH, load_sources
from university_recruitment.sources.factory import build_source_adapter
from university_recruitment.storage import JobStore

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    level_name = str(LOG_LEVEL or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        for handler in root.handlers:
            handler.setLevel(level)
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _format_profile_summary(result: dict) -> str:
    profile = result.get("profile_stats")
    if not isinstance(profile, dict):
        profile = {}
    notes = profile.get("notes") or []
    parts = [
        f"elapsed={result.get('elapsed_seconds', 0.0):.2f}s",
        f"collect={result.get('collect_seconds', 0.0):.2f}s",
        f"upsert={result.get('upsert_seconds', 0.0):.2f}s",
        f"mark_removed={result.get('mark_removed_seconds', 0.0):.2f}s",
        f"attempts={result.get('attempt_count', 0)}",
        f"parser={result.get('parser', '-')}",
        f"candidates={profile.get('candidates_seen', 0)}",
        f"list={profile.get('list_requests', 0)}req/{profile.get('list_seconds', 0.0):.2f}s",
        f"detail={profile.get('detail_requests', 0)}req/{profile.get('detail_seconds', 0.0):.2f}s",
        f"detail_ok={profile.get('detail_success', 0)}",
        f"detail_fail={profile.get('detail_failures', 0)}",
        f"limit={profile.get('detail_limit')}",
        f"jobs={result.get('collected', 0)}",
        f"inserted={result.get('inserted', 0)}",
        f"updated={result.get('updated', 0)}",
        f"unchanged={result.get('unchanged', 0)}",
    ]
    if notes:
        parts.append(f"notes={','.join(str(n) for n in notes[:3])}")
    return " ".join(parts)


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
        "parser": source_config.parser,
        "status": "failed",
        "collected": 0,
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "removed": 0,
        "error": None,
        "active_ids": set(),
        "attempt_count": 0,
        "collect_seconds": 0.0,
        "upsert_seconds": 0.0,
        "mark_removed_seconds": 0.0,
        "elapsed_seconds": 0.0,
        "profile_stats": {},
    }

    logger.info("[%s] Collecting %s", run_id[:8], source_name)
    jobs = []
    overall_started_at = perf_counter()
    try:
        for attempt in range(COLLECT_MAX_RETRIES + 1):
            try:
                adapter = build_source_adapter(source_config, use_llm=use_llm)
                result["attempt_count"] = attempt + 1
                collect_started_at = perf_counter()
                jobs = adapter.collect()
                result["collect_seconds"] = perf_counter() - collect_started_at
                result["collected"] = len(jobs)
                result["active_ids"] = {j.id for j in jobs}
                get_profile_stats = getattr(adapter, "get_profile_stats", None)
                if callable(get_profile_stats):
                    profile_stats = get_profile_stats()
                    if isinstance(profile_stats, dict):
                        result["profile_stats"] = profile_stats
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
                    result["error"] = f"{type(exc).__name__}: {exc!s}"[:500]
                    result["finished_at"] = datetime.now(timezone.utc)
                    result["elapsed_seconds"] = perf_counter() - overall_started_at
                    logger.warning("[%s] Source profile %s -> %s", run_id[:8], source_name, _format_profile_summary(result))
                    return result
    except Exception as exc:
        # Outer safety net — catch anything that escapes
        result["error"] = f"{type(exc).__name__}: {exc!s}"[:500]
        result["finished_at"] = datetime.now(timezone.utc)
        result["elapsed_seconds"] = perf_counter() - overall_started_at
        logger.error("[%s] Unexpected error for %s: %s", run_id[:8], source_name, exc)
        logger.warning("[%s] Source profile %s -> %s", run_id[:8], source_name, _format_profile_summary(result))
        return result

    # Empty collection protection — fail closed
    if len(jobs) == 0:
        try:
            store = JobStore()
            previous_count = store.count_jobs_by_source(source_name)
            if previous_count > 0:
                result["error"] = (
                    f"collection returned 0 jobs while source has "
                    f"{previous_count} existing jobs; skip mark_removed"
                )
                result["finished_at"] = datetime.now(timezone.utc)
                logger.warning("[%s] %s: %s", run_id[:8], source_name, result["error"])
                result["elapsed_seconds"] = perf_counter() - overall_started_at
                logger.warning("[%s] Source profile %s -> %s", run_id[:8], source_name, _format_profile_summary(result))
                return result
        except Exception as exc:
            result["error"] = (
                f"empty-result safety check failed: "
                f"{type(exc).__name__}: {exc!s}"
            )[:500]
            result["finished_at"] = datetime.now(timezone.utc)
            logger.error(
                "[%s] empty-result safety check failed for %s: %s",
                run_id[:8], source_name, exc,
            )
            result["elapsed_seconds"] = perf_counter() - overall_started_at
            logger.warning("[%s] Source profile %s -> %s", run_id[:8], source_name, _format_profile_summary(result))
            return result

    # Database upsert — wrapped to prevent exceptions from escaping
    if not dry_run and jobs:
        try:
            store = JobStore()
            upsert_started_at = perf_counter()
            counts = store.upsert_jobs(jobs)
            result["upsert_seconds"] = perf_counter() - upsert_started_at
            result["inserted"] = counts.get("inserted", 0)
            result["updated"] = counts.get("updated", 0)
            result["unchanged"] = counts.get("unchanged", 0)
        except Exception as exc:
            result["error"] = f"db upsert: {type(exc).__name__}: {exc!s}"[:500]
            result["finished_at"] = datetime.now(timezone.utc)
            result["elapsed_seconds"] = perf_counter() - overall_started_at
            logger.error("[%s] upsert failed for %s: %s", run_id[:8], source_name, exc)
            logger.warning("[%s] Source profile %s -> %s", run_id[:8], source_name, _format_profile_summary(result))
            return result

    # Mark removed: only if collection succeeded (no error)
    if not dry_run and result["error"] is None:
        try:
            store = JobStore()
            mark_removed_started_at = perf_counter()
            removed = store.mark_removed(run_id, source_name, result["active_ids"])
            result["mark_removed_seconds"] = perf_counter() - mark_removed_started_at
            result["removed"] = removed
        except Exception as exc:
            result["error"] = (
                f"mark_removed: {type(exc).__name__}: {exc!s}"
            )[:500]
            result["finished_at"] = datetime.now(timezone.utc)
            result["elapsed_seconds"] = perf_counter() - overall_started_at
            logger.error(
                "[%s] mark_removed failed for %s: %s",
                run_id[:8], source_name, exc,
            )
            logger.warning("[%s] Source profile %s -> %s", run_id[:8], source_name, _format_profile_summary(result))
            return result

    result["status"] = "ok" if result["error"] is None else "failed"
    result["finished_at"] = datetime.now(timezone.utc)
    result["elapsed_seconds"] = perf_counter() - overall_started_at
    logger.info("[%s] Source profile %s -> %s", run_id[:8], source_name, _format_profile_summary(result))
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
    run_started_at = perf_counter()
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
                try:
                    r = future.result()
                except Exception as exc:
                    src = futures[future]
                    r = {
                        "source_name": src.source_name,
                        "started_at": datetime.now(timezone.utc),
                        "finished_at": datetime.now(timezone.utc),
                        "status": "failed",
                        "collected": 0, "inserted": 0, "updated": 0,
                        "unchanged": 0, "removed": 0,
                        "error": f"unhandled: {type(exc).__name__}: {exc!s}"[:500],
                        "active_ids": set(),
                    }
                    logger.error("[%s] Unhandled future error for %s: %s",
                                 run_id[:8], src.source_name, exc)
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

    error_summary = "; ".join(errors[:5]) if errors else None

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
            error_summary=error_summary,
        )

    logger.info(
        "[%s] Collection run summary: elapsed=%.2fs successful=%d failed=%d collected=%d inserted=%d updated=%d unchanged=%d removed=%d http_sources=%d browser_sources=%d",
        run_id[:8],
        perf_counter() - run_started_at,
        successful,
        failed,
        total_collected,
        total_inserted,
        total_updated,
        total_unchanged,
        total_removed,
        len(http_sources),
        len(browser_sources),
    )

    print(f"Finished. run_id={run_id} total_collected={total_collected} "
          f"inserted={total_inserted} updated={total_updated} "
          f"unchanged={total_unchanged} removed={total_removed} "
          f"status={run_status.value}")
    if error_summary:
        print(f"Errors: {error_summary}")

    return total_collected


def main() -> None:
    _setup_logging()
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
