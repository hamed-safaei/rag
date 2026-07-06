"""
app/rag/graph.py

منبع اصلی: app/utils/graph.py
فقط محل فایل استاندارد شده و مسیرهای import اصلاح شده (از جمله رفع باگ
`from app.utils.tools import route_query` که به‌اشتباه به ماژولی به نام
`tools` اشاره می‌کرد؛ اکنون درست به app.rag.query_transformer اشاره
می‌کند). منطق و رفتار گراف بدون هیچ تغییری باقی مانده است.

پیاده‌سازی کامل جریان RAG (از دریافت سؤال کاربر تا پاسخ نهایی) با LangGraph.

جریان کلی:

    search ──► decide ──► coverage ──┬─(COMPLETE)───────────► generate ──► END
                              ▲       │
                              │       └─(PARTIAL/NOT_FOUND و هنوز retry نشده)
                              │                       │
                              │                       ▼
                              └───────────────────  transform
                                (یک‌بار دیگر coverage چک می‌شود)

    اگر بعد از یک دور transform، coverage باز هم COMPLETE نبود، صرف‌نظر از
    status، مستقیم به generate می‌رویم (طبق مشخصات: فقط یک بار retry).
"""

from typing import TypedDict

from langgraph.graph import StateGraph, END

from app.rag.decider import decide_context, _build_context
from app.rag.coverage_checker import Coverage_Checker
from app.rag.query_transformer import route_query
from app.rag.generator import generate_answer
from app.services.retriever import search_children


# ════════════════════════════════════════════════════════════════
# تنظیمات
# ════════════════════════════════════════════════════════════════

FIRST_SEARCH_TOP_K = 5      # تعداد child در جست‌وجوی اولیه
TRANSFORM_TOP_K = 1         # تعداد child برای هر query تولیدشده در مرحله‌ی transform


# ════════════════════════════════════════════════════════════════
# State گراف
# ════════════════════════════════════════════════════════════════

class RAGState(TypedDict, total=False):
    query: str                 # سؤال اصلی کاربر (ثابت در طول گراف)
    child_results: list        # آخرین نتایج child بازیابی‌شده
    parent_ids: list[str]      # مجموع تمام parent_id هایی که تا الان context‌شان ساخته شده
    context: str                # context تجمعی نهایی
    status: str                 # آخرین خروجی Coverage_Checker: COMPLETE / PARTIAL / NOT_FOUND
    missing: list[str]           # آخرین بخش‌های ناقص گزارش‌شده توسط Coverage_Checker

    missing_before_transform: list[str]
    # همان missing ای که باعث ورود به مرحله‌ی transform شد؛ برخلاف
    # "missing" که بعد از دومین coverage check ممکن است خالی شود (مثلاً
    # چون status نهایی COMPLETE شده)، این فیلد ثابت می‌ماند تا مشخص باشد
    # قبل از transform دقیقاً چه چیزی ناقص تشخیص داده شده بود.

    transform_tool_used: list[str]
    # به ازای هر آیتم از missing_before_transform، نام ابزاری که
    # route_query انتخاب کرده (multiquery یا decompose).

    transform_queries: list[str]
    # مجموع تمام query/sub_query هایی که توسط transformer (چه از
    # multiquery چه از decompose) برای بازیابی مجدد ساخته و سرچ شده‌اند.

    retried: bool                # آیا یک دور transform را قبلاً طی کرده‌ایم؟
    answer: str                  # پاسخ نهایی


# ════════════════════════════════════════════════════════════════
# ابزار کمکی: پارس‌کردن خروجی JSON مدل Coverage_Checker
# ════════════════════════════════════════════════════════════════

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


# ════════════════════════════════════════════════════════════════
# Node 1 : جست‌وجوی اولیه بردار بر اساس سؤال کاربر
# ════════════════════════════════════════════════════════════════

def node_search(state: RAGState) -> dict:
    child_results = search_children(
        state["query"],
        collection_name="loader",
        top_k=FIRST_SEARCH_TOP_K,
    )
    return {"child_results": child_results}


# ════════════════════════════════════════════════════════════════
# Node 2 : تشخیص parent های مرتبط و ساخت context اولیه
# ════════════════════════════════════════════════════════════════

def node_decide(state: RAGState) -> dict:
    result = decide_context(state["query"], state["child_results"])
    return {
        "parent_ids": result.parent_ids,
        "context": result.context,
    }


# ════════════════════════════════════════════════════════════════
# Node 3 : بررسی کفایت context (Coverage Check)
# ════════════════════════════════════════════════════════════════

