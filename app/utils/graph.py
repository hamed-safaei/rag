"""
graph.py
────────
LangGraph orchestrator: retry با query transformation وقتی decider به NONE برسد.
"""

import json
import re
from typing import Literal, TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, END
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.utils.Decider import decide_context, DecisionResult, print_decision_result
from app.utils.Retriever import search_children


# ────────────────────────────────────────────────────────────
# State
# ────────────────────────────────────────────────────────────

class GraphState(TypedDict):
    query: str                          # سؤال اصلی (همیشه ثابت)
    current_query: str                  # سؤال فعلی برای جست‌وجو (ممکن است transform شده باشد)
    child_results: list                 # نتایج بازیابی‌شده (تجمعی)
    seen_child_ids: set                 # برای dedupe بین تلاش‌ها
    decision_result: DecisionResult | None
    attempts: int                       # شمارنده تلاش‌ها (حداکثر 3)
    used_techniques: Annotated[list[str], operator.add]  # تکنیک‌های امتحان‌شده
    final: bool                         # آیا گراف باید متوقف شود
    pending_technique: str | None       # تکنیک انتخاب‌شده در مرحله transform
    pending_queries: list[str]          # query(های) تولیدشده توسط transform agent


# ────────────────────────────────────────────────────────────
# Query Transformation Agent
# ────────────────────────────────────────────────────────────

_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    max_tokens=512,
    base_url="https://api.gapgpt.app/v1",
    api_key=settings.OPENAI_API_KEY,
)

_TRANSFORM_SYSTEM_PROMPT = """\
تو یک دستیار هوشمند هستی که وظیفه‌ات بهبود کیفیت بازیابی (Retrieval) در یک سیستم RAG است.

تاکنون با سؤال زیر، نتایج بازیابی‌شده برای پاسخ‌گویی کافی نبوده‌اند:
سؤال اصلی: {query}

تکنیک‌هایی که قبلاً امتحان شده‌اند (دیگر این‌ها را انتخاب نکن): {used_techniques}

باید یکی از این چهار تکنیک را انتخاب کنی تا سؤال را بازنویسی/گسترش دهی و نتیجه بازیابی بهتری بگیریم:

① MultiQuery — سؤال را به چند نسخه‌ی هم‌معنا اما با کلمات/زاویه‌ی متفاوت بازنویسی کن.
   مناسب وقتی: کلمات سؤال با اصطلاحات متن سند مطابقت ندارد (مثلاً مترادف‌ها).

② Decompose — سؤال را به چند زیرسؤال کوچک‌تر و مستقل تجزیه کن.
   مناسب وقتی: سؤال چند بخشی یا مرکب است.

③ StepBack — یک سؤال کلی‌تر و مفهومی‌تر (یک قدم به عقب) بساز که زمینه‌ی موضوع را پوشش دهد.
   مناسب وقتی: سؤال خیلی جزئی/فنی است و شاید سند فقط مفهوم کلی‌تر را پوشش داده.

④ HyDE — یک پاسخ فرضی (Hypothetical Document) برای سؤال بنویس که شبیه متنی باشد
   که در سند می‌تواند وجود داشته باشد؛ این پاسخ فرضی برای embedding search استفاده می‌شود.
   مناسب وقتی: سؤال کوتاه/مبهم است و embedding مستقیم سؤال، شباهت کافی با اسناد ندارد.

فقط یک تکنیک انتخاب کن (تکنیکی که قبلاً امتحان نشده). خروجی را دقیقاً به این فرمت JSON بده:

برای MultiQuery:
{{"technique": "MultiQuery", "queries": ["نسخه ۱", "نسخه ۲", "نسخه ۳"]}}

برای Decompose:
{{"technique": "Decompose", "queries": ["زیرسؤال ۱", "زیرسؤال ۲"]}}

برای StepBack:
{{"technique": "StepBack", "queries": ["سؤال کلی‌تر"]}}

برای HyDE:
{{"technique": "HyDE", "queries": ["متن فرضی پاسخ"]}}

هیچ توضیح اضافه‌ای ننویس — فقط JSON خالص برگردان.
"""

