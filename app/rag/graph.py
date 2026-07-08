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
from app.rag.schema.graphstate import RAGState
from .nodes import node_search , node_decide,node_coverage,node_transform,node_generate,route_after_coverage


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

    graph.add_edge("transform", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


_rag_app = build_rag_graph()

