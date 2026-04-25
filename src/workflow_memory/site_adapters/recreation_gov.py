import re
from typing import ClassVar

from workflow_memory.site_adapters.base import SiteAdapter

_CAMPSITE_PATTERN = re.compile(r"campsite|campground|available", re.IGNORECASE)


class RecreationGovAdapter(SiteAdapter):
    site_id: ClassVar[str] = "recreation_gov"
    entrypoint_url: ClassVar[str] = "https://www.recreation.gov/"

    def build_task_prompt(self, task: str) -> str:
        """Prepend the Recreation.gov URL to the user's natural-language task."""
        return (
            f"Go to {self.entrypoint_url} and complete the following task:\n{task}\n"
            "Return a structured summary including campground name, availability, dates, and site type."
        )

    def verify_result(self, task: str, result: str | None) -> bool:
        if not result:
            return False
        if len(result) <= 50:
            return False
        if not _CAMPSITE_PATTERN.search(result):
            return False
        return True
