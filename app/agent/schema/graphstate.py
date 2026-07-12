from typing import Any , TypedDict , List , Dict
from pydantic import BaseModel, Field


class GraphState(TypedDict):
    query: str
    parent_ids: List[str]
    child_ids: List[str]
    context: str
    retried: bool
    answer: str

    child_records: List[Dict[str, Any]]
    needs_retry: bool