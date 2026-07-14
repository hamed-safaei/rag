from typing import Any, Dict, List, TypedDict


class GraphState(TypedDict, total=False):
    query: str
    session_id: str

    route: str 

    parent_ids: List[str]
    child_ids: List[str]
    context: str
    retried: bool

    history: str

    answer: str

    child_records: List[Dict[str, Any]]
    child_after_transform: List[Dict[str, Any]]
    needs_retry: bool