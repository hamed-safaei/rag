from typing import Any, Dict, List

from app.services import rerank_results, format_chunks, build_context, search_children
from app.agent.services import generate_answer, evaluate_retrieved, route_query
from app.agent.schema.graphstate import GraphState


TOP_K_RETRIEVE = 10
TOP_K_RERANK = 5
TRANSFORM_TOP_K = 1
PARENT_COLLECTION = "loader_parents"
CHILD_COLLECTION = "loader_children"


def _to_dict(record: Any) -> Dict[str, Any]:
    """تبدیل یک child record (dict یا آبجکت ChildSearchResult) به dict یکنواخت."""
    if isinstance(record, dict):
        return record
    return {
        "parent_id": record.parent_id,
        "parent_title": record.parent_title,
        "child_id": record.child_id,
        "child_title": record.child_title,
        "child_content": record.child_content,
    }


# ---------------------------------------------------------------------------
# Node 1: retrieve + rerank
# ---------------------------------------------------------------------------
def node_retrieve(state: GraphState) -> Dict[str, Any]:
    child_results = search_children(
        state["query"],
        collection_name=CHILD_COLLECTION,
        top_k=TOP_K_RETRIEVE,
    )

    top_results = rerank_results(
        state["query"],
        child_results,
        top_k=TOP_K_RERANK,
    )

    return {"child_records": top_results}


# ---------------------------------------------------------------------------
# Node 2: evaluate
# این نود هم بار اول (روی child_records اولیه) و هم بعد از transform
# (روی child_after_transform) صدا زده می‌شود. تنها جایی است که
# parent_ids / child_ids / context آپدیت می‌شوند.
# ---------------------------------------------------------------------------
def node_evaluate(state: GraphState) -> Dict[str, Any]:
    # اگر از مرحله‌ی transform برگشته‌ایم، فقط رکوردهای جدید را بررسی کن؛
    # وگرنه (دور اول) روی کل child_records بازیابی‌شده کار کن.
    child_after_transform = state.get("child_after_transform") or []
    round_records = child_after_transform if child_after_transform else state["child_records"]

    raw_text = format_chunks(round_records)
    ids_input = evaluate_retrieved(state["query"], raw_text)

    new_parent_ids = ids_input.get("parent_ids", []) or []
    new_child_ids = ids_input.get("child_ids", []) or []

    existing_parent_ids = state.get("parent_ids", []) or []
    existing_child_ids = state.get("child_ids", []) or []
    existing_parent_set = set(existing_parent_ids)
    existing_child_set = set(existing_child_ids)

    # new_child_ids همیشه دقیقاً از دل round_records می‌آیند (چون همان چیزی
    # است که به evaluator نشان داده شد)، پس همان pool برای build_context کافی است
    new_context = build_context(
        {"parent_ids": new_parent_ids, "child_ids": new_child_ids},
        round_records,
        parent_collection_name=PARENT_COLLECTION,
    )

    merged_context = state.get("context", "")
    if new_context:
        merged_context = f"{merged_context}\n\n{new_context}" if merged_context else new_context

    merged_parent_ids = existing_parent_ids + [
        pid for pid in dict.fromkeys(new_parent_ids) if pid not in existing_parent_set
    ]
    merged_child_ids = existing_child_ids + [
        cid for cid in dict.fromkeys(new_child_ids) if cid not in existing_child_set
    ]

    return {
        "parent_ids": merged_parent_ids,
        "child_ids": merged_child_ids,
        "context": merged_context,
        "needs_retry": bool(ids_input.get("retry", False)),
    }


def route_after_evaluate(state: GraphState) -> str:
    """فقط بار اول (retried هنوز false) اگر مدل retry=true داد، برو به transform."""
    if state.get("needs_retry") and not state.get("retried"):
        return "transform"
    return "generate"


# ---------------------------------------------------------------------------
# Node 3: query transform + جست‌وجوی مجدد
# این نود فقط رکوردهای جدید را پیدا و فیلتر می‌کند و در child_after_transform
# می‌گذارد. هیچ آپدیتی روی parent_ids/child_ids/context انجام نمی‌دهد —
# آن کار فقط به عهده‌ی node_evaluate است.
# ---------------------------------------------------------------------------
def node_transform(state: GraphState) -> Dict[str, Any]:
    query_transform = route_query(state["query"])
    sub_queries = (query_transform.get("result") or {}).get("queries", []) or []

    all_new_child_results: List[Any] = []
    for q in sub_queries:
        results = search_children(
            query=q,
            collection_name=CHILD_COLLECTION,
            top_k=TRANSFORM_TOP_K,
        )
        all_new_child_results.extend(results)

    # فقط موارد یونیک
    unique_child_results = list(
        {item.child_id: item for item in all_new_child_results}.values()
    )

    # فیلتر بر اساس parent_ids/child_ids ای که تا این لحظه توسط evaluate
    # تایید شده‌اند (همان منطق اصلی و درست)
    parent_ids_set = set(state.get("parent_ids", []) or [])
    child_ids_set = set(state.get("child_ids", []) or [])

    filtered_child_results = [
        item
        for item in unique_child_results
        if item.parent_id not in parent_ids_set and item.child_id not in child_ids_set
    ]

    # چیز جدیدی پیدا نشد → مستقیم به سمت generate می‌رویم
    if not filtered_child_results:
        return {"child_after_transform": [], "retried": True}

    filtered_as_dicts = [_to_dict(item) for item in filtered_child_results]

    return {
        "child_after_transform": filtered_as_dicts,
        "retried": True,
    }


def route_after_transform(state: GraphState) -> str:
    """اگر رکورد جدیدی پیدا شد برو evaluate تا بررسی و state ها آپدیت شوند،
    وگرنه مستقیم برو generate."""
    if state.get("child_after_transform"):
        return "evaluate"
    return "generate"


# ---------------------------------------------------------------------------
# Node 4: generate
# ---------------------------------------------------------------------------
def node_generate(state: GraphState) -> Dict[str, Any]:
    answer = generate_answer(state["query"], state["context"])
    return {"answer": answer}