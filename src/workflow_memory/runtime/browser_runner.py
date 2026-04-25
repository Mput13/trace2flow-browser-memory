import os
import time
from dataclasses import dataclass
from typing import Any, Protocol

from browser_use import Agent, BrowserProfile, ChatOpenAI
from browser_use.agent.views import AgentHistoryList


class AgentFactory(Protocol):
    def __call__(self, task: str, llm: Any, browser_profile: Any) -> Any: ...


@dataclass
class BrowserRunResult:
    history: AgentHistoryList
    elapsed_seconds: float


class BrowserRunner:
    def __init__(
        self,
        model: str,
        headless: bool = True,
        max_failures: int = 3,
        agent_factory: AgentFactory | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.headless = headless
        self.max_failures = max_failures
        self._agent_factory = agent_factory
        self._base_url = base_url
        self._api_key = api_key

    @classmethod
    def from_config(cls, config: Any, **kwargs: Any) -> "BrowserRunner":
        """Create a BrowserRunner from a ProjectConfig, respecting llm_provider settings."""
        base_url = getattr(config, "llm_base_url", None)
        api_key_env = getattr(config, "llm_api_key_env", "OPENAI_API_KEY")
        api_key = os.environ.get(api_key_env)
        return cls(
            model=config.judge_model,
            base_url=base_url,
            api_key=api_key,
            **kwargs,
        )

    def _build_llm(self) -> ChatOpenAI:
        kwargs: dict[str, Any] = {"model": self.model}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        if self._api_key:
            kwargs["api_key"] = self._api_key
        return ChatOpenAI(**kwargs)

    def run(self, task_prompt: str, max_steps: int = 25) -> BrowserRunResult:
        llm = self._build_llm()
        profile = BrowserProfile(headless=self.headless)
        if self._agent_factory is not None:
            agent = self._agent_factory(task=task_prompt, llm=llm, browser_profile=profile)
        else:
            agent = Agent(
                task=task_prompt,
                llm=llm,
                browser_profile=profile,
                use_judge=False,
                generate_gif=False,
                max_failures=self.max_failures,
            )
        start = time.time()
        history = agent.run_sync(max_steps=max_steps)
        elapsed = time.time() - start
        return BrowserRunResult(history=history, elapsed_seconds=elapsed)
