"""Single optimization pass: analyze a baseline run and produce a hint packet."""
from typing import Any

from pydantic import BaseModel


class PageNode(BaseModel):
    url_pattern: str
    description: str
    params: dict[str, str] = {}


class OptimizationResponse(BaseModel):
    analysis: dict[str, Any]
    optimized_workflow: dict[str, Any]
    human_summary: str | None = None
    site_pages: list[PageNode] = []


def build_hint_packet(
    analysis: dict[str, Any],
    optimized_workflow: dict[str, Any],
) -> dict[str, Any]:
    """Assemble a structured hint packet from analysis + optimized workflow.

    Args:
        analysis: Analysis dict (e.g. wasted_steps, loop_count).
        optimized_workflow: Workflow dict with likely_path, page_hints, etc.

    Returns:
        Hint packet dict ready for storage and retrieval.
    """
    return {
        "goal": optimized_workflow.get("goal", "Complete the task efficiently"),
        "analysis": analysis,
        "direct_url": optimized_workflow.get("direct_url"),
        "likely_path": optimized_workflow.get("likely_path", ""),
        "page_hints": optimized_workflow.get("page_hints", []),
        "success_cues": optimized_workflow.get("success_cues", []),
        "mismatch_signals": optimized_workflow.get("mismatch_signals", []),
    }


def run_optimization_pass(
    model_name: str,
    packet: dict[str, Any],
    base_url: str | None = None,
    api_key: str | None = None,
) -> OptimizationResponse:
    """Call the optimizer LLM to produce an OptimizationResponse.

    Args:
        model_name: Model identifier (supports OpenRouter format).
        packet: Raw analysis packet from the baseline run.
        base_url: Optional OpenRouter / custom base URL.
        api_key: Optional API key override.

    Returns:
        Validated OptimizationResponse.
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
                "content": (
                    "You are a browser workflow optimizer. "
                    "You receive a browser agent run: task, site, action sequence, visited URLs, and final result. "
                    "Analyze the urls_visited list to extract site structure and find the most direct entry point. "
                    "Return JSON with these keys:\n"
                    "1. analysis: {current_flow_assessment, identified_bottlenecks, optimization_strategy}\n"
                    "2. optimized_workflow: {\n"
                    "     direct_url: the most efficient entry URL from urls_visited (or null),\n"
                    "     likely_path: fallback navigation description if direct_url is insufficient,\n"
                    "     page_hints: [strings],\n"
                    "     success_cues: [strings],\n"
                    "     mismatch_signals: [strings]\n"
                    "   }\n"
                    "3. site_pages: array of page nodes observed in urls_visited. Each node: {\n"
                    "     url_pattern: URL with variable parts replaced by {param_name} placeholders,\n"
                    "     description: what this page does and when to use it,\n"
                    "     params: {param_name: description} for each placeholder or query param\n"
                    "   }\n"
                    "   Example: url_pattern='mai.ru/schedule/index.php', params={'group': 'URL-encoded group name'}\n"
                    "4. human_summary: string"
                ),
            },
            {"role": "user", "content": str(packet)},
        ],
    )
    raw = response.choices[0].message.content or "{}"
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0].strip()
    return OptimizationResponse.model_validate_json(raw)
