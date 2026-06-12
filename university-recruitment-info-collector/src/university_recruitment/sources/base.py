from abc import ABC, abstractmethod

from university_recruitment.models import RecruitmentJob


class SourceAdapter(ABC):
    source_name: str

    @abstractmethod
    def collect(self) -> list[RecruitmentJob]:
        """Collect source data and return normalized recruitment jobs."""
