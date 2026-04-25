import re
from typing import ClassVar

from workflow_memory.site_adapters.base import SiteAdapter

_TIME_PATTERN = re.compile(r"\d{1,2}:\d{2}")


class MaiScheduleAdapter(SiteAdapter):
    site_id: ClassVar[str] = "mai_schedule"
    entrypoint_url: ClassVar[str] = "https://mai.ru/education/studies/schedule/groups.php"

    def build_task_prompt(self, task: str) -> str:
        """Prepend the MAI schedule URL to the user's natural-language task."""
        return (
            f"Go to {self.entrypoint_url} and complete the following task:\n{task}\n"
            "Return the result as a structured list with time, subject, room, and instructor."
        )

    def verify_result(self, task: str, result: str | None) -> bool:
        if not result:
            return False
        if len(result) <= 50:
            return False
        if not _TIME_PATTERN.search(result):
            return False
        return True
