# CoverageChecker.py

import json
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings


# ────────────────────────────────────────────────────────────────

_llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.3,
    max_tokens=1024,
    base_url="https://api.gapgpt.app/v1",
    api_key=settings.OPENAI_API_KEY,
)


# ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """
تو یک Coverage Checker در یک سیستم RAG هستی.

وظیفه تو پاسخ دادن به سؤال کاربر نیست.

وظیفه تو فقط بررسی کامل بودن Context است.
ورودی تو شامل موارد زیر است:

1. سؤال اصلی کاربر
2. Context بازیابی شده
--------------------------------------------------

ابتدا سؤال کاربر را به بخش‌های اطلاعاتی موردنیاز تجزیه کن.

سپس بررسی کن که آیا Context هر بخش را پوشش می‌دهد یا خیر.

اگر همه بخش‌ها پوشش داده شده‌اند:

{{
  "status":"COMPLETE",
}}

اگر فقط بخشی از سؤال قابل پاسخ است:
فقظ و فقط قسمتی که پاسخ برای آن وجود ندارد را در missing قرار بده
{{
  "status":"PARTIAL",
  "missing":[
      "...",
      "..."
  ]
}}

اگر هیچ بخشی قابل پاسخ نیست:

{{
  "status":"NOT_FOUND",
  "missing":[
      "..."
  ]
}}

--------------------------------------------------

قواعد مهم
- فقط JSON معتبر تولید کن.
missing را سعی نکن خودت پر کنی یا تغیری در پرسش کاربر بدی ، هر قسمتی که پاسخ برایش وجود ندارد را همانگونه که هست در این بخش قرار بده

"""


_HUMAN_TEMPLATE = """\
Context:
{context}

سؤال کاربر:
{query}
"""


_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
    ("human", _HUMAN_TEMPLATE),
])

_chain = _prompt | _llm | StrOutputParser()


# ─────────────────────────────────────────────────────────
# مقادیر پیش‌فرض/محافظه‌کارانه برای حالت‌های استثنایی
# ─────────────────────────────────────────────────────────

_NOT_FOUND_NO_CONTEXT = {"status": "NOT_FOUND", "missing": []}
_NOT_FOUND_PARSE_ERROR = {"status": "NOT_FOUND", "missing": []}


def _parse_coverage_json(raw: str) -> dict:
    """
    خروجی خام مدل (رشته‌ی JSON) را به دیکشنری استاندارد {status, missing}
    تبدیل می‌کند. در صورت هرگونه خطا در parse، NOT_FOUND با missing خالی
    برگردانده می‌شود (محافظه‌کارانه‌ترین حالت، یعنی یک دور تلاش برای
    بازیابی مجدد context در گراف انجام شود).
    """
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return dict(_NOT_FOUND_PARSE_ERROR)

    try:
        data = json.loads(match.group())
    except (json.JSONDecodeError, AttributeError):
        return dict(_NOT_FOUND_PARSE_ERROR)

    status = data.get("status", "NOT_FOUND")
    if status not in ("COMPLETE", "PARTIAL", "NOT_FOUND"):
        status = "NOT_FOUND"

    missing = data.get("missing", [])
    if not isinstance(missing, list):
        missing = []
    missing = [str(m).strip() for m in missing if str(m).strip()]

    return {"status": status, "missing": missing}


# ─────────────────────────────────────────────────────────

def Coverage_Checker(query: str, context: str) -> dict:
    """
    بررسی می‌کند که آیا context موجود برای پاسخ‌دهی کامل به query کافی
    است یا نه.

    پارامترها:
        query   : سؤال کاربر
        context : context بازیابی‌شده (خروجی result.context از decide_context)

    خروجی:
        دیکشنری استاندارد به یکی از سه شکل زیر:
            {"status": "COMPLETE"}
            {"status": "PARTIAL",   "missing": [...]}
            {"status": "NOT_FOUND", "missing": [...]}

    اگر context خالی باشد (یعنی هیچ منبع مرتبطی پیدا نشده)، بدون صدا
    زدن مدل، مستقیماً NOT_FOUND با missing برابر خود سؤال برگردانده
    می‌شود.
    """
    if not context or not context.strip():
        return {"status": "NOT_FOUND", "missing": [query]}

    raw: str = _chain.invoke({
        "query": query,
        "context": context,
    })

    return _parse_coverage_json(raw)