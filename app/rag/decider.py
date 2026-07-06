# app/rag/decider.py
#
# منبع اصلی: app/utils/Decider.py
# فقط محل و نام فایل استاندارد شده؛ منطق بدون تغییر.

import json
import re
from dataclasses import dataclass, field

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings


# ────────────────────────────────────────────────────────────────

_llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
    max_tokens=256,
    base_url="https://api.gapgpt.app/v1",
    api_key=settings.OPENAI_API_KEY,
)


# ────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """تو یک دستیار بررسی Context در سیستم RAG هستی.

وظیفه‌ات پاسخ به سؤال نیست. فقط باید تک‌تک Childهای بازیابی‌شده را یکی‌یکی بررسی کنی
و برای هرکدام تصمیم بگیری که آیا برای پاسخ‌دهی به سؤال لازم هستند یا نه.

ورودی:
1. سؤال کاربر
2. مجموعه‌ای از Child ها 

روش بررسی هر Child:
فقط به این سه مورد نگاه کن:
- parent_title
- child_title
- child_content

برای هر Child:
- اگر کاملاً مطمئن بودی که نه parent_title، نه child_title و نه child_content
  هیچ ربطی به سؤال ندارند → از آن Child بگذر و به سراغ Child بعدی برو (چیزی برایش برنگردان).
- حتی اگر بخشی از child_content با سوال مرتبط بود ، آن child تایید است

نکات مهم:
- همیشه فقط parent_id برگردانده می‌شود، هرگز child_id برگردانده نمی‌شود.
- اگر چند Child متعلق به یک parent مرتبط تشخیص داده شدند، parent_id فقط یک‌بار
  (به‌صورت یکتا) در خروجی بیاید.
- ترتیب خاصی برای parent_id ها لازم نیست.

━━━ خروجی ━━━
فقط یک JSON معتبر و تک‌خطی، بدون هیچ توضیح یا متن اضافه:

{{
  "parents": ["..."]
}}

اگر هیچ Childی واجد شرایط نبود، آرایه را خالی برگردان:

{{
  "parents": []
}}
"""

_HUMAN_TEMPLATE = """\
سؤال کاربر:
{query}

Child های بازیابی‌شده:
{formatted_chunks}
"""


_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
    ("human", _HUMAN_TEMPLATE),
])

_chain = _prompt | _llm | StrOutputParser()


# ─────────────────────────────────────────────────────────

@dataclass
class DecisionResult:
    parent_ids: list[str] = field(default_factory=list)
    context:    str       = ""     # context نهایی آماده برای LLM اصلی

    @property
    def is_empty(self) -> bool:
        """اگر parent_ids خالی باشد، یعنی Context کافی پیدا نشده (NONE)."""
        return not self.parent_ids


# ─────────────────────────────────────────

def _format_chunks(child_results) -> str:
    """
    parent title :  ...
    child title  :  ...
    child content:
    ...
    parent id    :  X
    """
    parts = []
    for r in child_results:
        parts.append(
            f"parent title :  {r.parent_title}\n"
            f"child title : {r.child_title}\n"
            f"child content :\n{r.child_content}\n"
            f"parent id    :  {r.parent_id}"
        )
    return "\n\n---\n\n".join(parts)


# ───────────────────────────────────────────────────

def _parse_response(raw: str) -> list[str]:
    """
    خروجی JSON مدل را parse می‌کند.
    برمی‌گرداند: parent_ids
    در صورت هرگونه خطا در parse → [] (یعنی معادل NONE)
    """
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_match:
        return []

    try:
        data = json.loads(json_match.group())

        parent_ids = data.get("parents", [])

        if not isinstance(parent_ids, list):
            parent_ids = []

        # حذف تکراری‌ها با حفظ ترتیب
        parent_ids = list(dict.fromkeys(str(p) for p in parent_ids))

        return parent_ids

    except (json.JSONDecodeError, AttributeError):
        return []


# ────────────────────────────────────────────────

def _build_context(
    parent_ids: list[str],
    child_results,
) -> str:
    """
    parent_ids خالی → خروجی خالی (NONE)
    در غیر این صورت: برای هر parent_id انتخاب‌شده، کل parent_content
    یک‌بار (به‌صورت یکتا) اضافه می‌شود.
    """
    if not parent_ids:
        return ""

    parts = []
    added_parents = set()
    id_set = set(parent_ids)

    for r in child_results:
        if r.parent_id in id_set and r.parent_id not in added_parents:
            added_parents.add(r.parent_id)
            parts.append(
                f"### [{r.parent_id}] {r.parent_title}\n"
                f"{r.parent_content}"
            )

    return "\n\n".join(parts)


# ─────────────────────────────────────────────────────────

def decide_context(
    query: str,
    child_results,
) -> DecisionResult:
    """
    LangChain chain را صدا می‌زند و بر اساس بررسی تک‌تک Childها (parent_title,
    child_title, child_content)، آرایه‌ی یکتای parent_ids را پر می‌کند و
    context نهایی را می‌سازد.

    پارامترها:
        query        : سؤال کاربر
        child_results: خروجی search_children
    """
    if not child_results:
        return DecisionResult(context="")

    formatted_chunks = _format_chunks(child_results)

    raw_output: str = _chain.invoke({
        "query": query,
        "formatted_chunks": formatted_chunks,
    })

    parent_ids = _parse_response(raw_output)
    context = _build_context(parent_ids, child_results)

    return DecisionResult(
        parent_ids=parent_ids,
        context=context,
    )


# ───────────────────────────────────────────────────────────────

def print_decision_result(result: DecisionResult) -> None:
    """نتیجه تصمیم و context انتخاب‌شده را به‌صورت خوانا چاپ می‌کند."""
    print("=" * 60)
    if result.is_empty:
        print("تصمیم      : NONE")
        print("اطلاعات کافی برای پاسخ به این سؤال در منابع یافت نشد.")
        print("=" * 60)
        return
    print(f"Parent IDs : {result.parent_ids}")
    print("=" * 60)
    print("Context نهایی:")
    print("-" * 60)
    print(result.context)
    print("=" * 60)
