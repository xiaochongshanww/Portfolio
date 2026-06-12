import uvicorn
from fastapi import FastAPI

from university_recruitment.llm import LlmMatcher
from university_recruitment.matching import RuleMatcher
from university_recruitment.models import MatchRequest, MatchResponse, RecruitmentJob
from university_recruitment.storage import JobStore


app = FastAPI(title="University Recruitment Matcher", version="0.1.0")
store = JobStore()
rule_matcher = RuleMatcher()
llm_matcher = LlmMatcher()


@app.on_event("startup")
def startup() -> None:
    store.init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/jobs", response_model=list[RecruitmentJob])
def list_jobs(include_expired: bool = False) -> list[RecruitmentJob]:
    return store.list_jobs(include_expired=include_expired)


@app.post("/match", response_model=MatchResponse)
def match_jobs(request: MatchRequest) -> MatchResponse:
    jobs = store.list_jobs(include_expired=False)
    results = rule_matcher.rank(request.user, jobs, limit=request.limit)
    if request.use_llm:
        results = llm_matcher.enrich(request.user, results)
    return MatchResponse(results=results)


def main() -> None:
    uvicorn.run("university_recruitment.user_portal.api:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
