"""Page-state fingerprinting and near-identical detection."""


def _normalize_path(url: str) -> str:
    return url.split("?")[0].rstrip("/")


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def page_state_similarity(left: dict, right: dict) -> float:
    """Compute a [0, 1] similarity score between two page-state dicts.

    Weights: path 40%, title 20%, labels 40%.
    """
    path_score = 1.0 if _normalize_path(left["url"]) == _normalize_path(right["url"]) else 0.0
    title_score = 1.0 if left.get("title") == right.get("title") else 0.0
    label_score = _jaccard(set(left.get("labels", [])), set(right.get("labels", [])))
    return round((0.4 * path_score) + (0.2 * title_score) + (0.4 * label_score), 2)
