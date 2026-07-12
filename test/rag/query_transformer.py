import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.agent.chians import multiquery_chain , decompose_chain 

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
    max_tokens=512,
    base_url="https://api.gapgpt.app/v1",
    api_key=settings.OPENAI_API_KEY,
)


# ────────────────────────────────────────────────────────────────
# ابزار کمکی برای parse کردن خروجی JSON مدل‌ها (مشترک بین Agent‌های تخصصی)
# ────────────────────────────────────────────────────────────────

def _parse_json_list(raw: str, key: str) -> list[str]:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group())
        values = data.get(key, [])
        if not isinstance(values, list):
            return []
        return [str(v).strip() for v in values if str(v).strip()]
    except (json.JSONDecodeError, AttributeError):
        return []


# -------------------------------------



def run_multiquery_agent(query: str) -> dict:
    """اجرای Agent تخصصی Multi-Query و برگرداندن نتیجه‌ی parse‌شده."""
    raw = multiquery_chain.invoke({"query": query})
    queries = _parse_json_list(raw, "queries")
    if not queries:
        queries = [query]
    return {"queries": queries}

# -------------------------------------------------------------

def run_decompose_agent(query: str) -> dict:
    raw = decompose_chain.invoke({"query": query})
    queries = _parse_json_list(raw, "queries")   # قبلاً "sub_queries" بود
    if not queries:
        queries = [query]
    return {"queries": queries}   # قبلاً "sub_queries": ... بود



# ════════════════════════════════════════════════════════════════

@tool
def multiquery(query: str) -> str:
    """
    وقتی سؤال کاربر مبهم است یا می‌تواند به چند شکل مختلف بیان شود و برای
    بهبود پوشش بازیابی (retrieval) نیاز به چند بازنویسی متفاوت از همان
    سؤال داریم، از این ابزار استفاده کن.
    برای مثال یک مفهوم یا واژه کلیدی را به فارسی تایپ کرده و آن باید هم
    به انگلیسی ترجمه/بازنویسی شود. مثل: رگ → rag، استریم → stream،
    رگ گراف → graphrag.
    """


@tool
def decompose(query: str) -> str:
    """
    وقتی سؤال کاربر پیچیده، چندبخشی است یا شامل چند پرسش مستقل/وابسته
    در دل خودش است (مثلاً «تفاوت X و Y چیست و کدام برای Z بهتر است؟»)،
    از این ابزار استفاده کن.
    """


AGENT_DISPATCH = {
    "multiquery": run_multiquery_agent,
    "decompose": run_decompose_agent,
}

router_tools = [multiquery, decompose]
router_llm = llm.bind_tools(router_tools, tool_choice="required")

ROUTER_SYSTEM = """تو یک Router هوشمند در سیستم RAG هستی.

وظیفه‌ات این است که با توجه به خصوصیات سؤال کاربر، دقیقاً یکی از دو
ابزار زیر را انتخاب و صدا بزنی — نه بیشتر، نه کمتر. فقط تصمیم بگیر و
ابزار را صدا بزن؛ خودت هرگز سعی نکن مستقیماً به سؤال پاسخ بدهی،
بازنویسی کنی یا تجزیه کنی:

1. multiquery  : وقتی سؤال مبهم است یا می‌تواند به چند شکل مختلف بیان
                 شود و نیاز به بازنویسی‌های متعدد برای پوشش بهتر
                 جست‌وجو داریم.
2. decompose   : وقتی سؤال پیچیده و چندبخشی است و شامل چند پرسش مستقل
                 یا وابسته به هم است.
"""


# ────────────────────────────────────────────────────────────────

def route_query(query: str) -> dict:
 
    decision = router_llm.invoke([
        SystemMessage(content= ROUTER_SYSTEM),
        HumanMessage(content=query),
    ])

    tool_calls = getattr(decision, "tool_calls", None) or []
    if not tool_calls:
        tool_used = "multiquery"
    else:
        tool_used = tool_calls[0]["name"]

    agent_fn = AGENT_DISPATCH.get(tool_used, run_multiquery_agent)
    result = agent_fn(query)

    return {
        "tool_used": tool_used,
        "result": result,
    }


# ────────────────────────────────────────────────────────────────

# def print_route_result(route_result: dict) -> None:
#     """نتیجه‌ی مسیریابی و خروجی Agent تخصصی انتخاب‌شده را خوانا چاپ می‌کند."""
#     print("=" * 60)
#     print(f"Agent تخصصی انتخاب‌شده : {route_result.get('tool_used')}")
#     print("-" * 60)
#     print(json.dumps(route_result.get("result", {}), ensure_ascii=False, indent=2))
#     print("=" * 60)