_transform_prompt = ChatPromptTemplate.from_messages([
    ("system", _TRANSFORM_SYSTEM_PROMPT),
])

_transform_chain = _transform_prompt | _llm | StrOutputParser()


def _parse_transform_response(raw: str) -> tuple[str, list[str]]:
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_match:
        return "MultiQuery", []
    try:
        data = json.loads(json_match.group())
        technique = data.get("technique", "MultiQuery")
        queries = data.get("queries", [])
        if not isinstance(queries, list):
            queries = []
        return technique, queries
    except (json.JSONDecodeError, AttributeError):
        return "MultiQuery", []


# ────────────────────────────────────────────────────────────
# Graph Nodes
# ────────────────────────────────────────────────────────────

def node_initial_search(state: GraphState) -> dict:
    """جست‌وجوی اولیه با سؤال خام کاربر."""
    results = search_children(state["query"], collection_name="loader", top_k=5)
    seen = {r.child_id for r in results}
    return {
        "current_query": state["query"],
        "child_results": results,
        "seen_child_ids": seen,
        "attempts": 0,
    }


def node_decide(state: GraphState) -> dict:
    """صدا زدن decider روی نتایج فعلی."""
    result = decide_context(state["query"], state["child_results"])
    return {"decision_result": result}


def node_transform_query(state: GraphState) -> dict:
    """Agent تصمیم می‌گیرد کدام تکنیک query transformation را اجرا کند."""
    raw = _transform_chain.invoke({
        "query": state["query"],
        "used_techniques": ", ".join(state["used_techniques"]) or "هیچ‌کدام",
    })
    technique, queries = _parse_transform_response(raw)

    if not queries:
        queries = [state["query"]]

    return {
        "pending_technique": technique,
        "pending_queries": queries,
    }


def node_search_transformed(state: GraphState) -> dict:
    """جست‌وجو با queryهای تولیدشده توسط transform agent، با dedupe نسبت به نتایج قبلی."""
    technique = state["pending_technique"]
    queries = state["pending_queries"]

    all_results = []
    seen = set(state["seen_child_ids"])

    # وقتی چند query داریم (MultiQuery/Decompose)، top_k رو کمی پایین‌تر می‌آریم
    # تا context شلوغ نشه
    top_k = 5 if len(queries) == 1 else 3

    for q in queries:
        results = search_children(q, collection_name="loader", top_k=top_k)
        for r in results:
            if r.child_id not in seen:
                seen.add(r.child_id)
                all_results.append(r)

    combined_results = state["child_results"] + all_results

    return {
        "current_query": " | ".join(queries),
        "child_results": combined_results,
        "seen_child_ids": seen,
        "used_techniques": [technique],
        "attempts": state["attempts"] + 1,
    }


# ────────────────────────────────────────────────────────────
# Conditional Edges
# ────────────────────────────────────────────────────────────

def route_after_decide(state: GraphState) -> Literal["transform", "end"]:
    decision = state["decision_result"].decision

    if decision != "NONE":
        return "end"

    if state["attempts"] >= 3:
        return "end"

    return "transform"


# ────────────────────────────────────────────────────────────
# Build Graph
# ────────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("initial_search", node_initial_search)
    graph.add_node("decide", node_decide)
    graph.add_node("transform_query", node_transform_query)
    graph.add_node("search_transformed", node_search_transformed)

    graph.set_entry_point("initial_search")

    graph.add_edge("initial_search", "decide")

    graph.add_conditional_edges(
        "decide",
        route_after_decide,
        {
            "transform": "transform_query",
            "end": END,
        },
    )

    graph.add_edge("transform_query", "search_transformed")
    graph.add_edge("search_transformed", "decide")

    return graph.compile()


# ────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────

_compiled_graph = build_graph()


def run_query(query: str) -> GraphState:
    initial_state: GraphState = {
        "query": query,
        "current_query": query,
        "child_results": [],
        "seen_child_ids": set(),
        "decision_result": None,
        "attempts": 0,
        "used_techniques": [],
        "final": False,
        "pending_technique": None,
        "pending_queries": [],
    }

    final_state = _compiled_graph.invoke(initial_state)
    return final_state
