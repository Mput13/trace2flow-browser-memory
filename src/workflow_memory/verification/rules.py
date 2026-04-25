"""Rule-based result verification."""
from typing import Any


def rule_based_verdict(
    required_fields: list[str],
    structured_output: dict[str, Any],
) -> dict[str, Any]:
    """Check that all required fields are present and non-empty.

    Args:
        required_fields: List of field names that must be present.
        structured_output: The agent's structured output dict.

    Returns:
        Dict with 'passed' bool and 'missing_fields' list.
    """
    missing = [field for field in required_fields if not structured_output.get(field)]
    return {"passed": not missing, "missing_fields": missing}
