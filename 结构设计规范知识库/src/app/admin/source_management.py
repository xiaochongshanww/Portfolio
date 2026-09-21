from src.pipeline.source_catalog import SourceCatalogStore

from ..core.config import settings
from .storage import job_store as source_job_store

source_catalog_store = SourceCatalogStore(settings.data_dir)


def reconcile_interrupted_source_revisions(recovered_jobs: list[dict[str, object]]) -> int:
    reconciled = 0
    for recovered in recovered_jobs:
        job_id = str(recovered.get("job_id") or "")
        if not job_id:
            continue
        job = source_job_store.read(job_id)
        if not job or job.get("type") != "source_rebuild":
            continue
        params = job.get("params") if isinstance(job.get("params"), dict) else {}
        revision_id = str(params.get("source_catalog_revision") or "")
        if not revision_id:
            continue
        source_catalog_store.fail_revision(revision_id, "API 进程重启，来源候选构建已中断")
        reconciled += 1
    return reconciled
