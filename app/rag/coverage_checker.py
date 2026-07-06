#coverage_checker.py

import json
import re
from app.rag.chians import coverage_chain


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

    raw: str = coverage_chain.invoke({
        "query": query,
        "context": context,
    })

    return _parse_coverage_json(raw)
