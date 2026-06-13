import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from university_recruitment.config import (
    API_ACCESS_TOKEN, APP_ENV, APP_HOST, APP_PORT,
    CORS_ALLOWED_ORIGINS, MAX_REQUEST_BODY_BYTES,
    RATE_LIMIT_ENABLED, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_SECONDS,
    LLM_DAILY_LIMIT,
)
from university_recruitment.llm import LlmMatcher
from university_recruitment.matching import RuleMatcher
from university_recruitment.models import (
    JobListResponse, JobStatus, MatchRequest, MatchResponse, PaginationMeta,
)
from university_recruitment.storage import JobStore

logger = logging.getLogger(__name__)

# ── Rate limiter (in-memory, single-process) ──────────
_rate_limit_store: dict[str, list[float]] = {}
_llm_counter: dict[str, int] = {}
_llm_day: str = ""


def _clean_rate_store() -> None:
    """Remove expired rate limit entries."""
    now = time.time()
    window = RATE_LIMIT_WINDOW_SECONDS
    expired = [k for k, v in _rate_limit_store.items() if not v or v[-1] < now - window]
    for k in expired:
        del _rate_limit_store[k]


def _check_rate_limit(key: str) -> bool:
    """Returns True if request is allowed."""
    if not RATE_LIMIT_ENABLED:
        return True
    now = time.time()
    window = RATE_LIMIT_WINDOW_SECONDS
    if key not in _rate_limit_store:
        _rate_limit_store[key] = []
    _rate_limit_store[key] = [t for t in _rate_limit_store[key] if t > now - window]
    if len(_rate_limit_store[key]) >= RATE_LIMIT_REQUESTS:
        return False
    _rate_limit_store[key].append(now)
    return True


def _check_llm_limit() -> bool:
    """Returns True if LLM request is within daily limit."""
    global _llm_day, _llm_counter
    from datetime import date
    today = date.today().isoformat()
    if _llm_day != today:
        _llm_day = today
        _llm_counter = {}
    count = _llm_counter.get("calls", 0)
    if count >= LLM_DAILY_LIMIT:
        return False
    _llm_counter["calls"] = count + 1
    return True


# ── Auth ──────────────────────────────────────────────

def verify_token(request: Request) -> None:
    if not API_ACCESS_TOKEN:
        return  # No token configured — allow all
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = auth[len("Bearer "):]
    if token != API_ACCESS_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid access token")


# ── App setup ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    store.init_db()
    yield


app = FastAPI(
    title="University Recruitment Matcher",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
if not origins and APP_ENV == "development":
    origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
if APP_ENV != "development" and not origins:
    logger.warning("CORS_ALLOWED_ORIGINS is empty in non-development mode — no cross-origin requests allowed")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["null"],  # "null" effectively blocks all CORS
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

store = JobStore()
rule_matcher = RuleMatcher()
llm_matcher = LlmMatcher()


# ── Error handlers ────────────────────────────────────

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ── Middleware ────────────────────────────────────────

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Endpoints ─────────────────────────────────────────

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.2.0"}


@app.get("/jobs", response_model=JobListResponse)
def list_jobs(
    request: Request,
    status: str | None = None,
    school: str | None = None,
    location: str | None = None,
    source_name: str | None = None,
    include_expired: bool = False,
    include_removed: bool = False,
    limit: int = 100,
    offset: int = 0,
    _auth: None = Depends(verify_token),
) -> JobListResponse:
    job_status = JobStatus(status) if status else None
    jobs, total = store.list_jobs(
        status=job_status,
        include_expired=include_expired,
        include_removed=include_removed,
        school=school,
        source_name=source_name,
        location=location,
        limit=min(limit, 200),
        offset=offset,
    )
    return JobListResponse(
        jobs=jobs,
        pagination=PaginationMeta(
            total=total,
            limit=min(limit, 200),
            offset=offset,
            has_more=(offset + min(limit, 200)) < total,
        ),
    )


@app.post("/match", response_model=MatchResponse)
def match_jobs(
    request: Request,
    body: MatchRequest,
    _auth: None = Depends(verify_token),
) -> MatchResponse:
    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests")

    if body.use_llm and not _check_llm_limit():
        raise HTTPException(status_code=429, detail="LLM daily limit reached")

    # Gather candidates
    jobs, _ = store.list_jobs(
        status=JobStatus.ACTIVE,
        limit=body.candidate_limit,
    )
    total_candidates = len(jobs)

    # Rule match
    results = rule_matcher.rank(
        body.user,
        jobs,
        limit=body.candidate_limit,
        include_hard_failures=body.include_hard_constraint_failures,
    )
    hard_filtered = total_candidates - len(results)

    # LLM batch rerank
    if body.use_llm and results:
        results = llm_matcher.enrich(body.user, results)
        # Re-sort after LLM adjusts scores
        results.sort(key=lambda r: r.match_score, reverse=True)

    return MatchResponse(
        results=results[:body.result_limit],
        total_candidates=total_candidates,
        hard_filtered_out=hard_filtered,
    )


@app.get("/collection-runs")
def list_collection_runs(
    limit: int = 20,
    _auth: None = Depends(verify_token),
) -> list[dict[str, Any]]:
    runs = store.get_latest_collection_runs(limit=limit)
    return [r.model_dump(mode="json") for r in runs]


@app.get("/collection-runs/{run_id}")
def get_collection_run(
    run_id: str,
    _auth: None = Depends(verify_token),
) -> dict[str, Any]:
    run = store.get_collection_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    source_runs = store.get_source_runs_for_run(run_id)
    return {
        "run": run.model_dump(mode="json"),
        "sources": [sr.model_dump(mode="json") for sr in source_runs],
    }


@app.get("/source-health")
def source_health(
    _auth: None = Depends(verify_token),
) -> list[dict[str, Any]]:
    return store.get_source_health()


def main() -> None:
    import uvicorn
    uvicorn.run(
        "university_recruitment.user_portal.api:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=False,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
