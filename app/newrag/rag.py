"""
گراف RAG با LangGraph

جریان:
1) retrieve      : جست‌وجوی 10 مورد از Qdrant + Re-rank به 5 مورد برتر
2) evaluate       : ارزیابی قطعات توسط مدل، ساخت context اولیه، تصمیم retry
3) transform      : (فقط اگر retry=true و قبلاً retry نشده باشیم) تولید کوئری‌های
                     جایگزین، جست‌وجوی هرکدام، فیلتر موارد تکراری/قبلی، ارزیابی مجدد
                     و افزودن context جدید
4) generate       : تولید پاسخ نهایی از روی context جمع‌آوری‌شده

نکته‌ی کلیدی طبق خواسته‌ی شما:
- فقط بار اول اگر مدل retry=true بدهد وارد transform می‌شویم.
- بعد از یک بار transform (چه نتیجه‌ی جدید پیدا شود چه نه)، صرف‌نظر از هر چیزی
  مستقیم به generate می‌رویم.
"""

from typing import Any, Dict, List, TypedDict

from langgraph.graph import StateGraph, END

from app.utils.Retriever import search_children
from app.newrag.reranker import rerank_results
from app.newrag.evaluator import (
    evaluate_retrieved_raw_text,
    format_chunks,
    build_context,
)
from app.rag.query_transformer import route_query
from app.rag.generator import generate_answer


TOP_K_RETRIEVE = 10
TOP_K_RERANK = 5
TRANSFORM_TOP_K = 1
PARENT_COLLECTION = "loader_parents"
CHILD_COLLECTION = "loader_children"


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
class GraphState(TypedDict):
    query: str
    parent_ids: List[str]
    child_ids: List[str]
    context: str
    retried: bool
    answer: str

    # فیلدهای داخلی کمکی (بخشی از state لازم برای پیاده‌سازی، خارج از ۶ فیلد اصلی)
    child_records: List[Dict[str, Any]]
    needs_retry: bool


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
# Node 2: evaluate (تشخیص parent/child مرتبط + retry) + ساخت context اولیه
# ---------------------------------------------------------------------------
def node_evaluate(state: GraphState) -> Dict[str, Any]:
    raw_text = format_chunks(state["child_records"])

    ids_input = evaluate_retrieved_raw_text(state["query"], raw_text)

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


# ---------------------------------------------------------------------------
# Node 3: query transform + جست‌وجوی مجدد + ارزیابی مجدد
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
    ids_input = evaluate_retrieved_raw_text(state["query"], raw_text)

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


# ---------------------------------------------------------------------------
# Node 4: generate
# ---------------------------------------------------------------------------
def node_generate(state: GraphState) -> Dict[str, Any]:
    answer = generate_answer(state["query"], state["context"])
    return {"answer": answer}


# ---------------------------------------------------------------------------
# ساخت گراف
# ---------------------------------------------------------------------------
def build_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node("retrieve", node_retrieve)
    workflow.add_node("evaluate", node_evaluate)
    workflow.add_node("transform", node_transform)
    workflow.add_node("generate", node_generate)

    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "evaluate")

    workflow.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {
            "transform": "transform",
            "generate": "generate",
        },
    )

    workflow.add_edge("transform", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


graph = build_graph()


