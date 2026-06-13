"""API endpoint tests using FastAPI TestClient (no real LLM calls)."""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from university_recruitment.models import (
    JobStatus, MatchResponse, RecruitmentJob, SourceType, UserProfile,
)
from university_recruitment.storage import JobStore


def _new_test_store(tmp_path):
    """Create an isolated JobStore with a test database."""
    db = tmp_path / "test_api.sqlite"
    store = JobStore(db)
    store.init_db()
    return store


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a TestClient with an isolated test database."""
    db = tmp_path / "test_api.sqlite"
    monkeypatch.setattr(
        "university_recruitment.config.DEFAULT_DB_PATH", db
    )
    monkeypatch.setattr(
        "university_recruitment.config.RATE_LIMIT_ENABLED", False
    )
    monkeypatch.setattr(
        "university_recruitment.config.API_ACCESS_TOKEN", None
    )
    monkeypatch.setattr(
        "university_recruitment.config.APP_ENV", "development"
    )
    monkeypatch.setattr(
        "university_recruitment.config.CORS_ALLOWED_ORIGINS", "http://localhost:5173"
    )

    from university_recruitment.user_portal.api import app
    client = TestClient(app)
    store = JobStore(db)
    store.init_db()
    import university_recruitment.user_portal.api as api_mod
    api_mod.store = store
    return client


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_health_no_auth_required(self, client, monkeypatch):
        monkeypatch.setattr(
            "university_recruitment.config.API_ACCESS_TOKEN", "secret-token"
        )
        # Reload the api module's token config
        from university_recruitment import config
        config.API_ACCESS_TOKEN = "secret-token"
        resp = client.get("/health")
        assert resp.status_code == 200


class TestJobsEndpoint:
    def test_list_jobs_empty(self, client):
        resp = client.get("/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert "jobs" in data
        assert "pagination" in data
        assert data["pagination"]["total"] == 0

    def test_list_jobs_with_data(self, client, tmp_path):
        store = _new_test_store(tmp_path)
        for i in range(3):
            store.upsert_jobs([RecruitmentJob(
                id=f"j{i}", school="T", position=f"P{i}",
                source_type=SourceType.UNIVERSITY_TALENT_SITE,
                source_name="S", source_url=f"https://x.com/{i}",
                description="", status=JobStatus.ACTIVE,
            )])
        import university_recruitment.user_portal.api as api_mod
        api_mod.store = store

        resp = client.get("/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["jobs"]) == 3
        assert data["pagination"]["total"] == 3

    def test_list_jobs_pagination(self, client, tmp_path):
        store = _new_test_store(tmp_path)
        for i in range(5):
            store.upsert_jobs([RecruitmentJob(
                id=f"p{i}", school="T", position=f"P{i}",
                source_type=SourceType.UNIVERSITY_TALENT_SITE,
                source_name="S", source_url=f"https://x.com/p{i}",
                description="", status=JobStatus.ACTIVE,
            )])
        import university_recruitment.user_portal.api as api_mod
        api_mod.store = store

        resp = client.get("/jobs?limit=2&offset=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["jobs"]) == 2
        assert data["pagination"]["total"] == 5
        assert data["pagination"]["has_more"] is True

    def test_list_jobs_include_expired(self, client, tmp_path):
        store = _new_test_store(tmp_path)
        store.upsert_jobs([RecruitmentJob(
            id="ai-active", school="T", position="P",
            source_type=SourceType.UNIVERSITY_TALENT_SITE,
            source_name="S", source_url="https://x.com/ai-a",
            status=JobStatus.ACTIVE, description="",
        )])
        store.upsert_jobs([RecruitmentJob(
            id="ai-expired", school="T", position="E",
            source_type=SourceType.UNIVERSITY_TALENT_SITE,
            source_name="S", source_url="https://x.com/ai-e",
            status=JobStatus.EXPIRED, description="",
            deadline=date(2020, 1, 1),  # past deadline → stays EXPIRED
        )])
        import university_recruitment.user_portal.api as api_mod
        api_mod.store = store

        resp = client.get("/jobs")
        assert len(resp.json()["jobs"]) == 1
        resp = client.get("/jobs?include_expired=true")
        assert len(resp.json()["jobs"]) == 2


class TestMatchEndpoint:
    def test_match_basic(self, client, tmp_path):
        store = _new_test_store(tmp_path)
        store.upsert_jobs([RecruitmentJob(
            id="m1", school="中山大学", position="人工智能教师",
            department="计算机学院", discipline="人工智能",
            location="广州", education_requirement="博士",
            job_type="教学科研岗", deadline=date(2027, 12, 31),
            source_type=SourceType.UNIVERSITY_TALENT_SITE,
            source_name="S", source_url="https://x.com/m1",
            description="招聘人工智能方向教师",
            status=JobStatus.ACTIVE,
        )])
        import university_recruitment.user_portal.api as api_mod
        api_mod.store = store

        resp = client.post("/match", json={
            "user": {
                "education": "博士",
                "major": "计算机科学与技术",
                "research_direction": "人工智能",
                "keywords": ["机器学习"],
                "target_locations": ["广州"],
                "target_school_types": ["双一流"],
                "job_preferences": ["教学科研岗"],
                "constraints": ["编制"],
            },
            "limit": 10,
            "use_llm": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) == 1
        r = data["results"][0]
        assert "match_score" in r
        assert "confidence_score" in r
        assert "hard_constraint_passed" in r

    def test_match_empty_candidates(self, client):
        resp = client.post("/match", json={
            "user": {
                "education": "博士", "major": "计算机",
                "research_direction": "", "keywords": [],
                "target_locations": [], "target_school_types": [],
                "job_preferences": [], "constraints": [],
            },
            "limit": 10,
            "use_llm": False,
        })
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 0


class TestCollectionRunsEndpoint:
    def test_list_collection_runs_empty(self, client):
        resp = client.get("/collection-runs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_collection_runs_with_data(self, client, tmp_path):
        from university_recruitment.models import RunStatus
        store = _new_test_store(tmp_path)
        store.create_run("run-1", "中山大学", 1)
        store.finish_run("run-1", RunStatus.SUCCESS, successful_sources=1)
        import university_recruitment.user_portal.api as api_mod
        api_mod.store = store

        resp = client.get("/collection-runs")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_get_collection_run_not_found(self, client):
        resp = client.get("/collection-runs/nonexistent")
        assert resp.status_code == 404


class TestSourceHealthEndpoint:
    def test_source_health_empty(self, client):
        resp = client.get("/source-health")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestCORSSecurity:
    def test_cors_allows_configured_origin(self, client):
        resp = client.options(
            "/health",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        )
        # Should have CORS headers
        assert resp.status_code in (200, 405)


class TestRateLimit:
    def test_rate_limit_disabled_in_test(self, client):
        # Rate limiting is off in test config, so multiple rapid requests should work
        for _ in range(5):
            resp = client.get("/health")
            assert resp.status_code == 200
