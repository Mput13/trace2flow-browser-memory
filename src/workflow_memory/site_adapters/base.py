from abc import ABC, abstractmethod
from typing import ClassVar


class SiteAdapter(ABC):
    site_id: ClassVar[str]
    entrypoint_url: ClassVar[str]

    @abstractmethod
    def build_task_prompt(self, task: str) -> str:
        """Accept a natural-language task string, return a prompt for the browser agent."""
        ...

    @abstractmethod
    def verify_result(self, task: str, result: str | None) -> bool:
        """Check plausibility of the agent result for the given task."""
        ...
