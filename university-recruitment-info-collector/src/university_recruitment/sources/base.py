from abc import ABC, abstractmethod
from copy import deepcopy
from time import perf_counter

from university_recruitment.models import RecruitmentJob


class SourceAdapter(ABC):
    source_name: str

    def _init_profile_stats(self) -> None:
        self._profile_stats = {
            "list_requests": 0,
            "list_seconds": 0.0,
            "detail_requests": 0,
            "detail_seconds": 0.0,
            "detail_success": 0,
            "detail_failures": 0,
            "candidates_seen": 0,
            "detail_limit": None,
            "notes": [],
        }

    def _ensure_profile_stats(self) -> None:
        if not hasattr(self, "_profile_stats"):
            self._init_profile_stats()

    def _record_profile(self, key: str, value: int | float = 1) -> None:
        self._ensure_profile_stats()
        self._profile_stats[key] = self._profile_stats.get(key, 0) + value

    def _set_profile(self, key: str, value) -> None:
        self._ensure_profile_stats()
        self._profile_stats[key] = value

    def _append_profile_note(self, note: str) -> None:
        self._ensure_profile_stats()
        self._profile_stats.setdefault("notes", []).append(note)

    def get_profile_stats(self) -> dict:
        self._ensure_profile_stats()
        return deepcopy(self._profile_stats)

    def _timed_profile_block(self, request_key: str, seconds_key: str):
        self._ensure_profile_stats()

        class _ProfileTimer:
            def __init__(self, outer):
                self.outer = outer
                self.started_at = 0.0

            def __enter__(self):
                self.outer._record_profile(request_key, 1)
                self.started_at = perf_counter()
                return self

            def __exit__(self, exc_type, exc, tb):
                self.outer._record_profile(seconds_key, perf_counter() - self.started_at)

        return _ProfileTimer(self)

    @abstractmethod
    def collect(self) -> list[RecruitmentJob]:
        """Collect source data and return normalized recruitment jobs."""
