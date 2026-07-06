# app/rag/query_transformer.py
#
# منبع اصلی: app/utils/transformer.py
# فقط محل و نام فایل استاندارد شده (transformer.py -> query_transformer.py)؛
# منطق بدون تغییر.

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.core.config import settings


# ────────────────────────────────────────────────────────────────
# LLM مشترک بین Router-Agent و Agent‌های تخصصی
# ────────────────────────────────────────────────────────────────

_llm = ChatOpenAI(
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


# ════════════════════════════════════════════════════════════════
# AGENT تخصصی ۱ : Multi-Query Agent
# مسئول تولید ۳ تا ۵ بازنویسی مختلف از سؤال کاربر برای پوشش بهتر
# جست‌وجوی معنایی (semantic search).
# ════════════════════════════════════════════════════════════════

_MULTIQUERY_SYSTEM = """تو یک Agent تخصصی بازنویسی سؤال در سیستم RAG هستی.

وظیفه‌ات این است که از روی سؤال کاربر، ۳ تا ۵ بازنویسی متفاوت اما هم‌معنی
تولید کنی. هدف این است که با زاویه‌ها و کلمات مختلف، پوشش بهتری برای
جست‌وجوی معنایی (semantic search) به دست بیاید.

قوانین:
- معنای اصلی سؤال نباید تغییر کند.
- از مترادف، تغییر ساختار جمله و زوایای دید مختلف استفاده کن.
- فقط بازنویسی سؤال؛ به آن پاسخ نده.
- برخی کلید واژه‌ها که ممکن است نیاز باشد از فارسی به انگلیسی ترجمه شود.

━━━ خروجی ━━━
فقط یک JSON معتبر و تک‌خطی، بدون هیچ توضیح یا متن اضافه:

{{
  "queries": ["...", "...", "..."]
}}
"""

_multiquery_prompt = ChatPromptTemplate.from_messages([
    ("system", _MULTIQUERY_SYSTEM),
    ("human", "سؤال کاربر:\n{query}"),
])

_multiquery_chain = _multiquery_prompt | _llm | StrOutputParser()


def run_multiquery_agent(query: str) -> dict:
    """اجرای Agent تخصصی Multi-Query و برگرداندن نتیجه‌ی parse‌شده."""
    raw = _multiquery_chain.invoke({"query": query})
    queries = _parse_json_list(raw, "queries")
    if not queries:
        queries = [query]
    return {"tool": "multiquery", "queries": queries}


# ════════════════════════════════════════════════════════════════
# AGENT تخصصی ۲ : Decompose Agent
# مسئول شکستن سؤال پیچیده و چندبخشی به چند زیرسؤال ساده‌تر و مستقل.
# ════════════════════════════════════════════════════════════════

_DECOMPOSE_SYSTEM = """تو یک Agent تخصصی تجزیه سؤال در سیستم RAG هستی.

وظیفه‌ات این است که یک سؤال پیچیده یا چندبخشی را به چند زیرسؤال ساده‌تر و
مستقل بشکنی، طوری که پاسخ به همه‌ی زیرسؤال‌ها در کنار هم، پاسخ کامل
سؤال اصلی را بدهد.

قوانین:
- هر زیرسؤال باید به‌تنهایی قابل‌فهم و قابل‌جست‌وجو باشد.
- از تکرار غیرضروری خودداری کن.
- اگر سؤال اصلی خیلی هم پیچیده نیست، همان یک زیرسؤال (خود سؤال اصلی) را
  برگردان.

━━━ خروجی ━━━
فقط یک JSON معتبر و تک‌خطی، بدون هیچ توضیح یا متن اضافه:

{{
  "sub_queries": ["...", "...", "..."]
}}
"""

_decompose_prompt = ChatPromptTemplate.from_messages([
    ("system", _DECOMPOSE_SYSTEM),
    ("human", "سؤال کاربر:\n{query}"),
])

_decompose_chain = _decompose_prompt | _llm | StrOutputParser()


def run_decompose_agent(query: str) -> dict:
    """اجرای Agent تخصصی Decompose و برگرداندن نتیجه‌ی parse‌شده."""
    raw = _decompose_chain.invoke({"query": query})
    sub_queries = _parse_json_list(raw, "sub_queries")
    if not sub_queries:
        sub_queries = [query]
    return {"tool": "decompose", "sub_queries": sub_queries}


# ════════════════════════════════════════════════════════════════
# ابزارهای Router (فقط برای معرفی schema به مدل جهت tool-calling)
# این‌ها هیچ‌وقت واقعاً اجرا (invoke) نمی‌شوند؛ فقط برای اینکه مدل
# اول با function-calling تصمیم بگیرد کدام یک مناسب است استفاده
# می‌شوند. اجرای واقعی هر کدام به‌صورت مستقیم و دستی در ادامه (بدون
# برگرداندن نتیجه به مدل اول) انجام می‌شود.
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


# نگاشت نام ابزار به Agent تخصصی متناظر جهت اجرای مستقیم و دستی
_AGENT_DISPATCH = {
    "multiquery": run_multiquery_agent,
    "decompose": run_decompose_agent,
}

_router_tools = [multiquery, decompose]

# مدل با ابزارها bind می‌شود اما هیچ agent-loop‌ای وجود ندارد؛
# فقط از قابلیت tool-calling برای «تصمیم‌گیری» یک‌باره استفاده می‌شود.
_router_llm = _llm.bind_tools(_router_tools, tool_choice="required")

_ROUTER_SYSTEM = """تو یک Router هوشمند در سیستم RAG هستی.

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
    """
    سؤال را پردازش می‌کند:
      1) فقط یک API call به مدل اول (Router) زده می‌شود تا مشخص شود
         کدام Agent تخصصی (multiquery / decompose) باید اجرا شود.
         خروجی این تماس صرفاً یک tool_call است؛ محتوایی تولید نمی‌شود.
      2) بر اساس نام ابزار انتخاب‌شده، Agent تخصصی متناظر مستقیماً و
         دستی (بدون واسطه‌ی هیچ agent-loop‌ای) فراخوانی می‌شود و خروجی
         نهایی را تولید می‌کند.
      3) نتیجه‌ی همان Agent تخصصی، بدون بازگشت به مدل اول، مستقیماً
         به‌عنوان خروجی نهایی برگردانده می‌شود. یعنی در کل فقط دو
         API call زده می‌شود: یکی برای تصمیم‌گیری، یکی برای تولید محتوا.

    خروجی یک دیکشنری شامل:
        - tool_used : نام Agent تخصصی‌ای که انتخاب شده
        - result    : خروجی نهایی Agent تخصصی (dict)
    """
    decision = _router_llm.invoke([
        SystemMessage(content=_ROUTER_SYSTEM),
        HumanMessage(content=query),
    ])

    tool_calls = getattr(decision, "tool_calls", None) or []
    if not tool_calls:
        # حالت استثنایی: مدل هیچ ابزاری صدا نزده؛ به multiquery برمی‌گردیم.
        tool_used = "multiquery"
    else:
        tool_used = tool_calls[0]["name"]

    agent_fn = _AGENT_DISPATCH.get(tool_used, run_multiquery_agent)
    result = agent_fn(query)

    return {
        "tool_used": tool_used,
        "result": result,
    }


# ────────────────────────────────────────────────────────────────

def print_route_result(route_result: dict) -> None:
    """نتیجه‌ی مسیریابی و خروجی Agent تخصصی انتخاب‌شده را خوانا چاپ می‌کند."""
    print("=" * 60)
    print(f"Agent تخصصی انتخاب‌شده : {route_result.get('tool_used')}")
    print("-" * 60)
    print(json.dumps(route_result.get("result", {}), ensure_ascii=False, indent=2))
    print("=" * 60)

