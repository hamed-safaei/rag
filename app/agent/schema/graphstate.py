# from typing import Any , TypedDict , List , Dict
# from pydantic import BaseModel, Field


# class GraphState(TypedDict):
#     query: str
#     parent_ids: List[str]
#     child_ids: List[str]
#     context: str
#     retried: bool
#     answer: str

#     child_records: List[Dict[str, Any]]
#     needs_retry: bool


from typing import Any, Dict, List, TypedDict


class GraphState(TypedDict):
    query: str
    parent_ids: List[str]
    child_ids: List[str]
    context: str
    retried: bool
    answer: str

    # فیلدهای داخلی/کمکی (برای پیاده‌سازی گراف، خارج از ۶ فیلد اصلی)
    child_records: List[Dict[str, Any]]
    child_after_transform: List[Dict[str, Any]]
    needs_retry: bool