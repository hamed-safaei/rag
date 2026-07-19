from typing import Any, Dict, List

from app.services import rerank_results, format_chunks, build_context, search_children
from app.agent.services import (
    generate_answer,
    evaluate_retrieved,
    route_query,        # decompose/multiquery chain
    classify_query,      # router
)
from app.agent.schema.graphstate import GraphState
from app.models.database import Message
from langfuse import observe
from langchain_core.runnables import RunnableConfig
from app.agent.schema import RouteDecision


TOP_K_RETRIEVE = 10
TOP_K_RERANK = 5
TRANSFORM_TOP_K = 1
PARENT_COLLECTION = "loader_parents"
CHILD_COLLECTION = "loader_children"
HISTORY_LIMIT = 10


def _to_dict(record: Any) -> Dict[str, Any]:
    if isinstance(record, dict):
        return record
    return {
        "parent_id": record.parent_id,
        "parent_title": record.parent_title,
        "child_id": record.child_id,
        "child_title": record.child_title,
        "child_content": record.child_content,
    }


def _search_query(state: GraphState) -> str:
    """پرسشی که برای retrieve/transform استفاده می‌شود: بازنویسی‌شده در صورت وجود، وگرنه اصلی."""
    return state.get("rewritten_query") or state["query"]


# ---------------------------------------------------------------------------
@observe(name="history")
def node_history(state: GraphState, config: RunnableConfig) -> Dict[str, Any]:
    db = config["configurable"]["db"]
    session_id = state["session_id"]

    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .offset(1)              # رد کردن آخرین پیام (همان query فعلی که قبلاً ثبت شده)
        .limit(HISTORY_LIMIT)
        .all()
    )
    messages = list(reversed(messages))  # قدیم -> جدید

    role_map = {"user": "کاربر", "agent": "دستیار"}
    lines = [
        f"{role_map.get(getattr(m, 'role', 'user'), 'کاربر')}: {getattr(m, 'content', '')}"
        for m in messages
    ]
    history_text = "\n\n".join(lines) if lines else "(تاریخچه‌ای وجود ندارد)"

    return {"history": history_text}

# ---------------------------------------------------------------------------
@observe(name="route")
def node_route(state: GraphState, config: RunnableConfig) -> Dict[str, Any]:
    result = classify_query(state["query"], state.get("history", ""))

    update: Dict[str, Any] = {"route": result.decision.value}
    if result.decision == RouteDecision.retrieve:
        # query اصلی کاربر دست‌نخورده می‌ماند؛ فقط rewritten_query ست می‌شود
        update["rewritten_query"] = result.query or state["query"]

    return update

# ---------------------------------------------------------------------------

@observe(name="after_route")
def route_after_route(state: GraphState) -> str:
    return state["route"]


# ---------------------------------------------------------------------------
@observe(name="retrieve")
def node_retrieve(state: GraphState) -> Dict[str, Any]:
    query = _search_query(state)

    child_results = search_children(
        query,
        collection_name=CHILD_COLLECTION,
        top_k=TOP_K_RETRIEVE,
    )

    top_results = rerank_results(
        query,
        child_results,
        top_k=TOP_K_RERANK,
    )

    return {"child_records": top_results}


# ---------------------------------------------------------------------------
@observe(name="evaluate")
def node_evaluate(state: GraphState) -> Dict[str, Any]:
    query = _search_query(state)

    child_after_transform = state.get("child_after_transform") or []
    round_records = child_after_transform if child_after_transform else state["child_records"]

    raw_text = format_chunks(round_records)
    ids_input = evaluate_retrieved(query, raw_text)

    new_parent_ids = ids_input.get("parent_ids", []) or []
    new_child_ids = ids_input.get("child_ids", []) or []

    existing_parent_ids = state.get("parent_ids", []) or []
    existing_child_ids = state.get("child_ids", []) or []
    existing_parent_set = set(existing_parent_ids)
    existing_child_set = set(existing_child_ids)

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
    if state.get("needs_retry") and not state.get("retried"):
        return "transform"
    return "generate"


# ---------------------------------------------------------------------------
@observe(name="transform")
def node_transform(state: GraphState) -> Dict[str, Any]:
    query = _search_query(state)
    query_transform = route_query(query)
    sub_queries = (query_transform.get("result") or {}).get("queries", []) or []

    all_new_child_results: List[Any] = []
    for q in sub_queries:
        results = search_children(
            query=q,
            collection_name=CHILD_COLLECTION,
            top_k=TRANSFORM_TOP_K,
        )
        all_new_child_results.extend(results)

    unique_child_results = list(
        {item.child_id: item for item in all_new_child_results}.values()
    )

    parent_ids_set = set(state.get("parent_ids", []) or [])
    child_ids_set = set(state.get("child_ids", []) or [])

    filtered_child_results = [
        item
        for item in unique_child_results
        if item.parent_id not in parent_ids_set and item.child_id not in child_ids_set
    ]

    if not filtered_child_results:
        return {"child_after_transform": [], "retried": True}

    filtered_as_dicts = [_to_dict(item) for item in filtered_child_results]

    return {
        "child_after_transform": filtered_as_dicts,
        "retried": True,
    }


def route_after_transform(state: GraphState) -> str:
    # چه رکورد جدید پیدا شده باشد چه نه، بعد از transform همیشه یک‌بار به evaluate برمی‌گردیم.
    # روند retried=True در evaluate جلوی loop دوباره را می‌گیرد (route_after_evaluate).
    return "evaluate"


# ---------------------------------------------------------------------------
@observe(name="generate")
def node_generate(state: GraphState) -> Dict[str, Any]:
    answer = generate_answer(
        query=state["query"],              # همیشه سوال اصلی کاربر، نه rewritten_query
        context=state.get("context", ""),
        history=state.get("history", ""),
    )
    return {"answer": answer}