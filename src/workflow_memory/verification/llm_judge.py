"""LLM-based result judge (WebJudge-inspired)."""
import os
from typing import Any


def build_llm_judge_payload(
    task_description: str,
    structured_output: dict[str, Any],
    action_history: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the payload sent to the LLM judge.

    Args:
        task_description: Natural-language task description.
        structured_output: The agent's structured output.
        action_history: Normalized action history.

    Returns:
        Payload dict ready for the judge LLM.
    """
    return {
        "task_description": task_description,
        "structured_output": structured_output,
        "action_history": action_history,
        "mode": "webjudge-inspired",
    }


def run_llm_judge(model_name: str, payload: dict[str, Any], base_url: str | None = None, api_key: str | None = None) -> dict[str, Any]:
    """Run the LLM judge against a task result payload.

    Args:
        model_name: Model identifier (supports OpenRouter format).
        payload: Judge payload from build_llm_judge_payload.
        base_url: Optional OpenRouter / custom base URL.
        api_key: Optional API key override.

    Returns:
        Dict with 'raw_text' and parsed 'passed', 'rationale', 'confidence'.
    """
    from openai import OpenAI

    client_kwargs: dict[str, Any] = {}
    if base_url:
        client_kwargs["base_url"] = base_url
    if api_key:
        client_kwargs["api_key"] = api_key

    client = OpenAI(**client_kwargs)
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": "Return JSON with passed (bool), rationale (str), and confidence (float 0-1) for a web-task verdict.",
            },
            {"role": "user", "content": str(payload)},
        ],
    )
    raw = response.choices[0].message.content or ""
    return {"raw_text": raw}
