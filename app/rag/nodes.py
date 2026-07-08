from app.rag.decider import decide_context, _build_context
from app.rag.coverage_checker import Coverage_Checker
from app.rag.query_transformer import route_query
from app.rag.generator import generate_answer
from app.services.retriever import search_children
from typing import TypedDict
from app.rag.schema.graphstate import RAGState


FIRST_SEARCH_TOP_K = 5     
TRANSFORM_TOP_K = 1        




def _extract_transform_queries(route_result: dict) -> list[str]:
    """
    از خروجی route_query (که یا multiquery است یا decompose)، لیست
    query/sub_query هایی که باید دوباره سرچ شوند را استخراج می‌کند.
    """
    tool_used = route_result.get("tool_used")
    result = route_result.get("result", {})

    if tool_used == "decompose":
        queries = result.get("sub_queries", [])
    else:  # multiquery یا هر حالت پیش‌فرض دیگر
        queries = result.get("queries", [])

    return [q for q in queries if str(q).strip()]


# Node 1 

def node_search(state: RAGState) -> dict:
    child_results = search_children(
        state.query,
        collection_name="loader_children",
        top_k=FIRST_SEARCH_TOP_K,
    )
    return {"child_results": child_results}


# Node 2 

def node_decide(state: RAGState) -> dict:
    result = decide_context(state.query, state.child_results)
    return {
        "parent_ids": result.parent_ids,
        "context": result.context,
    }


# Node 3 

def node_coverage(state: RAGState) -> dict:
    check_result = Coverage_Checker(state.query, state.context)
    return {
        "status": check_result.get("status", "NOT_FOUND"),
        "missing": check_result.get("missing", []),
    }


# Node 4

def node_transform(state: RAGState) -> dict:
    missing_list = state.missing or []

    if not missing_list:
        return {
            "retried": True,
            "missing_before_transform": [],
            "transform_tool_used": [],
            "transform_queries": [],
        }

    all_new_child_results = []
    transform_tool_used: list[str] = []
    transform_queries_all: list[str] = []

    for missing_query in missing_list:
        route_result = route_query(missing_query)

        tool_used = route_result.get("tool_used", "")
        transform_tool_used.append(tool_used)

        transform_queries = _extract_transform_queries(route_result)
        if not transform_queries:
            transform_queries = [missing_query]

        transform_queries_all.extend(transform_queries)

        for q in transform_queries:
            results = search_children(
                query=q,
                collection_name="loader_children",
                top_k=TRANSFORM_TOP_K,
            )
            all_new_child_results.extend(results)


        # فقط parent_id های یکتا
        unique_parent_ids = list({
            r.parent_id
            for r in all_new_child_results
        })


        # حذف parent هایی که قبلاً داشتیم
        seen_parent_ids = set(state.parent_ids)

        new_parent_ids = [
            pid
            for pid in unique_parent_ids
            if pid not in seen_parent_ids
        ]

    new_context = ""
    if new_parent_ids:
        new_context = _build_context(new_parent_ids)

    merged_context = state.context
    if new_context:
        merged_context = (
            f"{merged_context}\n\n{new_context}".strip()
            if merged_context
            else new_context
        )

    merged_parent_ids = list(seen_parent_ids | set(new_parent_ids))

    return {
        "context": merged_context,
        "parent_ids": merged_parent_ids,
        "retried": True,
        "missing_before_transform": missing_list,
        "transform_tool_used": transform_tool_used,
        "transform_queries": transform_queries_all,
    }


# Node 5 

def node_generate(state: RAGState) -> dict:
    answer = generate_answer(state.query, state.context)
    return {"answer": answer}


# router

def route_after_coverage(state: RAGState) -> str:
    if state.status == "COMPLETE":
        return "generate"

    if state.retried:
        return "generate"

    return "transform"