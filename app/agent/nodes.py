from typing import Any, Dict, List, TypedDict
from app.services import rerank_results , format_chunks , build_context , search_children
from app.agent.services import generate_answer , evaluate_retrieved , route_query
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



# Node 1: retrieve + rerank

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


# Node 2: evaluate (تشخیص parent/child مرتبط + retry) + ساخت context اولیه

def node_evaluate(state: GraphState) -> Dict[str, Any]:
    raw_text = format_chunks(state["child_records"])

    ids_input = evaluate_retrieved(state["query"], raw_text)

    parent_ids = ids_input.get("parent_ids", []) or []
    child_ids = ids_input.get("child_ids", []) or []

    context = build_context(
        ids_input,
        state["child_records"],
        parent_collection_name=PARENT_COLLECTION,
    )

    return {
        "parent_ids": parent_ids,
        "child_ids": child_ids,
        "context": context,
        "needs_retry": bool(ids_input.get("retry", False)),
    }


def route_after_evaluate(state: GraphState) -> str:
    """فقط بار اول (retried هنوز false) اگر مدل retry=true داد، برو به transform."""
    if state.get("needs_retry") and not state.get("retried"):
        return "transform"
    return "generate"


# Node 3: query transform + جست‌وجوی مجدد + ارزیابی مجدد

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

    parent_ids_set = set(state["parent_ids"])
    child_ids_set = set(state["child_ids"])

    filtered_child_results = [
        item
        for item in unique_child_results
        if item.parent_id not in parent_ids_set and item.child_id not in child_ids_set
    ]

    # اگر چیز جدیدی پیدا نشد، فقط retried را true می‌کنیم و می‌رویم سراغ generate
    if not filtered_child_results:
        return {"retried": True}

    filtered_as_dicts = [_to_dict(item) for item in filtered_child_results]

    raw_text = format_chunks(filtered_as_dicts)
    ids_input = evaluate_retrieved(state["query"], raw_text)

    new_parent_ids = ids_input.get("parent_ids", []) or []
    new_child_ids = ids_input.get("child_ids", []) or []

    # child_records تجمیعی برای اینکه build_context بتواند محتوای child_id های جدید را پیدا کند
    updated_child_records = state["child_records"] + filtered_as_dicts

    new_context = build_context(
        {"parent_ids": new_parent_ids, "child_ids": new_child_ids},
        updated_child_records,
        parent_collection_name=PARENT_COLLECTION,
    )

    merged_context = state["context"]
    if new_context:
        merged_context = f"{merged_context}\n\n{new_context}" if merged_context else new_context

    merged_parent_ids = state["parent_ids"] + [
        pid for pid in dict.fromkeys(new_parent_ids) if pid not in parent_ids_set
    ]
    merged_child_ids = state["child_ids"] + [
        cid for cid in dict.fromkeys(new_child_ids) if cid not in child_ids_set
    ]

    return {
        "parent_ids": merged_parent_ids,
        "child_ids": merged_child_ids,
        "context": merged_context,
        "child_records": updated_child_records,
        "retried": True,
    }


# Node 4: generate

def node_generate(state: GraphState) -> Dict[str, Any]:
    answer = generate_answer(state["query"], state["context"])
    return {"answer": answer}