def node_coverage(state: RAGState) -> dict:
    check_result = Coverage_Checker(state["query"], state["context"])
    return {
        "status": check_result.get("status", "NOT_FOUND"),
        "missing": check_result.get("missing", []),
    }


# ════════════════════════════════════════════════════════════════
# Node 4 : Transform — برای هر بخش missing، route_query صدا زده
# می‌شود (multiquery یا decompose)، سپس برای هر query نتیجه‌ی آن
# جست‌وجوی جدید انجام و merge می‌شود. فقط برای parent_id هایی که
# قبلاً دیده نشده‌اند context جدید ساخته می‌شود.
# ════════════════════════════════════════════════════════════════

def node_transform(state: RAGState) -> dict:
    missing_list = state.get("missing") or []

    if not missing_list:
        # چیزی برای transform کردن نیست؛ فقط retry را علامت می‌زنیم
        # تا در دور بعد coverage، مستقیم به generate برویم.
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
                collection_name="loader",
                top_k=TRANSFORM_TOP_K,
            )
            all_new_child_results.extend(results)

    # حذف نتایج تکراری بر اساس child_id
    unique_results = {r.child_id: r for r in all_new_child_results}
    unique_results = list(unique_results.values())

    unique_parent_ids = list({r.parent_id for r in unique_results})

    # فقط برای parent_id هایی که تا الان دیده نشده‌اند context بسازیم
    seen_parent_ids = set(state.get("parent_ids") or [])
    new_parent_ids = [pid for pid in unique_parent_ids if pid not in seen_parent_ids]

    new_context = ""
    if new_parent_ids:
        new_context = _build_context(new_parent_ids, unique_results)

    merged_context = state.get("context", "")
    if new_context:
        merged_context = f"{merged_context}\n\n{new_context}".strip() if merged_context else new_context

    merged_parent_ids = list(seen_parent_ids | set(new_parent_ids))

    return {
        "context": merged_context,
        "parent_ids": merged_parent_ids,
        "retried": True,
        "missing_before_transform": missing_list,
        "transform_tool_used": transform_tool_used,
        "transform_queries": transform_queries_all,
    }


# ════════════════════════════════════════════════════════════════
# Node 5 : تولید پاسخ نهایی
# ════════════════════════════════════════════════════════════════

def node_generate(state: RAGState) -> dict:
    answer = generate_answer(state["query"], state.get("context", ""))
    return {"answer": answer}


# ════════════════════════════════════════════════════════════════
# مسیر شرطی بعد از Coverage
# ════════════════════════════════════════════════════════════════

def route_after_coverage(state: RAGState) -> str:
    if state.get("status") == "COMPLETE":
        return "generate"
    if state.get("retried"):
        # قبلاً یک بار transform انجام شده؛ دیگر تلاش دوباره نمی‌کنیم
        # و با همین context، به generate می‌رویم.
        return "generate"
    return "transform"


# ════════════════════════════════════════════════════════════════
# ساخت گراف
# ════════════════════════════════════════════════════════════════

def build_rag_graph():
    graph = StateGraph(RAGState)

    graph.add_node("search", node_search)
    graph.add_node("decide", node_decide)
    graph.add_node("coverage", node_coverage)
    graph.add_node("transform", node_transform)
    graph.add_node("generate", node_generate)

    graph.set_entry_point("search")

    graph.add_edge("search", "decide")
    graph.add_edge("decide", "coverage")

    graph.add_conditional_edges(
        "coverage",
        route_after_coverage,
        {
            "generate": "generate",
            "transform": "transform",
        },
    )

    graph.add_edge("transform", "coverage")
    graph.add_edge("generate", END)

    return graph.compile()


_rag_app = build_rag_graph()


# ════════════════════════════════════════════════════════════════
# API نهایی
# ════════════════════════════════════════════════════════════════

def run_rag_pipeline(query: str) -> RAGState:
    """
    کل جریان RAG را برای یک سؤال کاربر اجرا می‌کند و state نهایی
    (شامل answer, context, parent_ids, status, missing و ...) را
    برمی‌گرداند.
    """
    initial_state: RAGState = {
        "query": query,
        "child_results": [],
        "parent_ids": [],
        "context": "",
        "status": "",
        "missing": [],
        "missing_before_transform": [],
        "transform_tool_used": [],
        "transform_queries": [],
        "retried": False,
        "answer": "",
    }
    final_state = _rag_app.invoke(initial_state)
    return final_state


# ────────────────────────────────────────────────────────────────
# مثال استفاده:
#
# result = run_rag_pipeline(
#     "از اجزای rag درباره تقسیم بندی متن کامل توضییح بده و آینده این سیستم هارم بگو"
# )
# print(result["answer"])
# ────────────────────────────────────────────────────────────────
